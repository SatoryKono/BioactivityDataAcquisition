from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

DOC_ROOTS: list[str] = [
    "README.md",
    "docs/00-project",
    "docs/01-requirements",
    "docs/02-architecture",
    "docs/03-guides",
    "docs/03-data-model",
    "docs/04-reference",
    "docs/adr",
]
CODE_ROOTS: list[str] = ["src"]
OUT: Path = Path("reports/documentation_sentence_audit.csv")
SUMMARY: Path = Path("reports/documentation_sentence_audit_summary.md")

STOP_WORDS: set[str] = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "are",
    "was",
    "were",
    "have",
    "has",
    "had",
    "not",
    "but",
    "или",
    "для",
    "как",
    "что",
    "это",
    "при",
    "все",
    "under",
    "into",
    "also",
    "can",
    "must",
    "should",
    "may",
    "using",
    "used",
    "use",
    "data",
    "layer",
    "layers",
    "project",
    "bioetl",
}


def extract_words(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[A-Za-zА-Яа-я0-9_]{3,}", text)]


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out: list[str] = []
    for ln in lines:
        if ln.startswith("#") or ln.startswith("|"):
            continue
        parts = re.split(r"(?<=[.!?])\s+", ln)
        for part in parts:
            sentence = part.strip(" -\t")
            if len(sentence) >= 15:
                out.append(sentence)
    return out


def main() -> None:
    entries: list[tuple[str, int, str]] = []
    for root in CODE_ROOTS:
        for file in Path(root).rglob("*.py"):
            txt = file.read_text(encoding="utf-8", errors="ignore").splitlines()
            for i, line in enumerate(txt, 1):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                entries.append((str(file).replace("\\", "/"), i, stripped))

    total_entries: int = len(entries)
    inverted: dict[str, list[int]] = defaultdict(list)
    doc_freq: Counter[str] = Counter()
    entry_tokens: list[Counter[str]] = []

    for idx, (_, _, line) in enumerate(entries):
        tokens = [w for w in extract_words(line) if w not in STOP_WORDS]
        token_counter: Counter[str] = Counter(tokens)
        entry_tokens.append(token_counter)
        for token in token_counter:
            inverted[token].append(idx)
            doc_freq[token] += 1

    idf: dict[str, float] = {
        token: math.log((total_entries + 1) / (count + 1)) + 1
        for token, count in doc_freq.items()
    }

    rows: list[list[object]] = []
    stats: Counter[str] = Counter()

    for root in DOC_ROOTS:
        base = Path(root)
        files = [base] if base.is_file() else sorted(base.rglob("*.md"))
        for file in files:
            rel = str(file).replace("\\", "/")
            text = file.read_text(encoding="utf-8", errors="ignore")
            sentences = split_sentences(text)
            for num, sentence in enumerate(sentences, 1):
                tokens = [w for w in extract_words(sentence) if w not in STOP_WORDS]
                query: Counter[str] = Counter(tokens)
                candidates: Counter[int] = Counter()

                for token, value in query.items():
                    for idx in inverted.get(token, []):
                        candidates[idx] += int(value * idf.get(token, 1.0) * 100)

                code_ref = ""
                fragment = ""
                overlap = 0

                if candidates:
                    best_idx, _ = candidates.most_common(1)[0]
                    file_path, line_no, frag = entries[best_idx]
                    code_ref = f"{file_path}:{line_no}"
                    fragment = frag[:220]
                    overlap = len(set(query) & set(entry_tokens[best_idx]))

                ok = "да" if overlap >= 2 else "нет"
                stats[ok] += 1
                if ok == "нет":
                    rows.append(
                        [
                            rel,
                            num,
                            sentence,
                            code_ref,
                            fragment,
                            ok,
                            "Уточнить формулировку и/или добавить ссылку на реализацию в коде.",
                        ]
                    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "документ",
                "номер предложения",
                "предложение",
                "ссылка на код (файл:строка)",
                "код (фрагмент)",
                "описание соответствует кода (да/нет)",
                "предлагаемый план устранения несоответствий",
            ]
        )
        writer.writerows(rows)

    unique_docs = {row[0] for row in rows}
    with SUMMARY.open("w", encoding="utf-8") as fh:
        fh.write("# Отчет по автоматизированному аудиту предложений документации\n\n")
        fh.write(f"- Проверено документов: {len(unique_docs)}\n")
        fh.write(f"- Проверено предложений: {stats['да'] + stats['нет']}\n")
        fh.write(f"- Соответствует коду (да): {stats['да']}\n")
        fh.write(f"- Потенциальные несоответствия (нет): {stats['нет']}\n")
        fh.write(f"- В таблицу выгружены строки со статусом 'нет': {len(rows)}\n")
        fh.write(
            "\n> Метод: автоматический поиск наиболее релевантной строки кода по пересечению токенов; "
            "все записи со статусом 'нет' требуют ручной валидации архитектором.\n"
        )


if __name__ == "__main__":
    main()
