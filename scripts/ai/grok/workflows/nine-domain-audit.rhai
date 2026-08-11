// BioETL nine-domain audit fan-out (read-only by default).
// Tracked copy: scripts/ai/grok/workflows/nine-domain-audit.rhai
// Machine-local: copy to .grok/workflows/nine-domain-audit.rhai for /workflow invoke.
//
// Args (optional object):
//   domains: "all" | "docs-content,tests-system,..." (csv)
//   language: "ru" (default)
//   mode: "audit" (default)
//   audit_mode: "full" | "differential"
//   allow_issue_write: false (default) — never expands capability of agents

let meta = #{
    name: "nine-domain-audit",
    description: "Parallel BioETL domain audits (docs, tests, debt, root, GHA, agents, diagrams, docs-pipeline, architecture)",
    when_to_use: "Run the nine library audit cards in parallel and synthesize a rollup under reports/audit-runs/",
    phases: [
        #{ title: "Preflight", detail: "run_id, git safety, domain selection" },
        #{ title: "Domain audits", detail: "one read-only agent per domain card" },
        #{ title: "Synthesize", detail: "rollup scores + PROVEN findings index" },
    ],
};

let domain_schema = #{
    "type": "object",
    "required": ["domain_id", "prompt_id", "surface_score", "artifact_dir", "blocked", "summary", "findings"],
    "properties": #{
        "domain_id": #{ "type": "string" },
        "prompt_id": #{ "type": "string" },
        "surface_score": #{ "type": "integer", "minimum": 0, "maximum": 3 },
        "artifact_dir": #{ "type": "string" },
        "report_path": #{ "type": "string" },
        "findings_path": #{ "type": "string" },
        "blocked": #{ "type": "boolean" },
        "block_reason": #{ "type": "string" },
        "summary": #{ "type": "string" },
        "proven_count": #{ "type": "integer" },
        "p0_p1_count": #{ "type": "integer" },
        "findings": #{
            "type": "array",
            "maxItems": 20,
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
                    "effort": #{ "type": "string" },
                    "automation": #{ "type": "string" },
                    "automated_fix_possible": #{ "type": "boolean" },
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
    "required": ["overall_surface_score", "domain_scores", "p0_p1_count", "summary", "rollup_path"],
    "properties": #{
        "overall_surface_score": #{ "type": "integer", "minimum": 0, "maximum": 3 },
        "p0_p1_count": #{ "type": "integer" },
        "gate": #{ "type": "string" },
        "rollup_path": #{ "type": "string" },
        "findings_index_path": #{ "type": "string" },
        "summary": #{ "type": "string" },
        "domain_scores": #{
            "type": "array",
            "maxItems": 12,
            "items": #{
                "type": "object",
                "required": ["domain_id", "surface_score", "finding_count", "blocked"],
                "properties": #{
                    "domain_id": #{ "type": "string" },
                    "prompt_id": #{ "type": "string" },
                    "surface_score": #{ "type": "integer" },
                    "finding_count": #{ "type": "integer" },
                    "p0_p1_count": #{ "type": "integer" },
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
                    "remediation": #{ "type": "string" },
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

fn arg_str(a, key, default_val) {
    if a == () { return default_val; }
    let v = a[key];
    if v == () { return default_val; }
    if type_of(v) == "string" {
        if v == "" { return default_val; }
        return v;
    }
    v.to_string()
}

fn arg_bool(a, key, default_val) {
    if a == () { return default_val; }
    let v = a[key];
    if v == () { return default_val; }
    if type_of(v) == "bool" { return v; }
    if type_of(v) == "string" {
        if v == "true" || v == "1" || v == "yes" { return true; }
        if v == "false" || v == "0" || v == "no" { return false; }
    }
    default_val
}

