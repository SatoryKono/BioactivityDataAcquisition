#!/usr/bin/env python3
"""Generate .grok/workflows/project-domain-audit.rhai (operator helper; not runtime SSOT)."""

from __future__ import annotations

from pathlib import Path

RHAI = r"""let meta = #{
    name: "project-domain-audit",
    description: "Nine-domain BioETL project audit: docs, tests, debt, root, GHA, agents, diagrams, docs-pipeline, architecture",
    when_to_use: "Run multi-domain audit via Prompt Library cards under docs/00-project/ai/prompts/library/",
    phases: [
        #{ title: "Preflight", detail: "resolve args, domain list, run_id, artifact root" },
        #{ title: "Domain audits", detail: "parallel domain agents from library cards" },
        #{ title: "Synthesize", detail: "merge findings, surface scores, top remediations" },
        #{ title: "Final", detail: "write rollup under reports/audit/project-domain/" },
    ],
};

let domain_result_schema = #{
    "type": "object",
    "required": ["domain_id", "prompt_id", "surface_score", "findings", "artifact_dir", "blocked", "summary"],
    "properties": #{
        "domain_id": #{ "type": "string" },
        "prompt_id": #{ "type": "string" },
        "surface_score": #{ "type": "integer", "minimum": 0, "maximum": 3 },
        "artifact_dir": #{ "type": "string" },
        "blocked": #{ "type": "boolean" },
        "block_reason": #{ "type": "string" },
        "summary": #{ "type": "string" },
        "findings": #{
            "type": "array",
            "maxItems": 24,
            "items": #{
                "type": "object",
                "required": ["id", "path", "observation", "status", "priority"],
                "properties": #{
                    "id": #{ "type": "string" },
                    "path": #{ "type": "string" },
                    "observation": #{ "type": "string" },
                    "method": #{ "type": "string" },
                    "expected": #{ "type": "string" },
                    "actual": #{ "type": "string" },
                    "impact": #{ "type": "string" },
                    "status": #{ "type": "string" },
                    "priority": #{ "type": "string" },
                    "severity": #{ "type": "string" },
                    "confidence": #{ "type": "string" },
                    "remediation": #{ "type": "string" },
                    "automation": #{ "type": "string" },
                },
            },
        },
        "top_remediations": #{
            "type": "array",
            "maxItems": 8,
            "items": #{ "type": "string" },
        },
    },
};

let synthesis_schema = #{
    "type": "object",
    "required": ["overall_surface_score", "domain_scores", "p0_p1_count", "top_findings", "rollup_path", "summary"],
    "properties": #{
        "overall_surface_score": #{ "type": "integer", "minimum": 0, "maximum": 3 },
        "p0_p1_count": #{ "type": "integer" },
        "rollup_path": #{ "type": "string" },
        "summary": #{ "type": "string" },
        "domain_scores": #{
            "type": "array",
            "maxItems": 12,
            "items": #{
                "type": "object",
                "required": ["domain_id", "surface_score", "finding_count", "blocked"],
                "properties": #{
                    "domain_id": #{ "type": "string" },
                    "surface_score": #{ "type": "integer" },
                    "finding_count": #{ "type": "integer" },
                    "blocked": #{ "type": "boolean" },
                },
            },
        },
        "top_findings": #{
            "type": "array",
            "maxItems": 20,
            "items": #{
                "type": "object",
                "required": ["domain_id", "id", "priority", "path", "observation"],
                "properties": #{
                    "domain_id": #{ "type": "string" },
                    "id": #{ "type": "string" },
                    "priority": #{ "type": "string" },
                    "path": #{ "type": "string" },
                    "observation": #{ "type": "string" },
                },
            },
        },
        "recommended_next_steps": #{
            "type": "array",
            "maxItems": 12,
            "items": #{ "type": "string" },
        },
    },
};

let mode = "audit";
let language = "ru";
let domains_arg = "all";
let require_gh = "false";
let run_id_arg = "";

if args != () {
    if args.mode != () { mode = args.mode; }
    if args.language != () { language = args.language; }
    if args.domains != () { domains_arg = args.domains; }
    if args.require_gh_tracking != () { require_gh = args.require_gh_tracking; }
    if args.run_id != () { run_id_arg = args.run_id; }
}

if mode != "audit" && mode != "propose-patches" {
    pause("verification", "args.mode must be audit or propose-patches (default audit).");
}

let all_ids = [
    "docs-content",
    "tests-system",
    "tech-debt",
    "repo-tree",
    "github-actions",
    "agents-runtime",
    "diagrams",
    "docs-pipeline",
    "architecture",
];
let all_prompts = [
    "docs/00-project/ai/prompts/library/audit/docs-content.md",
    "docs/00-project/ai/prompts/library/audit/tests-system.md",
    "docs/00-project/ai/prompts/library/audit/tech-debt.md",
    "docs/00-project/ai/prompts/library/audit/repo-tree.md",
    "docs/00-project/ai/prompts/library/audit/github-actions.md",
    "docs/00-project/ai/prompts/library/audit/agents-runtime.md",
    "docs/00-project/ai/prompts/library/audit/diagrams.md",
    "docs/00-project/ai/prompts/library/audit/docs-pipeline.md",
    "docs/00-project/ai/prompts/library/architecture/review-assessment.md",
];
let all_prompt_ids = [
    "prompt.audit.docs-content",
    "prompt.audit.tests-system",
    "prompt.audit.tech-debt",
    "prompt.audit.repo-tree",
    "prompt.audit.github-actions",
    "prompt.audit.agents-runtime",
    "prompt.audit.diagrams",
    "prompt.audit.docs-pipeline",
    "prompt.architecture.review",
];
let all_scopes = [
    "README.md docs/",
    "tests/ pyproject.toml",
    "src/ configs/quality/",
    ".",
    ".github/workflows",
    "AGENTS.md .codex/ .junie/ .devin/ docs/00-project/ai/ scripts/",
    "docs/ scripts/",
    "mkdocs.yml scripts/ docs/",
    "src/bioetl docs/02-architecture/",
];
let all_artifacts = [
    "reports/audit/docs-content",
    "reports/audit/tests",
    "reports/audit/tech-debt",
    "reports/audit/repo-tree",
    "reports/audit/gha",
    "reports/audit/agents",
    "reports/audit/diagrams",
    "reports/audit/docs-pipeline",
    "reports/audit/architecture",
];

let selected = [];
if domains_arg == "all" || domains_arg == "" {
    let i = 0;
    while i < all_ids.len() {
        selected.push(i);
        i += 1;
    }
} else {
    let i = 0;
    while i < all_ids.len() {
        let id = all_ids[i];
        if domains_arg.contains(id) {
            selected.push(i);
        }
        i += 1;
    }
}

if selected.len() == 0 {
    pause("verification", "No domains selected. Use args.domains=all or comma-separated domain ids.");
}

phase("Preflight");
log("project-domain-audit: mode=" + mode + " language=" + language + " domains=" + selected.len().to_string());

let run_id = run_id_arg;
if run_id == "" {
    run_id = "project-domain-audit";
}
let rollup_dir = "reports/audit/project-domain/" + run_id;

phase("Domain audits");
let jobs = [];
let j = 0;
while j < selected.len() {
    let idx = selected[j];
    let domain_id = all_ids[idx];
    let card_path = all_prompts[idx];
    let prompt_id = all_prompt_ids[idx];
    let scope = all_scopes[idx];
    let art = all_artifacts[idx];

    let p = "";
    p += "You are a BioETL domain auditor. MODE=" + mode + ". LANGUAGE=" + language + ".\n";
    p += "REQUIRE_GH_TRACKING=" + require_gh + " (do not create GitHub issues unless true).\n";
    p += "Do NOT raise debt budgets, edit .env, or put secrets in reports.\n";
    p += "If MODE=propose-patches: list minimal patch ideas only; do not apply without approval.\n\n";
    p += "DOMAIN_ID=" + domain_id + "\n";
    p += "PROMPT_ID=" + prompt_id + "\n";
    p += "CARD (read fully first with read_file): " + card_path + "\n";
    p += "Also read: docs/00-project/ai/prompts/fragments/finding-schema.md\n";
    p += "Also read: docs/00-project/ai/prompts/fragments/audit-scale.md\n";
    p += "Also read: docs/00-project/ai/prompts/fragments/reports-output.md\n";
    p += "SCOPE=" + scope + "\n";
    p += "ARTIFACT_DIR=" + art + "\n\n";
    p += "Method:\n";
    p += "1) Read the card and follow its Method/Checklist.\n";
    p += "2) Use grep, read_file, list_dir, and safe run_terminal_command for evidence.\n";
    p += "3) Findings need path-level evidence; status PROVEN or NOT_PROVEN; priority P0-P3.\n";
    p += "4) BioETL facts: Python/pytest/GHA/local-only; root-allowlist; debt budgets must not increase.\n";
    p += "5) Write " + art + "/report.md and " + art + "/findings.json.\n";
    p += "6) Return structured output matching the schema.\n";
    p += "Empty findings is valid only after real inventory of SCOPE.\n";

    jobs.push(#{
        prompt: p,
        label: "audit:" + domain_id,
        capability_mode: "read-write",
        output_schema: domain_result_schema,
    });
    j += 1;
}

let results = parallel(jobs);

let domain_outputs = [];
let failed_domains = [];
let k = 0;
while k < results.len() {
    let r = results[k];
    let idx = selected[k];
    let domain_id = all_ids[idx];
    if r == () || !r.success || r.output == () {
        failed_domains.push(domain_id);
        log("domain failed or empty: " + domain_id);
    } else {
        domain_outputs.push(r.output);
    }
    k += 1;
}

if domain_outputs.len() == 0 {
    complete(#{
        summary: "All domain audits failed or returned empty.",
        failed_domains: failed_domains,
        rollup_dir: rollup_dir,
    });
}

phase("Synthesize");
let synth_prompt = "";
synth_prompt += "You synthesize a multi-domain BioETL project audit.\n";
synth_prompt += "LANGUAGE=" + language + ".\n";
synth_prompt += "Read domain reports under reports/audit/*/report.md when present.\n";
synth_prompt += "Domain agent outputs (re-check top P0/P1 paths with tools):\n";
synth_prompt += json_encode(domain_outputs) + "\n\n";
synth_prompt += "Failed domains: " + json_encode(failed_domains) + "\n\n";
synth_prompt += "Tasks:\n";
synth_prompt += "1) domain_scores: domain_id, surface_score, finding_count, blocked.\n";
synth_prompt += "2) top_findings max 20, sort P0 then P1 then P2; PROVEN only.\n";
synth_prompt += "3) overall_surface_score = minimum of domain surface_scores that ran.\n";
synth_prompt += "4) p0_p1_count among PROVEN findings.\n";
synth_prompt += "5) Write " + rollup_dir + "/rollup.md and " + rollup_dir + "/findings-index.json.\n";
synth_prompt += "6) recommended_next_steps max 12.\n";
synth_prompt += "Do not raise debt budgets. REQUIRE_GH_TRACKING=" + require_gh + ".\n";
synth_prompt += "Return the synthesis schema fields.\n";

let synth = agent(synth_prompt, #{
    label: "synthesize",
    capability_mode: "read-write",
    output_schema: synthesis_schema,
});

phase("Final");
if synth == () || !synth.success || synth.output == () {
    let path = write_scratch_file("project-domain-audit-partial.md", "Synthesis failed; domain outputs may still exist under reports/audit/.");
    complete(#{
        summary: "Domain audits finished with partial results; synthesis failed.",
        failed_domains: failed_domains,
        domain_count: domain_outputs.len(),
        path: path,
        rollup_dir: rollup_dir,
    });
}

let out = synth.output;
let summary_text = out.summary;
if summary_text == () {
    summary_text = "Project domain audit complete.";
}

let md = "# Project domain audit rollup\n\n";
md += summary_text + "\n\n";
md += "- overall_surface_score: " + out.overall_surface_score.to_string() + "\n";
md += "- p0_p1_count: " + out.p0_p1_count.to_string() + "\n";
md += "- rollup_path: " + out.rollup_path + "\n";
md += "- failed_domains: " + json_encode(failed_domains) + "\n";
let scratch = write_scratch_file("project-domain-audit-summary.md", md);

log("project-domain-audit done: score=" + out.overall_surface_score.to_string());

complete(#{
    summary: summary_text,
    overall_surface_score: out.overall_surface_score,
    p0_p1_count: out.p0_p1_count,
    domain_scores: out.domain_scores,
    top_findings: out.top_findings,
    recommended_next_steps: out.recommended_next_steps,
    rollup_path: out.rollup_path,
    rollup_dir: rollup_dir,
    failed_domains: failed_domains,
    path: scratch,
});
"""


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    out = root / ".grok" / "workflows" / "project-domain-audit.rhai"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(RHAI.lstrip("\n"), encoding="utf-8", newline="\n")
    print(f"wrote {out} ({len(RHAI.splitlines())} lines)")


if __name__ == "__main__":
    main()
