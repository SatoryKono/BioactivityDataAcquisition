from pathlib import Path
from docx import Document
import re

docx_path = Path(
    r"C:\Users\Fedor\Desktop\bioetl_prompt_system_kernel_v3_full_portfolio_formatted_v2.1.docx"
)
doc = Document(str(docx_path))
paras = doc.paragraphs

prompt_indices = []
for i, p in enumerate(paras):
    if p.style.name == "Heading 2" and re.match(r"1\.\d+\.", p.text.strip()):
        prompt_indices.append(i)

end1 = None
for i, p in enumerate(paras):
    if p.style.name == "Heading 1" and p.text.strip().startswith("2."):
        end1 = i
        break

print("prompts", len(prompt_indices), "end1", end1)

out_dir = Path("docs/00-project/ai/prompts/library/audit/project/materialized-v3")
out_dir.mkdir(parents=True, exist_ok=True)

entries = []

for idx, start in enumerate(prompt_indices):
    end = prompt_indices[idx + 1] if idx + 1 < len(prompt_indices) else end1
    raw = paras[start:end]
    lines = [p.text for p in raw]
    full = "\n".join(lines)
    m = re.search(r"---\s*\n\s*id:\s*prompt\.", full)
    if m:
        usable = full[m.start() :].strip()
        header = raw[0].text
        source_line = ""
        for p in raw[1:6]:
            if "Источник:" in p.text or "Commit" in p.text:
                source_line += p.text + " "
        usable = (
            "<!-- " + header.strip() + " | " + source_line.strip() + " -->\n\n" + usable
        )
    else:
        usable = full

    id_match = re.search(r"id:\s*(prompt\.[^\n]+)", full)
    pid = id_match.group(1).strip() if id_match else "prompt-" + str(idx + 1).zfill(2)

    num = idx + 1
    slug_map = {
        1: "01-docs",
        2: "02-diagrams",
        3: "03-agents-memory",
        4: "04-configs",
        5: "05-tests",
        6: "06-tech-debt",
        7: "07-architecture",
        8: "08-telemetry",
        9: "09-dashboards",
        10: "10-coderabbit",
        11: "11-medallion",
        12: "12-dq-contracts",
        13: "13-control-plane",
        14: "14-providers",
        15: "15-http-clients",
        16: "16-normalization",
        17: "17-cli-compat",
        18: "18-security-secrets",
        19: "19-vcr-http",
        20: "20-qa-gates",
        21: "21-github-actions",
        22: "22-requirements-trace",
        23: "23-ops-runbooks",
        24: "24-scripts-inventory",
    }
    slug = slug_map[num]
    fname = slug + "__" + pid + ".md"
    target = out_dir / fname
    target.write_text(usable, encoding="utf-8")
    print("Wrote", str(target), "len", len(usable), "pid", pid)
    entries.append((num, slug, pid, fname, header))

# master
master_start = None
master_end = None
for i, p in enumerate(paras):
    if p.style.name == "Heading 2" and "5.6." in p.text:
        master_start = i
    if (
        master_start is not None
        and i > master_start
        and p.style.name.startswith("Heading")
    ):
        if "5.7." in p.text or p.text.strip().startswith("ПРИЛОЖЕНИЕ"):
            master_end = i
            break

print("master", master_start, "->", master_end)

if master_start and master_end:
    raw = paras[master_start:master_end]
    full = "\n".join(p.text for p in raw)
    m = re.search(r"# BIOETL FULL PROJECT AUDIT ORCHESTRATOR", full)
    if m:
        usable = full[m.start() :].strip()
        header = raw[0].text
        usable = (
            "<!-- "
            + header.strip()
            + " | Source: bioetl_prompt_system_kernel_v3_full_portfolio_formatted_v2.1.docx -->\n\n"
            + usable
        )
    else:
        usable = full
    target = out_dir / "master-orchestrator-v1__full-project-audit.md"
    target.write_text(usable, encoding="utf-8")
    print("Wrote master", str(target), "len", len(usable))
    entries.append((99, "master", "master-orchestrator-v1", target.name, "master"))

# README
readme = []
readme.append("# Materialized v3 — 24 циклических промпта + Master Orchestrator")
readme.append("")
readme.append(
    "Источник: `C:/Users/Fedor/Desktop/bioetl_prompt_system_kernel_v3_full_portfolio_formatted_v2.1.docx`"
)
readme.append(
    "Дата генерации: 28.08.2026 | ID документа: BIOETL-PROMPT-ARCH-KERNEL-V3-003"
)
readme.append("Repository baseline: `main @ 3aba8559a58038cd9ff9a90621f19ea39b930a2f`")
readme.append(
    "Профиль материализации: `MODE=full`, `ALLOW_ISSUE_WRITE/PUSH/MERGE/CLOSE=true` (fail-closed kernel + explicit full-write profile)"
)
readme.append("")
readme.append(
    "> Полные self-contained тексты — front matter + includes сведены в один copy-paste-ready текст. Источник: `docs/00-project/ai/prompts/library/audit/` на baseline-коммите."
)
readme.append("")
readme.append("## Состав")
readme.append("")
readme.append("| № | Объект | Prompt ID | Файл | Source path* | Score |")
readme.append("|---|---|---|---|---|---|")