// Canonical nine domains (order fixed for deterministic fan-out).
let ALL_DOMAINS = [
    #{
        id: "docs-content",
        prompt_id: "prompt.audit.docs-content",
        report_dir: "reports/audit/docs-content",
        scope: "README.md docs/",
        card_path: "docs/00-project/ai/prompts/library/audit/docs-content.md",
    },
    #{
        id: "tests-system",
        prompt_id: "prompt.audit.tests-system",
        report_dir: "reports/audit/tests",
        scope: "tests/ configs/quality/",
        card_path: "docs/00-project/ai/prompts/library/audit/tests-system.md",
    },
    #{
        id: "tech-debt",
        prompt_id: "prompt.audit.tech-debt",
        report_dir: "reports/audit/tech-debt",
        scope: "reports/quality/ configs/quality/ src/",
        card_path: "docs/00-project/ai/prompts/library/audit/tech-debt.md",
    },
    #{
        id: "repo-tree",
        prompt_id: "prompt.audit.repo-tree",
        report_dir: "reports/audit/repo-tree",
        scope: ".github/root-allowlist.txt scripts/ docs/00-project/governance/",
        card_path: "docs/00-project/ai/prompts/library/audit/repo-tree.md",
    },
    #{
        id: "github-actions",
        prompt_id: "prompt.audit.github-actions",
        report_dir: "reports/audit/gha",
        scope: ".github/workflows/ .github/actions/",
        card_path: "docs/00-project/ai/prompts/library/audit/github-actions.md",
    },
    #{
        id: "agents-runtime",
        prompt_id: "prompt.audit.agents-runtime",
        report_dir: "reports/audit/agents",
        scope: "AGENTS.md .codex/ .junie/ .devin/ docs/00-project/ai/",
        card_path: "docs/00-project/ai/prompts/library/audit/agents-runtime.md",
    },
    #{
        id: "diagrams",
        prompt_id: "prompt.audit.diagrams",
        report_dir: "reports/audit/diagrams",
        scope: "docs/02-architecture/diagrams/ scripts/diagrams/",
        card_path: "docs/00-project/ai/prompts/library/audit/diagrams.md",
    },
    #{
        id: "docs-pipeline",
        prompt_id: "prompt.audit.docs-pipeline",
        report_dir: "reports/audit/docs-pipeline",
        scope: "scripts/docs/ mkdocs.yml docs/",
        card_path: "docs/00-project/ai/prompts/library/audit/docs-pipeline.md",
    },
    #{
        id: "architecture-review",
        prompt_id: "prompt.architecture.review",
        report_dir: "reports/audit/architecture",
        scope: "src/bioetl/ docs/02-architecture/",
        card_path: "docs/00-project/ai/prompts/library/architecture/review-assessment.md",
    },
];

fn domain_selected(want, id) {
    if want == "all" || want == "" { return true; }
    // csv contains id as substring with separators — simple contains check
    if want == id { return true; }
    // ",id," padding
    let padded = "," + want + ",";
    let needle = "," + id + ",";
    if padded.contains(needle) { return true; }
    if want.contains(id) { return true; }
    false
}

let language = arg_str(args, "language", "ru");
let mode = arg_str(args, "mode", "audit");
let audit_mode = arg_str(args, "audit_mode", "full");
let domains_csv = arg_str(args, "domains", "all");
let allow_issue_write = arg_bool(args, "allow_issue_write", false);

if allow_issue_write {
    pause("verification", "allow_issue_write=true requires explicit operator approval; re-run with false or confirm resume after approval.");
}

phase("Preflight");
log("nine-domain-audit: language=" + language + " mode=" + mode + " domains=" + domains_csv);

let selected = [];
for d in ALL_DOMAINS {
    if domain_selected(domains_csv, d.id) {
        selected.push(d);
    }
}
if selected.len() == 0 {
    pause("verification", "No domains selected. Pass domains=all or a csv of domain ids.");
}
log("selected " + selected.len().to_string() + " domain(s)");

