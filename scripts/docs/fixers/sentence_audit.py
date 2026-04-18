#!/usr/bin/env python3
"""Generate a sentence-by-sentence documentation audit against code evidence."""

from __future__ import annotations

import argparse
import csv
import os
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
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
OUT_PROMPTS_HIGH = OUT_DIR / "document_update_prompts_high_risk.md"

DOC_FIELD = "документ"
SENTENCE_NUMBER_FIELD = "номер предложения"
CODE_LINK_FIELD = "ссылка на код (файл строки)"
CODE_FRAGMENT_FIELD = "код (фрагмент)"
STATUS_FIELD = "описание соответствует кода (да/нет)"
REMEDIATION_PLAN_FIELD = "предлагаемый план устранения несоответствий"

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
RISK_HIGH_KEYWORDS = {
    "must",
    "should",
    "shall",
    "required",
    "requirement",
    "обязател",
    "должен",
    "контракт",
    "contract",
    "schema",
    "схем",
    "api",
    "port",
    "adapter",
    "pipeline",
    "adr",
    "version",
    "release",
    "timeout",
    "retry",
    "backoff",
    "circuit",
    "qps",
    "rate limit",
    "idmapping",
    "checksum",
    "hash",
    "medallion",
    "bronze",
    "silver",
    "gold",
    "pandera",
    "validation",
    "naming",
    "policy",
    "governance",
}
RISK_LOW_HINTS = {
    "quick link",
    "quick links",
    "see also",
    "смотри также",
    "см. также",
    "toc",
    "table of contents",
    "оглавление",
    "navigation",
    "навигация",
}
NOISY_PATH_PARTS = {
    "fixtures",
    "vcr",
    "cassette",
    "cassette_library",
    "snapshots",
    "fixtures-data",
}


@dataclass(frozen=True)
class Evidence:
    path: Path
    line_no: int
    line: str
    score: int


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description="Generate a sentence-level documentation audit against repository code."
    )


def iter_doc_files() -> list[Path]:
    files = sorted((ROOT / "docs").rglob("*.md"))
    for extra in (
        ROOT / "README.md",
        ROOT / "docs" / "01-requirements" / "REQUIREMENTS.md",
    ):
        if extra.exists():
            files.append(extra)
    seen: set[Path] = set()
    result: list[Path] = []
    for path in files:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            result.append(resolved)
    return sorted(result, key=lambda path: str(path).lower())


