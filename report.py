"""
Report Generator
================
Takes a list of EncounterData objects and writes a formatted text report
showing per-encounter, per-player consumable usage.

Output file format (example):

  ════════════════════════════════════════════════════════
  ENCOUNTER: Gruul the Dragonkiller  [25 Player]  ★ KILL
  Start: 04/01 21:03:44.000  |  End: 04/01 21:08:12.000
  ════════════════════════════════════════════════════════

  Arthas
    Flask         : Flask of Relentless Assault
    Elixir (Battle) : Elixir of Major Agility
    Food          : Warp Burger
    Potion        : Super Mana Potion

  Uther
    Flask         : Flask of Mighty Restoration
    Food          : Golden Fish Sticks
    Scroll        : Scroll of Spirit VIII
  ...
"""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

from parser import EncounterData

# Category display order in the report
CATEGORY_ORDER = [
    "Flask",
    "Elixir (Battle)",
    "Elixir (Guardian)",
    "Potion",
    "Food",
    "Scroll",
    "Weapon Buff",
    "Engineering",
    "Other",
]

SEPARATOR_WIDE  = "═" * 60
SEPARATOR_THIN  = "─" * 60


def _result_label(enc: EncounterData) -> str:
    return "★ KILL" if enc.success else "✗ WIPE"


def _write_encounter_block(enc: EncounterData, out: TextIO) -> None:
    result = _result_label(enc)
    out.write(f"\n{SEPARATOR_WIDE}\n")
    out.write(f"ENCOUNTER : {enc.encounter_name}  [{enc.difficulty}]  {result}\n")
    out.write(f"Start     : {enc.start_time}  |  End: {enc.end_time}\n")
    out.write(f"{SEPARATOR_WIDE}\n\n")

    summary = enc.get_summary()
    if not summary:
        out.write("  (No consumable events detected for this encounter)\n")
        return

    for player in sorted(summary.keys(), key=str.lower):
        player_cats = summary[player]
        out.write(f"  {player}\n")
        for cat in CATEGORY_ORDER:
            if cat in player_cats:
                items = ", ".join(player_cats[cat])
                label = f"{cat:<22}"
                out.write(f"    {label}: {items}\n")
        # Any unlisted categories
        for cat, items in player_cats.items():
            if cat not in CATEGORY_ORDER:
                label = f"{cat:<22}"
                out.write(f"    {label}: {', '.join(items)}\n")
        out.write("\n")


def _write_summary_table(encounters: list[EncounterData], out: TextIO) -> None:
    """Quick index of all encounters at the top of the report."""
    out.write("ENCOUNTER SUMMARY\n")
    out.write(SEPARATOR_THIN + "\n")
    for i, enc in enumerate(encounters, 1):
        result = _result_label(enc)
        player_count = len(enc.consumable_events)
        out.write(
            f"  {i:>2}. {enc.encounter_name:<35} [{enc.difficulty:<14}] "
            f"{result}  ({player_count} players with consumable data)\n"
        )
    out.write("\n")


def generate_report(
    encounters: list[EncounterData],
    output_path: str | Path,
    log_filename: str = "",
) -> None:
    """
    Write the consumable report to `output_path`.

    Args:
        encounters   : list of parsed EncounterData objects
        output_path  : where to write the .txt report
        log_filename : original combat log filename (for the header)
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as out:
        # ── Header ──────────────────────────────────────────────────
        out.write("TBC ANNIVERSARY — CONSUMABLE USAGE REPORT\n")
        out.write(SEPARATOR_WIDE + "\n")
        if log_filename:
            out.write(f"Source log : {log_filename}\n")
        out.write(f"Encounters : {len(encounters)}\n")
        kills = sum(1 for e in encounters if e.success)
        out.write(f"Kills      : {kills}  |  Wipes: {len(encounters) - kills}\n")
        out.write(SEPARATOR_WIDE + "\n\n")

        # ── Summary table ────────────────────────────────────────────
        if encounters:
            _write_summary_table(encounters, out)
        else:
            out.write("No ENCOUNTER_START / ENCOUNTER_END blocks found in the log.\n")
            out.write(
                "Make sure your WoW client has Advanced Combat Logging enabled "
                "(System → Network → Advanced Combat Logging).\n"
            )
            return

        # ── Per-encounter detail ─────────────────────────────────────
        for enc in encounters:
            _write_encounter_block(enc, out)

        out.write(f"\n{SEPARATOR_WIDE}\n")
        out.write("END OF REPORT\n")

    print(f"[OK] Report written to: {output_path}")
