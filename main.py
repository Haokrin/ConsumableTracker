"""
TBC Anniversary Consumable Tracker — Main Entry Point

Usage:
    python main.py <path/to/WoWCombatLog.txt> [options]

Options:
    -o, --output   Output base path (default: consumable_report)
                   Generates <base>.txt and <base>.html
    -v, --verbose  Print debug info while parsing
    --wipes        Include wipe encounters (default: kills only)

Example:
    python main.py WoWCombatLog.txt -o reports/raid_night --wipes
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from parser import CombatLogParser
from report import generate_report
from report_html import generate_html_report


def main() -> None:
    arg_parser = argparse.ArgumentParser(
        description="TBC Anniversary — Combat Log Consumable Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    arg_parser.add_argument("log_file", help="Path to WoWCombatLog.txt")
    arg_parser.add_argument(
        "-o", "--output", default="consumable_report",
        help="Output base path without extension (default: consumable_report)",
    )
    arg_parser.add_argument("-v", "--verbose", action="store_true")
    arg_parser.add_argument(
        "--wipes", action="store_true",
        help="Include wipe attempts (default: kills only)",
    )

    args = arg_parser.parse_args()
    log_path = Path(args.log_file)

    if not log_path.exists():
        print(f"[ERROR] Log file not found: {log_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Parsing: {log_path}")
    parser = CombatLogParser(log_path, verbose=args.verbose)
    all_encounters = parser.parse()
    print(f"[INFO] Found {len(all_encounters)} encounter(s).")

    encounters = all_encounters if args.wipes else [e for e in all_encounters if e.success]
    wipe_count = len(all_encounters) - len(encounters)
    if wipe_count and not args.wipes:
        print(f"[INFO] Excluding {wipe_count} wipe(s). Use --wipes to include them.")

    base = Path(args.output)
    generate_report(encounters, base.with_suffix(".txt"), log_path.name)
    generate_html_report(encounters, base.with_suffix(".html"), log_path.name)


if __name__ == "__main__":
    main()