def clean_markdown_line(line: str) -> str:
    s = line.strip()
    s = re.sub(r"^\s{0,3}#{1,6}\s*", "", s)
    s = re.sub(r"^\s*[-*+]\s+", "", s)
    s = re.sub(r"^\s*\d+\.\s+", "", s)
    if "|" in s and re.search(r"\|", s):
        s = " ".join(
            part.strip()
            for part in s.split("|")
            if part.strip() and not set(part.strip()) <= {"-"}
        )
    s = _strip_markdown_links(s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _strip_markdown_links(text: str) -> str:
    parts: list[str] = []
    cursor = 0
    while cursor < len(text):
        start = text.find("[", cursor)
        if start == -1:
            parts.append(text[cursor:])
            break
        label_end = text.find("]", start + 1)
        if label_end == -1 or label_end + 1 >= len(text) or text[label_end + 1] != "(":
            parts.append(text[cursor : start + 1])
            cursor = start + 1
            continue
        target_end = text.find(")", label_end + 2)
        if target_end == -1:
            parts.append(text[cursor:])
            break
        parts.append(text[cursor:start])
        parts.append(text[start + 1 : label_end])
        cursor = target_end + 1
    return "".join(parts)


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
        for part in SENTENCE_SPLIT_RE.split(cleaned):
            sentence = part.strip()
            if len(sentence) < 8:
                continue
            if not re.search(r"[A-Za-zА-Яа-яЁё]", sentence):
                continue
            sentences.append(sentence)
    return sentences


def tokenize(text: str) -> list[str]:
    tokens = [token.lower() for token in TOKEN_RE.findall(text)]
    return [token for token in tokens if len(token) >= 4 and token not in STOPWORDS]


def classify_risk(sentence: str) -> str:
    s_lower = sentence.lower()
    tokens = set(tokenize(sentence))
    if any(hint in s_lower for hint in RISK_LOW_HINTS):
        return "low"
    if any(keyword in s_lower for keyword in RISK_HIGH_KEYWORDS):
        return "high"
    if re.search(r"\badr-\d{2,3}\b", s_lower):
        return "high"
    if re.search(r"\d", sentence):
        return "high"
    if any(token in {"api", "ports", "schemas", "contracts"} for token in tokens):
        return "high"
    return "medium"


def iter_code_files() -> Iterable[Path]:
    for src in SRC_DIRS:
        if src.is_file():
            yield src
            continue
        if not src.exists():
            continue
        for glob in CODE_FILE_GLOBS:
            for path in src.rglob(glob):
                if ".venv" in path.parts or "__pycache__" in path.parts:
                    continue
                yield path


def build_index() -> tuple[dict[str, set[int]], list[tuple[Path, int, str]], Counter]:
    lines: list[tuple[Path, int, str]] = []
    inverted: dict[str, set[int]] = defaultdict(set)
    freq: Counter = Counter()

    for file_path in sorted(iter_code_files(), key=lambda path: str(path).lower()):
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        for i, line in enumerate(text.splitlines(), start=1):
            idx = len(lines)
            lines.append((file_path, i, line))
            tokens = set(tokenize(line))
            for token in tokens:
                inverted[token].add(idx)
                freq[token] += 1
    return inverted, lines, freq


def find_evidence(
    sentence: str,
    inverted: dict[str, set[int]],
    lines: list[tuple[Path, int, str]],
    freq: Counter,
    first_line_idx_by_path: dict[str, int],
) -> Evidence | None:
    """Find evidence in code for a given sentence."""
    backticks = _extract_backticks(sentence)
    probe_tokens = _get_probe_tokens(sentence, freq)
    candidate_ids = _find_candidate_ids(probe_tokens, inverted)
    
    evidence = _check_backticks(backticks, first_line_idx_by_path, lines)
    if evidence is not None:
        return evidence
    
    if not candidate_ids:
        return None
    
    return _find_best_evidence(candidate_ids, lines, probe_tokens)


def _extract_backticks(sentence: str) -> list[str]:
    """Extract backtick-enclosed text from the sentence."""
    return [x.strip() for x in BACKTICK_RE.findall(sentence) if x.strip()]


def _get_probe_tokens(sentence: str, freq: Counter) -> list[str]:
    """Get the top probe tokens from the sentence."""
    sentence_tokens = tokenize(sentence)
    ranked_tokens = sorted(sentence_tokens, key=lambda token: (freq.get(token, 10**9), token))
    return ranked_tokens[:5]


def _find_candidate_ids(
    probe_tokens: list[str], inverted: dict[str, set[int]]
) -> set[int]:
    """Find candidate line indices based on probe tokens."""
    postings = [
        inverted.get(token, set()) for token in probe_tokens if token in inverted
    ]
    postings = sorted(postings, key=len)
    
    if len(postings) >= 2:
        candidate_ids = postings[0] & postings[1]
        if not candidate_ids:
            candidate_ids = postings[0] | postings[1]
    elif postings:
        candidate_ids = postings[0]
    else:
        candidate_ids = set()
    
    return candidate_ids


def _check_backticks(
    backticks: list[str],
    first_line_idx_by_path: dict[str, int],
    lines: list[tuple[Path, int, str]],
) -> Evidence | None:
    """Check backticks for direct code references."""
    for bt in backticks:
        bt_norm = bt.strip().replace("\\", "/")
        if "/" in bt_norm or bt_norm.endswith(
            (".py", ".md", ".yml", ".yaml", ".toml", ".json")
        ):
            abs_path = (ROOT / bt_norm).resolve()
            if abs_path.exists():
                key = str(abs_path).replace("\\", "/").lower()
                if key in first_line_idx_by_path:
                    idx = first_line_idx_by_path[key]
                    path, line_no, line = lines[idx]
                    return Evidence(
                        path=path, line_no=line_no, line=line.strip(), score=10
                    )
    return None


def _find_best_evidence(
    candidate_ids: set[int],
    lines: list[tuple[Path, int, str]],
    probe_tokens: list[str],
) -> Evidence | None:
    """Find the best evidence from candidate line indices."""
    best: Evidence | None = None
    for idx in sorted(candidate_ids)[:400]:
        path, line_no, line = lines[idx]
        weight = _path_weight(path)
        if weight == 0:
            continue
        line_tokens = set(tokenize(line))
        score = sum(1 for token in probe_tokens if token in line_tokens)
        if score <= 0:
            continue
        candidate = Evidence(path=path, line_no=line_no, line=line.strip(), score=score)
        best = _update_best_evidence(best, candidate, weight)
    return best


def _path_weight(path: Path) -> int:
    """Calculate the weight of a path based on its location."""
    parts = {part.lower() for part in path.parts}
    if any(noisy in parts for noisy in NOISY_PATH_PARTS):
        return 0
    if "tests" in parts:
        return 1
    if {"configs", "pyproject.toml", "mkdocs.yml"} & parts:
        return 3
    if "src" in parts:
        return 3
    return 2


def _update_best_evidence(
    best: Evidence | None,
    candidate: Evidence,
    weight: int,
) -> Evidence:
    """Update the best evidence based on score and weight."""
    if best is None:
        return candidate
    
    best_tuple = (best.score, _path_weight(best.path), str(best.path), best.line_no)
    current_tuple = (candidate.score, weight, str(candidate.path), candidate.line_no)
    
    if current_tuple > best_tuple:
        return candidate
    return best


def evaluate_status(sentence: str, evidence: Evidence | None) -> tuple[str, str]:
    if evidence is None:
        return "нет", "нет кандидата"
    numbers = re.findall(r"\d+", sentence)
    if numbers and not any(number in evidence.line for number in numbers):
        return "нет", "числа в предложении не найдены в коде"
    if evidence.score >= 2:
        return "да", "score>=2"
    return "нет", "score<2 (недостаточно совпадений)"


def generated_at_iso() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH", "0")
    try:
        ts = datetime.fromtimestamp(int(epoch), tz=UTC)
    except ValueError:
        ts = datetime.fromtimestamp(0, tz=UTC)
    return ts.isoformat()


def plan_for(status: str) -> str:
    if status == "да":
        return "Утверждение подтверждено; добавить/сохранить явную ссылку на код в документе."
    return (
        "Проверить утверждение вручную: либо скорректировать текст документа под текущий код, "
        "либо реализовать отсутствующее поведение и добавить тест."
    )


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def read_text_robust(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def generate() -> None:
    """Generate documentation audit reports."""
    _prepare_output_directory()
    doc_files = iter_doc_files()
    inverted, lines, freq = build_index()
    first_line_idx_by_path = _build_first_line_index(lines)
    
    rows = _process_documents(doc_files, inverted, lines, freq, first_line_idx_by_path)
    _write_csv_report(rows)
    _write_summary_report(rows, doc_files)
    _write_prompt_reports(rows)


def _prepare_output_directory() -> None:
    """Prepare the output directory for reports."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def _build_first_line_index(
    lines: list[tuple[Path, int, str]]
) -> dict[str, int]:
    """Build an index of the first line for each path."""
    first_line_idx_by_path: dict[str, int] = {}
    for idx, (path, _, _) in enumerate(lines):
        key = str(path).replace("\\", "/").lower()
        if key not in first_line_idx_by_path:
            first_line_idx_by_path[key] = idx
    return first_line_idx_by_path


def _process_documents(
    doc_files: list[Path],
    inverted: dict[str, set[int]],
    lines: list[tuple[Path, int, str]],
    freq: Counter,
    first_line_idx_by_path: dict[str, int],
) -> list[dict[str, str]]:
    """Process documents and collect rows for the report."""
    rows: list[dict[str, str]] = []
    prompt_map: dict[str, list[dict[str, str]]] = defaultdict(list)
    prompt_map_high: dict[str, list[dict[str, str]]] = defaultdict(list)
    
    for doc in doc_files:
        text = read_text_robust(doc)
        sentences = extract_sentences(text)
        for i, sentence in enumerate(sentences, start=1):
            evidence = find_evidence(
                sentence, inverted, lines, freq, first_line_idx_by_path
            )
            status, reason = evaluate_status(sentence, evidence)
            risk = classify_risk(sentence)
            code_link = ""
            code_fragment = ""
            if evidence is not None:
                code_link = f"{rel(evidence.path)}:{evidence.line_no}"
                code_fragment = evidence.line[:280]
            row = {
                DOC_FIELD: rel(doc),
                SENTENCE_NUMBER_FIELD: str(i),
                "предложение": sentence,
                CODE_LINK_FIELD: code_link,
                CODE_FRAGMENT_FIELD: code_fragment,
                STATUS_FIELD: status,
                REMEDIATION_PLAN_FIELD: plan_for(status),
                "причина": reason,
                "risk": risk,
            }
            rows.append(row)
            if status == "нет":
                prompt_map[rel(doc)].append(row)
                if risk == "high":
                    prompt_map_high[rel(doc)].append(row)
    
    rows.sort(key=lambda row: (row[DOC_FIELD], int(row[SENTENCE_NUMBER_FIELD])))
    return rows


def _write_csv_report(rows: list[dict[str, str]]) -> None:
    """Write the CSV report."""
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                DOC_FIELD,
                SENTENCE_NUMBER_FIELD,
                "предложение",
                CODE_LINK_FIELD,
                CODE_FRAGMENT_FIELD,
                STATUS_FIELD,
                REMEDIATION_PLAN_FIELD,
                "причина",
                "risk",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_summary_report(
    rows: list[dict[str, str]], doc_files: list[Path]
) -> None:
    """Write the summary report."""
    total = len(rows)
    ok = sum(1 for row in rows if row[STATUS_FIELD] == "да")
    bad = total - ok
    high_total = sum(1 for row in rows if row["risk"] == "high")
    high_ok = sum(
        1
        for row in rows
        if row["risk"] == "high" and row[STATUS_FIELD] == "да"
    )
    high_bad = high_total - high_ok

    generated_at = generated_at_iso()
    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write("# Исчерпывающий аудит документации (sentence-by-sentence)\n\n")
        f.write(f"- Дата (UTC): {generated_at}\n")
        f.write(f"- Документов: {len(doc_files)}\n")
        f.write(f"- Проверено предложений: {total}\n")
        f.write(f"- Соответствует коду: {ok}\n")
        f.write(f"- Не соответствует / не подтверждено автоматически: {bad}\n")
        f.write(
            f"- High-risk предложений: {high_total} (да: {high_ok}, нет: {high_bad})\n"
        )
        f.write(f"- Полный CSV: `{rel(OUT_CSV)}`\n\n")
        f.write("## Топ-20 документов с максимальным числом несоответствий\n\n")
        bad_by_doc = Counter(
            row[DOC_FIELD]
            for row in rows
            if row[STATUS_FIELD] == "нет"
        )
        f.write("| Документ | Несоответствий |\n")
        f.write("|---|---:|\n")
        for doc_name, cnt in bad_by_doc.most_common(20):
            f.write(f"| `{doc_name}` | {cnt} |\n")


def _write_prompt_reports(rows: list[dict[str, str]]) -> None:
    """Write the prompt reports."""
    prompt_map: dict[str, list[dict[str, str]]] = defaultdict(list)
    prompt_map_high: dict[str, list[dict[str, str]]] = defaultdict(list)
    
    for row in rows:
        if row[STATUS_FIELD] == "нет":
            doc_name = row[DOC_FIELD]
            prompt_map[doc_name].append(row)
            if row["risk"] == "high":
                prompt_map_high[doc_name].append(row)
    
    _write_prompts_report(prompt_map)
    _write_prompts_high_report(prompt_map_high)


def _write_prompts_report(prompt_map: dict[str, list[dict[str, str]]]) -> None:
    """Write the prompts report."""
    with OUT_PROMPTS.open("w", encoding="utf-8") as f:
        f.write("# Набор промптов для модификации документов\n\n")
        f.write("Ниже шаблоны для каждого документа, где найдены несоответствия.\n\n")
        for doc_name in sorted(prompt_map):
            mismatches = sorted(
                prompt_map[doc_name], key=lambda item: int(item[SENTENCE_NUMBER_FIELD])
            )
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
            for mismatch in mismatches[:50]:
                f.write(
                    f"- [{mismatch[SENTENCE_NUMBER_FIELD]}] (risk={mismatch['risk']}) {mismatch['предложение']}\n"
                    f"  - Текущее доказательство: {mismatch[CODE_LINK_FIELD] or 'нет'}\n"
                    f"  - Причина статуса: {mismatch['причина']}\n"
                )
            if len(mismatches) > 50:
                f.write(
                    f"- ... и еще {len(mismatches) - 50} предложений (см. полный CSV-отчет)\n"
                )
            f.write("```\n\n")


def _write_prompts_high_report(prompt_map_high: dict[str, list[dict[str, str]]]) -> None:
    """Write the high-risk prompts report."""
    with OUT_PROMPTS_HIGH.open("w", encoding="utf-8") as f:
        f.write("# High-risk промпты для модификации документов\n\n")
        f.write(
            "Сфокусируйтесь на утверждениях, влияющих на контракты, схемы, API, политики.\n\n"
        )
        for doc_name in sorted(prompt_map_high):
            mismatches = sorted(
                prompt_map_high[doc_name], key=lambda item: int(item[SENTENCE_NUMBER_FIELD])
            )
            f.write(f"## {doc_name}\n\n")
            f.write("```text\n")
            f.write(
                "Обнови документ, начиная с high-risk утверждений.\n"
                f"Файл: {doc_name}\n\n"
                "Требования:\n"
                "1) Для каждого пункта: либо исправь текст, либо создай задачу на реализацию, либо привяжи точную ссылку на код.\n"
                "2) Не нарушай публичные контракты без migration note.\n"
                "3) Подтверди схемы/контракты по коду и тестам.\n\n"
                "Проблемные предложения (high-risk):\n"
            )
            for mismatch in mismatches[:50]:
                f.write(
                    f"- [{mismatch[SENTENCE_NUMBER_FIELD]}] {mismatch['предложение']}\n"
                    f"  - Текущее доказательство: {mismatch[CODE_LINK_FIELD] or 'нет'}\n"
                    f"  - Причина статуса: {mismatch['причина']}\n"
                )
            if len(mismatches) > 50:
                f.write(
                    f"- ... и еще {len(mismatches) - 50} предложений (см. полный CSV-отчет)\n"
                )
            f.write("```\n\n")


def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)
    generate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
