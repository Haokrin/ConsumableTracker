"""
TBC Anniversary Combat Log Parser
===================================
Reads a raw WoWCombatLog.txt and extracts per-encounter consumable usage.

Real TBC Anniversary log format:
  M/D/YYYY HH:MM:SS.ffff  EVENT_TYPE,args...

COMBATANT_INFO ordering:
  COMBATANT_INFO events come AFTER ENCOUNTER_START (lines 19285 vs 19286+).
  The parser therefore does a two-pass read:
    Pass 1 — collect all COMBATANT_INFO GUIDs per encounter
    Pass 2 — process consumable events using the correct roster per encounter

Pre-pull tracking:
  _active_auras tracks every consumable buff seen anywhere in the log.
  At ENCOUNTER_START the current state is snapshotted so pre-pull flasks/
  food/elixirs applied before the pull are included in the report.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from consumables_db import CONSUMABLE_BY_SPELL_ID, DETECT_ON_AURA, DETECT_ON_CAST


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ConsumableEvent:
    timestamp: str
    player_name: str
    spell_id: int
    consumable_name: str
    category: str
    event_type: str   # AURA_APPLIED | AURA_REFRESH | AURA_PREPULL | CAST


@dataclass
class EncounterData:
    encounter_id: int
    encounter_name: str
    difficulty: str
    start_time: str
    end_time: str = ""
    success: bool = False
    consumable_events: dict[str, list[ConsumableEvent]] = field(default_factory=dict)
    # Full raid roster - every member present even with no consumables
    roster: list[str] = field(default_factory=list)
    # (elapsed_secs, player_name, spell_id, mana_pct_or_none)
    # mana_pct_or_none = float 0-1 if valid mana reading, else None
    timed_events: list[tuple] = field(default_factory=list)
    # (elapsed_secs, player_name) for each "Not enough mana" cast failure
    oom_events: list[tuple[float, str]] = field(default_factory=list)


    def add_event(self, evt: ConsumableEvent) -> None:
        self.consumable_events.setdefault(evt.player_name, []).append(evt)

    def get_summary(self) -> dict[str, dict[str, list[str]]]:
        """
        Returns {player_name: {category: [consumable_name, ...]}} de-duped.
        Every roster member is included even if they used no consumables.
        """
        summary: dict[str, dict[str, set[str]]] = {}
        for player in self.roster:
            summary.setdefault(player, {})
        for player, events in self.consumable_events.items():
            summary.setdefault(player, {})
            for evt in events:
                summary[player].setdefault(evt.category, set()).add(evt.consumable_name)
        return {
            player: {cat: sorted(names) for cat, names in cats.items()}
            for player, cats in sorted(summary.items(), key=lambda x: x[0].lower())
        }


# ---------------------------------------------------------------------------
# GUID and name helpers
# ---------------------------------------------------------------------------

PLAYER_GUID_RE = re.compile(r"^Player-", re.IGNORECASE)

def is_player_guid(guid: str) -> bool:
    return bool(PLAYER_GUID_RE.match(guid))


def clean_player_name(raw: str) -> str:
    """Strip realm suffix: 'Grumpyelf-Thunderstrike-EU' → 'Grumpyelf'."""
    name = raw.strip('"').strip("'").strip()
    dash = name.find('-')
    if dash > 0:
        name = name[:dash]
    return name


# ---------------------------------------------------------------------------
# Log line splitting
# ---------------------------------------------------------------------------

TIMESTAMP_RE = re.compile(r"^(\d{1,2}/\d{1,2}/\d{4} \d{2}:\d{2}:\d{2}\.\d+)\s{2}")


def _split_log_line(line: str) -> Optional[tuple[str, list[str]]]:
    m = TIMESTAMP_RE.match(line)
    if not m:
        # Fallback: old sample format MM/DD HH:MM:SS.mmm
        old = re.match(r"^(\d{1,2}/\d{1,2} \d{2}:\d{2}:\d{2}\.\d{3})\s+", line)
        if not old:
            return None
        m = old
    timestamp = m.group(1)
    rest = line[m.end():]
    try:
        fields = next(csv.reader(io.StringIO(rest)))
    except Exception:
        return None
    return timestamp, [f.strip() for f in fields]


DIFFICULTY_MAP = {
    "1": "Normal",    "2": "Heroic",
    "3": "10 Player", "4": "25 Player",
    "5": "10 Player (Heroic)", "6": "25 Player (Heroic)",
}


# ---------------------------------------------------------------------------
# Pass 1 — collect COMBATANT_INFO roster per encounter
# ---------------------------------------------------------------------------

def _collect_rosters(log_path: Path) -> dict[int, set[str]]:
    """
    Single-pass scan that returns {encounter_start_line: set_of_player_guids}.

    COMBATANT_INFO events immediately follow ENCOUNTER_START in the log.
    We key rosters by the line number of ENCOUNTER_START so Pass 2 can look
    up the exact roster for each encounter by its start line.
    """
    rosters: dict[int, set[str]] = {}
    current_start_line: Optional[int] = None
    current_guids: set[str] = set()

    with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip("\n\r")
            parsed = _split_log_line(line)
            if not parsed:
                continue
            _, fields = parsed
            if not fields:
                continue
            event = fields[0]

            if event == "ENCOUNTER_START":
                # Save previous encounter's roster if any
                if current_start_line is not None:
                    rosters[current_start_line] = current_guids
                current_start_line = lineno
                current_guids = set()

            elif event == "COMBATANT_INFO":
                if current_start_line is not None and len(fields) >= 2:
                    guid = fields[1].strip()
                    if is_player_guid(guid):
                        current_guids.add(guid)

            elif event == "ENCOUNTER_END":
                if current_start_line is not None:
                    rosters[current_start_line] = current_guids
                current_start_line = None
                current_guids = set()

    # Handle log that ends mid-encounter
    if current_start_line is not None:
        rosters[current_start_line] = current_guids

    return rosters


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class CombatLogParser:
    """
    Two-pass parser for WoWCombatLog.txt.

    Pass 1 (_collect_rosters): reads the entire file to build a map of
      encounter_start_line → set of raid member GUIDs from COMBATANT_INFO.

    Pass 2 (parse): processes the log normally. At each ENCOUNTER_START the
      correct raid roster is looked up and used to filter all subsequent
      consumable events for that encounter.

    Usage:
        parser = CombatLogParser("WoWCombatLog.txt")
        encounters = parser.parse()
    """

    def __init__(self, log_path: str | Path, verbose: bool = False):
        self.log_path = Path(log_path)
        self.verbose = verbose

    def parse(self) -> list[EncounterData]:
        # Pass 1: build roster map
        rosters = _collect_rosters(self.log_path)
        if self.verbose:
            print(f"[INFO] Pass 1 complete — {len(rosters)} encounter roster(s) found")
            for line, guids in sorted(rosters.items()):
                print(f"  Encounter starting at line {line}: {len(guids)} raid members")

        # Pass 2: process events
        encounters: list[EncounterData] = []
        current_encounter: Optional[EncounterData] = None
        current_roster: set[str] = set()
        # (player_guid, spell_id) → ConsumableEvent — tracks active buffs globally
        active_auras: dict[tuple[str, int], ConsumableEvent] = {}
        # GUID → clean name cache
        guid_to_name: dict[str, str] = {}

        def is_raid_member(guid: str) -> bool:
            # If no roster available (e.g. sample log without COMBATANT_INFO),
            # fall back to accepting all player GUIDs
            if not current_roster:
                return is_player_guid(guid)
            return guid in current_roster

        # player_name -> set of spell IDs they cast or received (for class inference)
        player_spells: dict[str, set[int]] = {}
        _enc_start_dt = None  # datetime of current encounter start

        with open(self.log_path, "r", encoding="utf-8", errors="replace") as fh:
            for lineno, raw_line in enumerate(fh, 1):
                line = raw_line.rstrip("\n\r")
                if not line:
                    continue
                parsed = _split_log_line(line)
                if not parsed:
                    continue
                timestamp, fields = parsed
                if not fields:
                    continue
                event_type = fields[0]

                # Always harvest name→GUID from every event
                for guid_i, name_i in ((1, 2), (5, 6)):
                    if len(fields) > name_i:
                        g, n = fields[guid_i], fields[name_i]
                        if is_player_guid(g) and n and n != "1":
                            guid_to_name[g] = clean_player_name(n)

                # Collect spell IDs CAST by each player (for class inference).
                # We only use spells the player actively cast — NOT auras received —
                # to avoid misclassifying a player who receives e.g. Windfury from
                # an Enhancement Shaman's totem as an Enhancement Shaman themselves.
                if event_type in ("SPELL_CAST_SUCCESS", "SPELL_CAST_START") and len(fields) > 9:
                    try:
                        sid = int(fields[9])
                    except ValueError:
                        sid = None
                    if sid:
                        src_g = fields[1] if len(fields) > 1 else ""
                        if is_player_guid(src_g):
                            src_name = guid_to_name.get(src_g) or clean_player_name(fields[2])
                            player_spells.setdefault(src_name, set()).add(sid)
                # Also include self-applied auras (src == dst) as evidence of class
                elif event_type == "SPELL_AURA_APPLIED" and len(fields) > 9:
                    try:
                        sid = int(fields[9])
                    except ValueError:
                        sid = None
                    if sid and len(fields) > 5:
                        src_g = fields[1]
                        dst_g = fields[5]
                        # Only count if player applied the aura to themselves
                        if src_g == dst_g and is_player_guid(src_g):
                            src_name = guid_to_name.get(src_g) or clean_player_name(fields[2])
                            player_spells.setdefault(src_name, set()).add(sid)

                # ── Encounter boundaries ──────────────────────────────

                if event_type == "ENCOUNTER_START":
                    enc_id = int(fields[1]) if len(fields) > 1 and fields[1].isdigit() else 0
                    enc_name = fields[2] if len(fields) > 2 else "Unknown"
                    diff = DIFFICULTY_MAP.get(fields[3], f"Difficulty {fields[3]}") if len(fields) > 3 else ""
                    current_roster = rosters.get(lineno, set())
                    # Build roster name list from GUIDs
                    roster_names = sorted(
                        set(guid_to_name[g] for g in current_roster if g in guid_to_name),
                        key=str.lower
                    )
                    current_encounter = EncounterData(
                        encounter_id=enc_id,
                        encounter_name=enc_name,
                        difficulty=diff,
                        start_time=timestamp,
                        roster=roster_names,
                    )
                    try:
                        from datetime import datetime as _dt
                        _enc_start_dt = _dt.strptime(timestamp, "%m/%d/%Y %H:%M:%S.%f")
                    except Exception:
                        _enc_start_dt = None
                    # Snapshot pre-pull auras for raid members only
                    snapshotted = 0
                    for (guid, spell_id), evt in active_auras.items():
                        if is_raid_member(guid):
                            current_encounter.add_event(ConsumableEvent(
                                timestamp=evt.timestamp,
                                player_name=evt.player_name,
                                spell_id=evt.spell_id,
                                consumable_name=evt.consumable_name,
                                category=evt.category,
                                event_type="AURA_PREPULL",
                            ))
                            snapshotted += 1
                    if self.verbose:
                        print(f"[ENCOUNTER START] {enc_name} ({diff}) @ {timestamp}  "
                              f"roster={len(current_roster)} prepull={snapshotted}")

                elif event_type == "ENCOUNTER_END":
                    if current_encounter is not None:
                        if len(fields) >= 6:
                            current_encounter.success = fields[5] == "1"
                        current_encounter.end_time = timestamp
                        encounters.append(current_encounter)
                        if self.verbose:
                            result = "KILL" if current_encounter.success else "WIPE"
                            print(f"[ENCOUNTER END] {current_encounter.encounter_name} — {result} @ {timestamp}")
                    current_encounter = None
                    current_roster = set()

                # ── Aura tracking (all players, not just raid) ────────
                # We track everyone so the pre-pull snapshot is accurate even
                # before COMBATANT_INFO has been read. Roster filtering happens
                # at snapshot time and at the point of recording into encounters.

                elif event_type in ("SPELL_AURA_APPLIED", "SPELL_AURA_REFRESH"):
                    if len(fields) < 11:
                        continue
                    dst_guid = fields[5]
                    if not is_player_guid(dst_guid):
                        continue
                    try:
                        spell_id = int(fields[9])
                    except ValueError:
                        continue
                    if spell_id not in DETECT_ON_AURA:
                        continue
                    aura_type = fields[12] if len(fields) > 12 else ""
                    if aura_type and aura_type != "BUFF":
                        continue
                    dst_name = guid_to_name.get(dst_guid) or clean_player_name(fields[6])
                    consumable = CONSUMABLE_BY_SPELL_ID[spell_id]
                    evt = ConsumableEvent(
                        timestamp=timestamp,
                        player_name=dst_name,
                        spell_id=spell_id,
                        consumable_name=consumable["name"],
                        category=consumable["category"],
                        event_type="AURA_REFRESH" if "REFRESH" in event_type else "AURA_APPLIED",
                    )
                    active_auras[(dst_guid, spell_id)] = evt
                    if current_encounter is not None and is_raid_member(dst_guid):
                        current_encounter.add_event(evt)

                elif event_type == "SPELL_CAST_FAILED":
                    # Detect genuine OOM — only the exact "Not enough mana" reason string.
                    # "Not yet recovered" = spell on cooldown, completely different.
                    # We also deduplicate: if the same player fired an OOM event within
                    # the last 30s, skip it — one OOM period = one event, not dozens.
                    _OOM_REASONS = {"not enough mana", "no mana"}
                    if (len(fields) > 12 and current_encounter is not None
                            and fields[12].lower() in _OOM_REASONS
                            and _enc_start_dt is not None):
                        src_guid = fields[1] if len(fields) > 1 else ''
                        in_roster = (not current_roster) or (src_guid in current_roster)
                        if is_player_guid(src_guid) and in_roster:
                            src_name = guid_to_name.get(src_guid) or clean_player_name(fields[2])
                            try:
                                from datetime import datetime as _dtoom
                                el = (_dtoom.strptime(timestamp, "%m/%d/%Y %H:%M:%S.%f") - _enc_start_dt).total_seconds()
                                # Deduplicate: skip if same player had OOM within last 30s
                                recent = [t for t, n in current_encounter.oom_events
                                          if n == src_name and el - t < 30.0]
                                if not recent:
                                    current_encounter.oom_events.append((el, src_name))
                            except Exception:
                                pass

                elif event_type == "SPELL_ENERGIZE":
                    # Record mana restoration details for efficiency scoring
                    if len(fields) >= 34 and current_encounter is not None:
                        try:
                            sid = int(fields[9])
                        except ValueError:
                            sid = None
                        if sid and sid in DETECT_ON_CAST:
                            try:
                                restored  = float(fields[30])
                                overflow  = float(fields[31])
                                max_mana  = int(fields[33])
                                dst_guid  = fields[5]
                                if is_player_guid(dst_guid) and max_mana > 0:
                                    dst_name = guid_to_name.get(dst_guid) or clean_player_name(fields[6])
                                    deficit_frac = (restored - overflow) / max_mana
                                    # Store as a special timed event with extra data
                                    # Use negative spell_id as sentinel so score_encounter
                                    # can distinguish energize events from cast events
                                    if _enc_start_dt is not None:
                                        from datetime import datetime as _dte
                                        el = (_dte.strptime(timestamp, "%m/%d/%Y %H:%M:%S.%f") - _enc_start_dt).total_seconds()
                                        # Encode as (elapsed, name, -sid, deficit_frac, overflow_frac)
                                        overflow_frac = overflow / max_mana if max_mana > 0 else 0.0
                                        current_encounter.timed_events.append(
                                            (el, dst_name, -sid, deficit_frac, overflow_frac)
                                        )
                            except (ValueError, IndexError):
                                pass

                elif event_type == "SPELL_AURA_REMOVED":
                    if len(fields) < 10:
                        continue
                    dst_guid = fields[5]
                    if not is_player_guid(dst_guid):
                        continue
                    try:
                        spell_id = int(fields[9])
                    except ValueError:
                        continue
                    if spell_id in DETECT_ON_AURA:
                        active_auras.pop((dst_guid, spell_id), None)

                elif event_type == "SPELL_CAST_SUCCESS":
                    if len(fields) < 10:
                        continue
                    src_guid = fields[1]
                    if not is_player_guid(src_guid) or not is_raid_member(src_guid):
                        continue
                    try:
                        spell_id = int(fields[9])
                    except ValueError:
                        continue
                    spell_name = fields[10] if len(fields) > 10 else ""

                    if current_encounter is not None and _enc_start_dt is not None:
                        try:
                            from datetime import datetime as _dtcs
                            el = (_dtcs.strptime(timestamp, "%m/%d/%Y %H:%M:%S.%f") - _enc_start_dt).total_seconds()
                            src_name_cs = guid_to_name.get(src_guid) or clean_player_name(fields[2])
                            # Record Bloodlust/Heroism timing
                            _BL_IDS = {2825, 32182}
                            if spell_id in _BL_IDS:
                                current_encounter.timed_events.append((el, src_name_cs, spell_id, None))
                        except Exception:
                            pass

                    if spell_id not in DETECT_ON_CAST:
                        continue
                    src_name = guid_to_name.get(src_guid) or clean_player_name(fields[2])
                    consumable = CONSUMABLE_BY_SPELL_ID[spell_id]
                    evt = ConsumableEvent(
                        timestamp=timestamp,
                        player_name=src_name,
                        spell_id=spell_id,
                        consumable_name=consumable["name"],
                        category=consumable["category"],
                        event_type="CAST",
                    )
                    if current_encounter is not None:
                        current_encounter.add_event(evt)
                        # Record potion timestamp + mana % for efficiency scoring
                        if _enc_start_dt is not None:
                            try:
                                from datetime import datetime as _dtp
                                el = (_dtp.strptime(timestamp, "%m/%d/%Y %H:%M:%S.%f") - _enc_start_dt).total_seconds()
                                current_encounter.timed_events.append((el, src_name, spell_id, None))
                            except Exception:
                                pass

        # Attach the global player_spells dict to each encounter for scoring
        for enc in encounters:
            enc.player_spells = player_spells
        return encounters
