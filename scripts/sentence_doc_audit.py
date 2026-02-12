from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
SRC_DIRS = [
    ROOT / "src",
    ROOT / "tests",
    ROOT / "configs",
    ROOT / "pyproject.toml",
    ROOT / "mkdocs.yml",
]
OUT_DIR = ROOT / "reports" / "documentation_audit"
OUT_CSV = OUT_DIR / "sentence_audit_full.csv"
OUT_MD = OUT_DIR / "sentence_audit_summary.md"
OUT_PROMPTS = OUT_DIR / "document_update_prompts.md"


STOPWORDS = {
    "и",
    "в",
    "во",
    "на",
    "по",
    "для",
    "из",
    "к",
    "с",
    "со",
    "а",
    "но",
    "или",
    "как",
    "что",
    "это",
    "при",
    "не",
    "да",
    "нет",
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "are",
    "was",
    "were",
    "into",
    "your",
    "using",
    "use",
}


CODE_FILE_GLOBS = ("*.py", "*.yml", "*.yaml", "*.toml", "*.json", "*.ini")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9_][A-Za-zА-Яа-яЁё0-9_\-]{2,}")
BACKTICK_RE = re.compile(r"`([^`]+)`")


@dataclass(frozen=True)
class Evidence:
    path: Path
    line_no: int
    line: str
    score: int


def iter_doc_files() -> list[Path]:
    files = sorted((ROOT / "docs").rglob("*.md"))
    for extra in (ROOT / "README.md", ROOT / "docs" / "01-requirements" / "REQUIREMENTS.md"):
        if extra.exists():
            files.append(extra)
    # Deduplicate preserving deterministic order
    seen: set[Path] = set()
    result: list[Path] = []
    for p in files:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            result.append(rp)
    return sorted(result, key=lambda p: str(p).lower())


def clean_markdown_line(line: str) -> str:
    s = line.strip()
    s = re.sub(r"^\s{0,3}#{1,6}\s*", "", s)
    s = re.sub(r"^\s*[-*+]\s+", "", s)
    s = re.sub(r"^\s*\d+\.\s+", "", s)
    if "|" in s and re.search(r"\|", s):
        s = " ".join(part.strip() for part in s.split("|") if part.strip() and not set(part.strip()) <= {"-"})
    s = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_sentences(md_text: str) -> list[str]:
    sentences: list[str] = []
    in_code = False
    for raw_line in md_text.splitlines():
        line = raw_line.rstrip()
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        cleaned = clean_markdown_line(line)
        if not cleaned:
            continue
        parts = SENTENCE_SPLIT_RE.split(cleaned)
        for part in parts:
            s = part.strip()
            if len(s) < 8:
                continue
            if not re.search(r"[A-Za-zА-Яа-яЁё]", s):
                continue
            sentences.append(s)
    return sentences


def tokenize(text: str) -> list[str]:
    tokens = [t.lower() for t in TOKEN_RE.findall(text)]
    return [t for t in tokens if len(t) >= 4 and t not in STOPWORDS]


def iter_code_files() -> Iterable[Path]:
    for src in SRC_DIRS:
        if src.is_file():
            yield src
            continue
        if not src.exists():
            continue
        for glob in CODE_FILE_GLOBS:
            for p in src.rglob(glob):
                if ".venv" in p.parts or "__pycache__" in p.parts:
                    continue
                yield p


def build_index() -> tuple[dict[str, set[int]], list[tuple[Path, int, str]], Counter]:
    lines: list[tuple[Path, int, str]] = []
    inverted: dict[str, set[int]] = defaultdict(set)
    freq: Counter = Counter()

    for file_path in sorted(iter_code_files(), key=lambda p: str(p).lower()):
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        for i, line in enumerate(text.splitlines(), start=1):
            idx = len(lines)
            lines.append((file_path, i, line))
            tks = set(tokenize(line))
            for tk in tks:
                inverted[tk].add(idx)
                freq[tk] += 1
    return inverted, lines, freq


def find_evidence(
    sentence: str,
    inverted: dict[str, set[int]],
    lines: list[tuple[Path, int, str]],
    freq: Counter,
) -> Evidence | None:
    backticks = [x.strip() for x in BACKTICK_RE.findall(sentence) if x.strip()]
    sentence_tokens = tokenize(sentence)
    ranked_tokens = sorted(sentence_tokens, key=lambda t: (freq.get(t, 10**9), t))
    probe_tokens = ranked_tokens[:5]

    candidate_ids: set[int] = set()
    for token in probe_tokens:
        candidate_ids |= inverted.get(token, set())

    # Prefer exact backtick references if they exist as path fragments.
    for idx, (path, line_no, line) in enumerate(lines):
        for bt in backticks:
            if bt and bt in str(path).replace("\\", "/"):
                return Evidence(path=path, line_no=line_no, line=line.strip(), score=10)
            if bt and bt in line:
                return Evidence(path=path, line_no=line_no, line=line.strip(), score=9)

    if not candidate_ids:
        return None

    best: Evidence | None = None
    for idx in sorted(candidate_ids):
        path, line_no, line = lines[idx]
        line_tokens = set(tokenize(line))
        score = sum(1 for token in probe_tokens if token in line_tokens)
        if score <= 0:
            continue
        candidate = Evidence(path=path, line_no=line_no, line=line.strip(), score=score)
        if best is None or (candidate.score, str(candidate.path), candidate.line_no) > (
            best.score,
            str(best.path),
            -best.line_no,
        ):
            best = candidate
    return best


