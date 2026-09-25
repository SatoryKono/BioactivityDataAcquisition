import json, os, re, subprocess, sys, tempfile, time

REPO = "/mnt/e/github/BioactivityDataAcquisition"
OUT = os.path.join(REPO, "reports/quality/coderabbit/20260925_085141")
RUN = os.path.expanduser("~/cr-audit-20260925_085141")
BASE = open(os.path.join(OUT, "baseline_sha.txt")).read().strip()
CONTEXT = [
    os.path.join(REPO, "AGENTS.md"),
    os.path.join(REPO, ".coderabbit.yaml"),
    os.path.join(OUT, "review-prompt.md"),
]
BACKOFF = [1800, 1800, 1800]
LEAF_TIMEOUT = 3600

os.makedirs(RUN, exist_ok=True)


def materialize(leaf_id, files, workdir):
    subprocess.run(["git", "init", "-q", "-b", "main", workdir], check=True)
    # .coderabbit.yaml must live inside the synthetic repo (not just -c):
    # default CLI filters ignore tests/, configs/, docs/ without it.
    import shutil
    shutil.copyfile(os.path.join(REPO, ".coderabbit.yaml"),
                    os.path.join(workdir, ".coderabbit.yaml"))
    subprocess.run(["git", "-C", workdir, "add", ".coderabbit.yaml"], check=True)
    subprocess.run(["git", "-C", workdir, "-c", "user.email=audit@local",
                    "-c", "user.name=audit", "commit", "-qm", "base"],
                   check=True)
    subprocess.run(["git", "-C", workdir, "checkout", "-qb", "review"], check=True)
    arc = subprocess.run(
        ["git", "-C", REPO, "archive", BASE, "--format=tar", "--"] + list(files),
        capture_output=True)
    if arc.returncode != 0:
        raise RuntimeError("git archive failed: " + arc.stderr.decode()[:500])
    tar_path = os.path.join(workdir, "_leaf.tar")
    with open(tar_path, "wb") as f:
        f.write(arc.stdout)
    subprocess.run(["tar", "-xf", "_leaf.tar"], cwd=workdir, check=True)
    os.remove(tar_path)
    subprocess.run(["git", "-C", workdir, "add", "-A"], check=True)
    subprocess.run(["git", "-C", workdir, "-c", "user.email=audit@local",
                    "-c", "user.name=audit", "commit", "-qm", "leaf"],
                   check=True)


def classify(log, err, rc):
    n_find = 0
    complete = False
    skipped = False
    errtxt = ""
    try:
        with open(log, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                t = ev.get("type")
                if t == "finding":
                    n_find += 1
                elif t == "complete":
                    complete = True
                    if ev.get("status") == "review_skipped":
                        skipped = True
                elif t == "error":
                    errtxt = str(ev)[:300]
    except FileNotFoundError:
        pass
    rate = False
    if not complete and os.path.exists(err):
        tail = open(err, encoding="utf-8", errors="replace").read()[-2000:]
        if "rate_limit" in tail or "rate limit" in tail.lower():
            rate = True
        if not errtxt:
            errtxt = tail[-300:]
    return n_find, complete, skipped, rate, errtxt


def quota_remaining():
    """Return included-review slots remaining, or None if unknown."""
    try:
        p = subprocess.run(["coderabbit", "usage"], capture_output=True,
                           text=True, timeout=60)
    except Exception:
        return None
    m = re.search(r"Remaining\s*:\s*(\d+)\s*of\s*(\d+)", p.stdout)
    if not m:
        return None
    return int(m.group(1))


def wait_for_quota(logp):
    """Block until at least one included review slot is free."""
    waited = 0
    while True:
        rem = quota_remaining()
        if rem is None or rem > 0:
            return rem
        logp("quota exhausted; waiting 300s (waited=%ds)" % waited)
        time.sleep(300)
        waited += 300
        if waited > 5400:
            return rem


def run_leaf(leaf_id, files):
    log = os.path.join(RUN, "review_" + leaf_id + ".jsonl")
    err = os.path.join(RUN, "review_" + leaf_id + ".stderr.txt")
    workdir = tempfile.mkdtemp(prefix="cr_" + leaf_id + "_")
    try:
        materialize(leaf_id, files, workdir)
    except Exception as e:
        return ("materialize_error", str(e))
    for attempt in range(len(BACKOFF) + 1):
        with open(log, "wb") as lo, open(err, "wb") as eo:
            try:
                p = subprocess.run(
                    ["coderabbit", "review", "--base", "main", "--agent",
                     "-c", *CONTEXT],
                    cwd=workdir, stdout=lo, stderr=eo, timeout=LEAF_TIMEOUT)
                rc = p.returncode
            except subprocess.TimeoutExpired:
                rc = -9
        n_find, complete, skipped, rate, errtxt = classify(log, err, rc)
        if complete and not skipped:
            return ("ok", "findings=%d" % n_find)
        if rate and attempt < len(BACKOFF):
            # poll quota window instead of fixed blind backoff
            waited = 0
            while True:
                rem = quota_remaining()
                if rem is None or rem > 0 or waited >= BACKOFF[attempt]:
                    break
                time.sleep(120)
                waited += 120
            continue
        if rc == -9:
            return ("timeout", errtxt)
        if skipped:
            return ("skipped", errtxt)
        return ("error", "rc=%s %s" % (rc, errtxt))
    return ("rate_limit", errtxt)


def main():
    matrix = json.load(open(os.path.join(OUT, "scope_matrix.json")))
    plog = open(os.path.join(RUN, "progress.log"), "a")

    def logp(m):
        plog.write(m + "\n")
        plog.flush()
        print(m, flush=True)

    state_p = os.path.join(RUN, "state.json")
    done = set()
    if os.path.exists(state_p):
        done = set(json.load(open(state_p)).get("ok", []))
    for leaf in matrix["leaves"]:
        lid = leaf["leaf_id"]
        if lid in done:
            logp("=== skip %s (already ok) ===" % lid)
            continue
        rem = wait_for_quota(logp)
        logp("=== start %s files=%d quota=%s %s ==="
             % (lid, len(leaf["files"]), rem, time.strftime("%H:%M:%S")))
        st, info = run_leaf(lid, leaf["files"])
        logp("=== end %s status=%s %s %s ==="
             % (lid, st, info, time.strftime("%H:%M:%S")))
        if st == "ok":
            done.add(lid)
            json.dump({"ok": sorted(done)}, open(state_p, "w"))
        time.sleep(30)
    logp("=== campaign finished ===")
    plog.close()
    # sync artifacts back to repo campaign dir
    import shutil
    for name in os.listdir(RUN):
        shutil.copy2(os.path.join(RUN, name), os.path.join(OUT, name))


if __name__ == "__main__":
    main()