table_data = [
    ("01", "Документация", "prompt.audit.cycle.docs", "cycle/docs.md", "8.87"),
    ("02", "Диаграммы", "prompt.audit.cycle.diagrams", "cycle/diagrams.md", "8.77"),
    (
        "03",
        "Агенты и память",
        "prompt.audit.cycle.agents-memory",
        "cycle/agents-memory.md",
        "8.81",
    ),
    ("04", "Конфигурация", "prompt.audit.cycle.configs", "cycle/configs.md", "8.73"),
    ("05", "Тестовая система", "prompt.audit.cycle.tests", "cycle/tests.md", "8.79"),
    (
        "06",
        "Технический долг",
        "prompt.audit.cycle.tech-debt",
        "cycle/tech-debt.md",
        "8.76",
    ),
    (
        "07",
        "Архитектура",
        "prompt.audit.cycle.architecture",
        "cycle/architecture.md",
        "9.12",
    ),
    ("08", "Телеметрия", "prompt.audit.cycle.telemetry", "cycle/telemetry.md", "8.84"),
    ("09", "Дашборды", "prompt.audit.cycle.dashboards", "cycle/dashboards.md", "8.98"),
    (
        "10",
        "Полный проект + CodeRabbit",
        "prompt.audit.cycle.coderabbit",
        "cycle/coderabbit.md",
        "9.23",
    ),
    (
        "11",
        "Medallion / write-path",
        "prompt.audit.project.new2.medallion",
        "project/new2/01-medallion.md",
        "8.68",
    ),
    (
        "12",
        "DQ / Pandera / Gold-контракты",
        "prompt.audit.project.new2.dq-contracts",
        "project/new2/02-dq-contracts.md",
        "8.64",
    ),
    (
        "13",
        "Control plane / replay / resume",
        "prompt.audit.project.new2.control-plane",
        "project/new2/03-control-plane.md",
        "8.68",
    ),
    (
        "14",
        "Провайдеры и каталог сущностей",
        "prompt.audit.project.new2.providers",
        "project/new2/04-providers.md",
        "8.45",
    ),
    (
        "15",
        "HTTP-клиенты и адаптеры",
        "prompt.audit.project.new2.http-clients",
        "project/new2/05-http-clients.md",
        "8.60",
    ),
    (
        "16",
        "Нормализация и идентификаторы",
        "prompt.audit.project.new2.normalization",
        "project/new2/06-normalization.md",
        "8.46",
    ),
    (
        "17",
        "CLI / HTTP public compatibility",
        "prompt.audit.project.new2.cli-compat",
        "project/new2/07-cli-compat.md",
        "8.41",
    ),
    (
        "18",
        "Безопасность и секреты",
        "prompt.audit.project.new2.security-secrets",
        "project/new2/08-security-secrets.md",
        "8.63",
    ),
    (
        "19",
        "VCR / HTTP fixtures",
        "prompt.audit.project.new2.vcr-http",
        "project/new2/09-vcr-http.md",
        "8.60",
    ),
    (
        "20",
        "QA gates и scorecard freshness",
        "prompt.audit.project.new2.qa-gates",
        "project/new2/10-qa-gates.md",
        "8.66",
    ),
    (
        "21",
        "GitHub Actions",
        "prompt.audit.project.new2.github-actions",
        "project/new2/11-github-actions.md",
        "8.57",
    ),
    (
        "22",
        "REQ-* traceability",
        "prompt.audit.project.new2.requirements-trace",
        "project/new2/12-requirements-trace.md",
        "8.60",
    ),
    (
        "23",
        "Operations / runbooks",
        "prompt.audit.project.new2.ops-runbooks",
        "project/new2/13-ops-runbooks.md",
        "8.45",
    ),
    (
        "24",
        "Scripts inventory / lifecycle",
        "prompt.audit.project.new2.scripts-inventory",
        "project/new2/14-scripts-inventory.md",
        "8.59",
    ),
]

for n, obj, pid, path, score in table_data:
    fname = [e[3] for e in entries if pid in e[2]]
    fname = fname[0] if fname else ""
    readme.append(
        "| "
        + n
        + " | "
        + obj
        + " | `"
        + pid
        + "` | ["
        + fname
        + "]("
        + fname
        + ") | `"
        + path
        + "` | "
        + score
        + " |"
    )

readme.append("")
readme.append(
    "**Master orchestrator:** [`master-orchestrator-v1__full-project-audit.md`](master-orchestrator-v1__full-project-audit.md) — последовательный запуск всех 24 циклов (01→24 + POST_AUDIT)."
)
readme.append("")
readme.append("## Как использовать")
readme.append("")
readme.append(
    "1. Один домен: вставь соответствующий `NN-*__prompt.*.md` как operator-paste."
)
readme.append(
    "2. Полный прогон 24: вставь `master-orchestrator-v1__full-project-audit.md`. Он резолвит 24 prompt_id из registry, рендерит с `MODE=full` и `ALLOW_*=true`, ведёт `master-ledger.jsonl`."
)
readme.append("3. Baseline: `main @ 3aba8559` — сверяй drift перед стартом.")
readme.append("")
readme.append("## Примечание")
readme.append("")
readme.append(
    "- Файлы — материализации на 28.08.2026. Source of truth — карточки в `library/audit/cycle/` и `library/audit/project/new2/`. Не редактируй materialized-файлы вручную; они — снапшот."
)
readme.append(
    "- Профиль `MODE=full, ALLOW_*=true` — explicit operator override, не library default (kernel остаётся fail-closed)."
)
readme.append(
    "- Артефакты циклов: `reports/audit-runs/<run_id>/` — см. каждый промпт раздел Outputs."
)

(out_dir / "README.md").write_text("\n".join(readme), encoding="utf-8")
print("Wrote README", str(out_dir / "README.md"))

for f in sorted(out_dir.iterdir()):
    print(f.name, f.stat().st_size)
