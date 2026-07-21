#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Продвинутый Grok CLI для BioETL проекта.
Обеспечивает расширенную функциональность для работы с Grok паттернами.
"""

import sys
import json
import argparse
from pygrok import Grok

# Устанавливаем UTF-8 кодировку для вывода на Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


# Predefined patterns for BioETL logs
BIETL_PATTERNS = {
    'bioetl_log': '%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} %{DATA:logger} - %{GREEDYDATA:message}',
    'pipeline_start': '%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} %{DATA:logger} - Pipeline %{DATA:pipeline_code} started with run_id %{DATA:run_id}',
    'pipeline_complete': '%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} %{DATA:logger} - Pipeline %{DATA:pipeline_code} completed in %{NUMBER:duration_ms}ms',
    'http_request': '%{IP:client} %{WORD:method} %{DATA:request} %{NUMBER:status} %{NUMBER:bytes}',
    'error': '%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} %{DATA:logger} - ERROR: %{GREEDYDATA:error_message}',
}


def parse_with_pattern(pattern, text, custom_patterns=None):
    """Parse text using Grok pattern."""
    try:
        if custom_patterns:
            grok = Grok(pattern, custom_patterns=custom_patterns)
        else:
            grok = Grok(pattern)
        result = grok.match(text)
        return result
    except Exception as e:
        return {'error': str(e)}


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description='Grok CLI for BioETL project')
    parser.add_argument('pattern', nargs='?', help='Grok pattern or predefined pattern name')
    parser.add_argument('text', nargs='?', help='Text to parse')
    parser.add_argument('--list-patterns', action='store_true', help='Show predefined patterns')
    parser.add_argument('--custom-patterns', help='Path to custom patterns JSON file')
    parser.add_argument('--output', choices=['json', 'pretty'], default='pretty', help='Output format')
    
    args = parser.parse_args()
    
    if args.list_patterns:
        print("Predefined patterns:")
        for name, pattern in BIETL_PATTERNS.items():
            print(f"  {name}: {pattern}")
        sys.exit(0)
    
    if not args.pattern or not args.text:
        parser.print_help()
        sys.exit(1)
    
    # Determine pattern
    if args.pattern in BIETL_PATTERNS:
        pattern = BIETL_PATTERNS[args.pattern]
    else:
        pattern = args.pattern
    
    # Load custom patterns if specified
    custom_patterns = None
    if args.custom_patterns:
        try:
            with open(args.custom_patterns, 'r', encoding='utf-8') as f:
                custom_patterns = json.load(f)
        except Exception as e:
            print(f"Error loading custom patterns: {e}")
            sys.exit(1)
    
    # Parse text
    result = parse_with_pattern(pattern, args.text, custom_patterns)
    
    # Output result
    if args.output == 'json':
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    if 'error' in result:
        sys.exit(1)


if __name__ == "__main__":
    main()