phase("Domain audits");
let jobs = [];
for d in selected {
    let prompt = "";
    prompt += "You are a BioETL domain auditor (read-only). ";
    prompt += "Execute the audit card at " + d.card_path + " (prompt id " + d.prompt_id + "). ";
    prompt += "Params: SCOPE=" + d.scope + "; MODE=" + mode + "; LANGUAGE=" + language + "; AUDIT_MODE=" + audit_mode + "; REQUIRE_GH_TRACKING=false. ";
    prompt += "Read AGENTS.md precedence, docs/00-project/NORMATIVE_SOURCES.md, and the card includes (evidence-contract, finding-schema, debt-budget-ban, env-guardrail). ";
    prompt += "Use tools (read_file, grep, list_dir, run_terminal_command for read-only diagnostics only). Do not edit product code. ";
    prompt += "Do NOT raise tech-debt budgets. Do NOT touch .env. Do NOT invent findings without path-level evidence (mark NOT_PROVEN). ";
    prompt += "Write artifacts under " + d.report_dir + "/ as report.md + findings.json (finding-schema). ";
    prompt += "Return structured output: domain_id=" + d.id + ", prompt_id, surface_score 0-3, artifact_dir, blocked, summary, findings array (max 20 PROVEN preferred), top_remediations. ";
    prompt += "Answer narrative in " + language + "; keep paths/commands in original form.";
    jobs.push(#{
        prompt: prompt,
        label: "audit:" + d.id,
        capability_mode: "read-only",
        output_schema: domain_schema,
    });
}

let results = parallel(jobs);

let domain_outputs = [];
let i = 0;
for r in results {
    let d = selected[i];
    if r == () || !r.success || r.output == () {
        log("domain failed or empty: " + d.id);
        domain_outputs.push(#{
            domain_id: d.id,
            prompt_id: d.prompt_id,
            surface_score: 0,
            artifact_dir: d.report_dir,
            blocked: true,
            block_reason: "agent_failed_or_empty",
            summary: "Domain agent failed or returned empty output",
            proven_count: 0,
            p0_p1_count: 0,
            findings: [],
            top_remediations: ["Re-run domain card manually: " + d.prompt_id],
        });
    } else {
        domain_outputs.push(r.output);
    }
    i += 1;
}

// Persist a compact JSON of domain outputs for the synthesizer
let domains_json = json_encode(domain_outputs);
let domains_blob_path = write_scratch_file("domain-outputs.json", domains_json);

phase("Synthesize");
let syn_prompt = "";
syn_prompt += "Synthesize BioETL nine-domain audit results. ";
syn_prompt += "Input JSON (domain agent outputs) is in scratch file domain-outputs.json (also embedded below). ";
syn_prompt += "Read each domain report_dir if present on disk (report.md / findings.json) and reconcile with agent outputs. ";
syn_prompt += "Compute overall_surface_score as the MIN of domain surface_scores (fail-closed). ";
syn_prompt += "Count p0_p1 across PROVEN findings only. ";
syn_prompt += "Write rollup to reports/audit-runs/latest-nine-domain/final-summary.md and findings-index.json (create dirs). ";
syn_prompt += "If write is not possible, put full markdown in summary and set rollup_path to the intended path. ";
syn_prompt += "Guards: no debt budget raises, no secrets, no invented findings. Language=" + language + ". ";
syn_prompt += "Domain outputs JSON: " + domains_json;

let syn = agent(syn_prompt, #{
    label: "synthesize-rollup",
    capability_mode: "read-write",
    output_schema: synthesis_schema,
});

if syn == () || !syn.success || syn.output == () {
    complete(#{
        ok: false,
        domains_blob: domains_blob_path,
        domain_count: domain_outputs.len(),
        error: "synthesis_failed",
        domains: domain_outputs,
    });
}

complete(#{
    ok: true,
    domains_blob: domains_blob_path,
    domain_count: domain_outputs.len(),
    synthesis: syn.output,
    domains: domain_outputs,
});