def status_for(sentence: str, evidence: Evidence | None) -> str:
    if evidence is None:
        return "нет"
    numbers = re.findall(r"\d+", sentence)
    if numbers and not any(n in evidence.line for n in numbers):
        return "нет"
    if evidence.score >= 2:
        return "да"
    return "нет"


def plan_for(status: str) -> str:
    if status == "да":
        return "Утверждение подтверждено; добавить/сохранить явную ссылку на код в документе."
    return (
        "Проверить утверждение вручную: либо скорректировать текст документа под текущий код, "
        "либо реализовать отсутствующее поведение и добавить тест."
    )


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def generate() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc_files = iter_doc_files()
    inverted, lines, freq = build_index()

    rows: list[dict[str, str]] = []
    prompt_map: dict[str, list[dict[str, str]]] = defaultdict(list)

    for doc in doc_files:
        text = doc.read_text(encoding="utf-8")
        sentences = extract_sentences(text)
        for i, sentence in enumerate(sentences, start=1):
            evidence = find_evidence(sentence, inverted, lines, freq)
            status = status_for(sentence, evidence)
            code_link = ""
            code_fragment = ""
            if evidence is not None:
                code_link = f"{rel(evidence.path)}:{evidence.line_no}"
                code_fragment = evidence.line[:280]
            row = {
                "документ": rel(doc),
                "номер предложения": str(i),
                "предложение": sentence,
                "ссылка на код (файл строки)": code_link,
                "код (фрагмент)": code_fragment,
                "описание соответствует кода (да/нет)": status,
                "предлагаемый план устранения несоответствий": plan_for(status),
            }
            rows.append(row)
            if status == "нет":
                prompt_map[rel(doc)].append(row)

    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "документ",
                "номер предложения",
                "предложение",
                "ссылка на код (файл строки)",
                "код (фрагмент)",
                "описание соответствует кода (да/нет)",
                "предлагаемый план устранения несоответствий",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    ok = sum(1 for r in rows if r["описание соответствует кода (да/нет)"] == "да")
    bad = total - ok

    generated_at = datetime.now(UTC).isoformat()
    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write("# Исчерпывающий аудит документации (sentence-by-sentence)\n\n")
        f.write(f"- Дата (UTC): {generated_at}\n")
        f.write(f"- Документов: {len(doc_files)}\n")
        f.write(f"- Проверено предложений: {total}\n")
        f.write(f"- Соответствует коду: {ok}\n")
        f.write(f"- Не соответствует / не подтверждено автоматически: {bad}\n")
        f.write(f"- Полный CSV: `{rel(OUT_CSV)}`\n\n")
        f.write("## Топ-20 документов с максимальным числом несоответствий\n\n")
        bad_by_doc = Counter(r["документ"] for r in rows if r["описание соответствует кода (да/нет)"] == "нет")
        f.write("| Документ | Несоответствий |\n")
        f.write("|---|---:|\n")
        for doc_name, cnt in bad_by_doc.most_common(20):
            f.write(f"| `{doc_name}` | {cnt} |\n")

    with OUT_PROMPTS.open("w", encoding="utf-8") as f:
        f.write("# Набор промптов для модификации документов\n\n")
        f.write("Ниже шаблоны для каждого документа, где найдены несоответствия.\n\n")
        for doc_name in sorted(prompt_map):
            mismatches = prompt_map[doc_name]
            f.write(f"## {doc_name}\n\n")
            f.write("```text\n")
            f.write(
                "Проверь и обнови документ в соответствии с кодом.\n"
                f"Файл: {doc_name}\n\n"
                "Требования:\n"
                "1) Для каждого пункта ниже либо исправь формулировку, либо укажи TODO на реализацию в коде.\n"
                "2) Добавь явные ссылки на код (файл:строка).\n"
                "3) Не меняй публичные контракты без migration note.\n\n"
                "Проблемные предложения:\n"
            )
            for m in mismatches[:50]:
                f.write(
                    f"- [{m['номер предложения']}] {m['предложение']}\n"
                    f"  - Текущее доказательство: {m['ссылка на код (файл строки)'] or 'нет'}\n"
                )
            if len(mismatches) > 50:
                f.write(f"- ... и еще {len(mismatches) - 50} предложений (см. полный CSV-отчет)\n")
            f.write("```\n\n")


if __name__ == "__main__":
    generate()
