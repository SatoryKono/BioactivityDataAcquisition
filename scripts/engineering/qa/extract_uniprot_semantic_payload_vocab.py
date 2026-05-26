"""Extract observed UniProt semantic payload vocabularies from Bronze fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _iter_jsonl_payloads(paths: list[Path]) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payloads.append(json.loads(line))
    return payloads


def extract_uniprot_semantic_payload_vocab(paths: list[Path]) -> dict[str, list[str]]:
    observed = {
        "feature_types": set(),
        "comment_types": set(),
        "keyword_categories": set(),
    }
    for payload in _iter_jsonl_payloads(paths):
        for feature in payload.get("features", []):
            if isinstance(feature, dict):
                feature_type = feature.get("type")
                if feature_type is not None:
                    observed["feature_types"].add(str(feature_type))
        for comment in payload.get("comments", []):
            if isinstance(comment, dict):
                comment_type = comment.get("commentType")
                if comment_type is not None:
                    observed["comment_types"].add(str(comment_type))
        for keyword in payload.get("keywords", []):
            if isinstance(keyword, dict):
                keyword_category = keyword.get("category")
                if keyword_category is not None:
                    observed["keyword_categories"].add(str(keyword_category))
    return {key: sorted(values) for key, values in observed.items() if values}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    payload = extract_uniprot_semantic_payload_vocab(list(args.paths))
    rendered = json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2)
    if args.json_out is None:
        print(rendered)
    else:
        args.json_out.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
