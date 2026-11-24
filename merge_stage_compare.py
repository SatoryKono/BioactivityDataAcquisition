import pathlib, re, subprocess
root = "D:/github/BioactivityDataAcquisition"
files = [
"configs/quality/external_resource_inventory.json",
"configs/quality/external_resource_inventory/part-01.json",
"configs/quality/external_resource_inventory/part-02.json",
"configs/quality/external_resource_inventory/part-03.json",
"configs/quality/external_resource_inventory/part-04.json",
"configs/quality/external_resource_inventory/part-05.json",
"configs/quality/external_resource_inventory/part-06.json",
"reports/quality/external-resource-inventory.md",
]
hex40 = re.compile(r"[0-9a-f]{40}")
hex64 = re.compile(r"[0-9a-f]{64}")
def show(stage, f):
    p = subprocess.run(["git","-c","safe.directory="+root,"show","%s:%s"%(stage,f)],
        cwd=root,capture_output=True)
    return p.stdout.decode("utf-8",errors="replace") if p.returncode==0 else None
def norm(s):
    s = hex40.sub("<C>",s); s = hex64.sub("<H>",s); return s
for f in files:
    b1=show(":1:",f); b2=show(":2:",f); b3=show(":3:",f)
    w=pathlib.Path(root,f).read_text(encoding="utf-8",errors="replace")
    tag = "worktree==stage2" if w==b2 else ("worktree==stage3" if w==b3 else ("worktree==stage1" if w==b1 else "worktree==NONE"))
    n2=norm(b2) if b2 else None; n3=norm(b3) if b3 else None
    same = "STAMP-ONLY" if (n2==n3) else "STRUCTURAL"
    print("%s | %s | %s | len2=%s len3=%s"%(
        f,tag,same,len(b2 or ""),len(b3 or "")))
