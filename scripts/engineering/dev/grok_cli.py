#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Grok CLI для BioETL проекта.
Обеспечивает CLI интерфейс для работы с Grok паттернами через pygrok.
"""

import sys
import json
from pygrok import Grok

# Устанавливаем UTF-8 кодировку для вывода на Windows
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")


def main():
    """Main CLI function."""
    if len(sys.argv) < 3:
        print("Usage: python scripts/grok_cli.py <pattern> <text>")
        print(
            "Example: python scripts/grok_cli.py '%{IP:client} %{WORD:method}' '192.168.1.1 GET /api'"
        )
        sys.exit(1)

    pattern = sys.argv[1]
    text = sys.argv[2]

    try:
        grok = Grok(pattern)
        result = grok.match(text)

        if result:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("No match")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
