"""
Consumable Scoring System
==========================
See module docstring in original for full design notes.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Class spell database — spells uniquely cast by one class
# Used to vote for a player's class from their cast history
# ---------------------------------------------------------------------------

_CLASS_SPELLS: dict[int, str] = {}

_RAW_CLASS_SPELLS: dict[str, set[int]] = {
    "Warrior": {
        29707, 25248, 12294,    # Mortal Strike (Arms)
        30330, 30022,            # Devastate (Prot)
        25231, 23922, 30356,    # Shield Slam (Prot)
        25264, 11574, 6343,     # Thunderclap
        2458, 71, 2457,         # Berserker / Defensive / Battle Stance
        12678, 20662, 25234,    # Execute
        34428,                   # Victory Rush
        30335, 23881,            # Bloodthirst (Fury)
        1680, 25251,             # Whirlwind (Fury)
        12292,                   # Death Wish (Fury)
        12328,                   # Sweeping Strikes (Arms)
        18499,                   # Berserker Rage
        2048, 6673,              # Battle Shout
        2687,                    # Bloodrage
        6554, 72,                # Pummel / Shield Bash
        355,                     # Taunt
        871,                     # Shield Wall
        12975,                   # Last Stand
        2565,                    # Shield Block
        25203,                   # Demoralizing Shout
        469,                     # Commanding Shout
    },
    "Paladin": {
        20473, 27174, 25903, 33072,  # Holy Shock
        25263, 10329, 27136,    # Holy Light
        27137,                   # Flash of Light
        25291, 19740,            # Greater Blessing of Might
        25290, 19742,            # Greater Blessing of Wisdom
        25292,                   # Greater Blessing of Kings
        20154, 27155, 21084,    # Seal of Righteousness
        31801, 348700,           # Seal of Vengeance / Seal of the Martyr
        20375, 20424,            # Seal of Command
        27158,                   # Seal of the Crusader
        27183,                   # Holy Shield (Prot)
        32223,                   # Crusader Aura
        27141,                   # Blessing of Kings
        19746,                   # Concentration Aura
        20218,                   # Sanctity Aura
        25898,                   # Greater Blessing of Salvation
        31884,                   # Avenging Wrath
        31789,                   # Righteous Defense (Prot)
        20924, 27173,            # Consecration
        35395,                   # Crusader Strike (Ret)
        20271,                   # Judgement
        20216,                   # Divine Favor (Holy)
        31842,                   # Divine Illumination (Holy)
        27154,                   # Lay on Hands
        27166,                   # Seal of Wisdom
    },
    "Hunter": {
        27044, 25296,            # Aspect of the Hawk
        27045,                   # Aspect of the Viper
        27016, 25294,            # Arcane Shot
        27065,                   # Multi-Shot
        34120,                   # Steady Shot
        19434, 25295,            # Aimed Shot
        3045,                    # Rapid Fire
        27067, 34026,            # Kill Command
        19386,                   # Wyvern Sting
        3034,                    # Viper Sting
    },
    "Rogue": {
        26866, 11300, 8647,     # Expose Armor
        26865, 11299,            # Eviscerate
        26862, 6774,             # Slice and Dice
        14177,                   # Cold Blood
        13877,                   # Blade Flurry
        13750,                   # Adrenaline Rush
        26889,                   # Vanish
        32684,                   # Shiv
        26679,                   # Deadly Throw
        8676,                    # Ambush
        1943,                    # Rupture
    },
    "Priest": {
        25233,                   # Prayer of Healing
        27681, 25222,            # Renew
        27803, 32999, 32996,    # Prayer of Mending
        15473,                   # Shadowform
        25392, 21562,            # Prayer of Fortitude
        15286,                   # Vampiric Embrace
        34914,                   # Vampiric Touch
        28276,                   # Shadow Word: Death
        25433, 10917, 25235,    # Greater / Flash Heal
    },
    "Shaman": {
        10623, 25422, 25423,    # Chain Heal (Resto)
        8004, 25357, 25567,     # Healing Wave (Resto)
        10466, 25420,            # Lesser Healing Wave (Resto)
        33736,                   # Water Shield (Resto + Ele)
        974, 32594,              # Earth Shield (Resto)
        32175, 32176, 25456,    # Stormstrike (Enhance)
        2825, 32182,             # Bloodlust / Heroism
        25441, 10414, 25442,    # Chain Lightning (Ele)
        25449,                   # Lightning Bolt (Ele)
        16166,                   # Elemental Mastery (Ele)
        30706,                   # Totem of Wrath (Ele — definitive)
        25528,                   # Strength of Earth Totem
        3738,                    # Wrath of Air Totem (Ele priority)
        25570, 5675,             # Mana Spring Totem
        8143,                    # Tremor Totem
        25454,                   # Earth Shock (Ele DPS rotation)
    },
    "Mage": {
        27127, 10157,            # Arcane Brilliance
        25306,                   # Fireball
        27087, 25304,            # Frostbolt
        12051,                   # Evocation
        11958,                   # Ice Block
        27101, 27100,            # Conjure Mana Emerald/Ruby
        30451,                   # Arcane Blast
        30455,                   # Ice Lance
        31661,                   # Dragon's Breath
        12826, 27132,            # Pyroblast
    },
    "Warlock": {
        27222, 31818,            # Life Tap
        27209,                   # Corruption
        27216,                   # Immolate
        25309,                   # Shadow Bolt
        27243,                   # Curse of Agony
        30321,                   # Unstable Affliction
        28610,                   # Shadow Ward
        28189,                   # Fel Armor
    },
    "Druid": {
        26991, 21849,            # Gift of the Wild
        25297,                   # Mark of the Wild
        8936, 26980,             # Regrowth
        33763,                   # Lifebloom
        26981, 25299,            # Rejuvenation
        27638,                   # Healing Touch
        22812,                   # Barkskin
        33831,                   # Force of Nature
        24858,                   # Moonkin Form
        26984, 26985,            # Wrath, Starfire
        6795,                    # Growl
        9634,                    # Dire Bear Form
    },
}


for cls, spells in _RAW_CLASS_SPELLS.items():
    for sid in spells:
        _CLASS_SPELLS[sid] = cls

# ---------------------------------------------------------------------------
# Role-indicator spell sets
# ---------------------------------------------------------------------------

# Healing role — strong indicators
HEALER_INDICATOR_SPELLS = {
    27803, 32999, 32996,    # Prayer of Mending
    10623, 25422, 25423,    # Chain Heal
    33763,                   # Lifebloom
    26980, 8936,             # Regrowth
    33736,                   # Water Shield (Resto Shaman primary indicator)
    974, 32594,              # Earth Shield
    25233,                   # Prayer of Healing
    27638, 25433, 10917,    # Healing Touch / Greater Heal / Flash Heal
    27136, 27137,            # Holy Light / Flash of Light (Paladin healer)
    20216, 31842,            # Divine Favor, Divine Illumination (Holy Pally only)
    27154,                   # Lay on Hands
}

# Tank role — strong indicators (must be unambiguously prot-only)
TANK_INDICATOR_SPELLS = {
    30330, 30022,            # Devastate (Prot Warrior only)
    30356,                   # Shield Slam rank 11 (high-level, Prot Warrior)
    871, 12975, 2565,        # Shield Wall, Last Stand, Shield Block (Prot cooldowns)
    30357,                   # Revenge (Prot Warrior)
    31789,                   # Righteous Defense (Prot Paladin)
    27183,                   # Holy Shield (Prot Paladin)
    6795,                    # Growl (Feral tank Druid)
    9634,                    # Dire Bear Form
    355,                     # Taunt (Warrior)
}

# Fury Warrior indicators
FURY_WARRIOR_SPELLS = {
    30335, 23881,            # Bloodthirst
    1680, 25251,             # Whirlwind
    12292,                   # Death Wish
    2458,                    # Berserker Stance
    13877,                   # Blade Flurry (Rogue — not Warrior, ignore)
}

# Arms Warrior indicators
ARMS_WARRIOR_SPELLS = {
    29707, 25248, 12294,    # Mortal Strike
    12328,                   # Sweeping Strikes
    2457,                    # Battle Stance
}

# Enhancement Shaman indicators
ENHANCE_SHAMAN_SPELLS = {
    32175, 32176, 25456,    # Stormstrike
}

# Elemental Shaman indicators — spells used in Ele rotation or Ele-only talents
ELEMENTAL_SHAMAN_SPELLS = {
    25449,                   # Lightning Bolt (Ele rotation)
    16166,                   # Elemental Mastery (Ele talent, definitive)
    30706,                   # Totem of Wrath (Ele talent, definitive)
    25441, 10414, 25442,    # Chain Lightning (Ele rotation)
    25454,                   # Earth Shock (Ele uses as filler)
    3738,                    # Wrath of Air Totem (Ele-preferred)
}

# Ret Paladin indicators
RET_PALADIN_SPELLS = {
    35395,                   # Crusader Strike
    20375, 20424,            # Seal of Command
    348700,                  # Seal of the Martyr
    31884,                   # Avenging Wrath (also Holy, but combined with Seal of Command = Ret)
}

# Prot Paladin indicators
PROT_PALADIN_SPELLS = {
    31789,                   # Righteous Defense
    27183,                   # Holy Shield
}

# Holy Paladin indicators
HOLY_PALADIN_SPELLS = {
    20216,                   # Divine Favor
    31842,                   # Divine Illumination
    27136, 27137,            # Holy Light / Flash of Light
    27154,                   # Lay on Hands
    27166,                   # Seal of Wisdom
}


def infer_role(cls: str, spells_cast: set[int]) -> str:
    """
    Returns one of: melee_dps | ranged_dps | caster_dps | healer | tank | unknown
    Uses class + spell pattern matching for accurate sub-spec disambiguation.
    """
    if not cls or cls == "Unknown":
        return "unknown"

    def hits(s): return len(spells_cast & s)

    if cls == "Warrior":
        tank_score  = hits(TANK_INDICATOR_SPELLS)
        fury_score  = hits(FURY_WARRIOR_SPELLS)
        # Hard prot spells: Devastate or Shield Wall/Last Stand/Block alone are
        # definitive. Require 2+ tank hits OR one of the absolute prot-only
        # spells (Devastate, Revenge, Shield Wall, Last Stand) to call tank.
        # This prevents a Fury warrior who uses Shield Slam occasionally from
        # being mislabelled.
        HARD_PROT = {30330, 30022, 871, 12975, 30357}  # Devastate, Shield Wall, Last Stand, Revenge
        hard_prot = len(spells_cast & HARD_PROT)
        if hard_prot >= 1 or tank_score >= 2:
            return "tank"
        # Fury wins if Bloodthirst or Whirlwind present
        if fury_score >= 1:
            return "melee_dps"
        return "melee_dps"

    if cls == "Paladin":
        holy_score  = hits(HOLY_PALADIN_SPELLS)
        prot_score  = hits(PROT_PALADIN_SPELLS)
        ret_score   = hits(RET_PALADIN_SPELLS)
        # Holy Paladin: Divine Favor or Divine Illumination are definitive
        if holy_score >= 1:
            return "healer"
        # Prot: Righteous Defense or Holy Shield
        if prot_score >= 1:
            return "tank"
        # Ret: Crusader Strike or Seal of Command/Martyr
        if ret_score >= 1:
            return "melee_dps"
        # Fallback: if casting heals, probably Holy
        if hits(HEALER_INDICATOR_SPELLS) >= 1:
            return "healer"
        return "melee_dps"

    if cls == "Druid":
        if hits(HEALER_INDICATOR_SPELLS) >= 1:
            return "healer"
        if hits(TANK_INDICATOR_SPELLS) >= 1:
            return "tank"
        return "caster_dps"  # Balance

    if cls == "Shaman":
        ele_score     = hits(ELEMENTAL_SHAMAN_SPELLS)
        enhance_score = hits(ENHANCE_SHAMAN_SPELLS)
        healer_score  = hits(HEALER_INDICATOR_SPELLS)
        # Elemental-only spells are definitive (Lightning Bolt, Elemental Mastery,
        # Totem of Wrath, Chain Lightning). If any present → Elemental.
        # Note: Chain Heal and Earth Shield are Resto-only so healer_score is
        # reliable when non-zero. Water Shield is used by both Resto and Elemental
        # so we don't count it as a healer-only indicator here.
        RESTO_ONLY = {10623, 25422, 25423, 974, 32594}  # Chain Heal, Earth Shield
        resto_score = len(spells_cast & RESTO_ONLY)
        if enhance_score >= 1:
            return "melee_dps"
        if ele_score >= 1 and resto_score == 0:
            return "caster_dps"
        if resto_score >= 1:
            return "healer"
        if ele_score >= 1:
            # Has elemental spells but also healer spells (rare hybrid) — go elemental
            return "caster_dps"
        return "healer" if healer_score >= 1 else "caster_dps"

    if cls == "Priest":
        # Shadowform = Shadow DPS
        return "caster_dps" if 15473 in spells_cast else "healer"

    if cls == "Hunter":
        return "ranged_dps"

    if cls in ("Warrior", "Rogue"):
        return "melee_dps"

    if cls in ("Mage", "Warlock"):
        return "caster_dps"

    return "unknown"


def infer_class_from_spells(spells_cast: set[int]) -> str:
    """Vote for most likely class from spell IDs seen."""
    votes: dict[str, int] = {}
    for sid in spells_cast:
        if sid in _CLASS_SPELLS:
            cls = _CLASS_SPELLS[sid]
            votes[cls] = votes.get(cls, 0) + 1
    if not votes:
        return "Unknown"
    return max(votes, key=votes.__getitem__)

# Scoring constants
# ---------------------------------------------------------------------------

# Flask: any flask = full score, covers both elixir slots
FLASK_SCORE = 1.0

# Battle elixir quality by role
BATTLE_ELIXIR_QUALITY: dict[str, dict[str, float]] = {
    "melee_dps": {
        "Elixir of Major Agility":   1.0,
        "Elixir of the Mongoose":    1.0,
        "Onslaught Elixir":          1.0,
        "Elixir of Major Strength":  1.0,
        "Elixir of Demonslaying":    1.0,   # BiS vs demons — Mag, BT, Hyjal
        "Elixir of Mastery":         0.85,
        "Adept's Elixir":            0.5,
    },
    "tank": {
        "Elixir of Major Agility":   1.0,
        "Elixir of Mastery":         0.9,
        "Elixir of the Mongoose":    0.85,
        "Elixir of Demonslaying":    0.85,  # situational but valid on demon bosses
        "Onslaught Elixir":          0.75,
        "Elixir of Major Strength":  0.75,
    },
    "caster_dps": {
        "Adept's Elixir":                1.0,
        "Elixir of Major Shadow Power":  1.0,
        "Elixir of Major Firepower":     1.0,
        "Elixir of Major Frost Power":   1.0,
        "Elixir of Mastery":             0.85,
        "Elixir of Healing Power":       0.5,
        "Elixir of Major Strength":      0.0,
        "Elixir of Major Agility":       0.0,
    },
    "healer": {
        "Elixir of Healing Power":       1.0,
        "Adept's Elixir":                0.85,
        "Elixir of Mastery":             0.8,
        "Elixir of Major Shadow Power":  0.4,
    },
}
BATTLE_ELIXIR_DEFAULT = 0.6  # used if consumable not in role-specific table

# Guardian elixir quality (same for all roles mostly)
GUARDIAN_ELIXIR_QUALITY: dict[str, float] = {
    "Elixir of Draenic Wisdom":   1.0,
    "Elixir of Major Mageblood":  1.0,
    "Elixir of Major Fortitude":  0.9,
    "Elixir of Major Defense":    0.9,
    "Earthen Elixir":             0.75,
    "Elixir of Empowerment":      0.85,
    "Elixir of Ironskin":         0.5,
}
GUARDIAN_ELIXIR_TANK_OVERRIDES = {
    "Elixir of Major Defense":    1.0,
    "Earthen Elixir":             0.9,
    "Elixir of Major Fortitude":  0.9,
    "Elixir of Draenic Wisdom":   0.6,
    "Elixir of Major Mageblood":  0.5,
}
GUARDIAN_ELIXIR_DEFAULT = 0.5

# Potion quality by role
POTION_QUALITY: dict[str, dict[str, float]] = {
    "melee_dps": {
        "Haste Potion":          1.0,   # +400 attack speed rating — BiS for most melee
        "Heroic Potion":         0.9,   # +35 str / +175 hp — good for str-scaling classes
        "Super Healing Potion":  0.6,
        "Free Action Potion":    0.5,
        "Living Action Potion":  0.5,
    },
    "ranged_dps": {
        # Hunters: Haste Potion gives +38% ranged attack speed — clear BiS
        "Haste Potion":          1.0,
        "Super Mana Potion":     0.7,   # Hunters use mana but not heavily
        "Major Mana Potion":     0.5,
        "Fel Mana Potion":       0.6,
    },
    "tank": {
        "Super Healing Potion":  1.0,
        "Heroic Potion":         0.85,
        "Major Healing Potion":  0.6,
    },
    "caster_dps": {
        # Destruction Potion is the only correct DPS pot for casters in TBC
        "Destruction Potion":    1.0,
        # Mana pots score 0 for caster DPS — they should always use Destruction Potion.
        # A mana pot is a pure DPS loss vs Destruction Potion regardless of mana situation.
        "Super Mana Potion":     0.0,
        "Fel Mana Potion":       0.0,
        "Major Mana Potion":     0.0,
        "Haste Potion":          0.0,   # does NOT increase spell casting speed in TBC
    },
    "healer": {
        "Super Mana Potion":     1.0,
        "Fel Mana Potion":       0.9,
        "Major Mana Potion":     0.6,
        "Super Healing Potion":  0.7,
    },
}
POTION_DEFAULT = 0.5

# Rune bonus (runes share a separate cooldown from potions)
RUNE_NAMES = {"Dark Rune", "Demonic Rune"}
RUNE_BONUS  = 0.25   # added to potion score, capped at 1.0

# Food: any valid raid food = full score
FOOD_SCORE  = 1.0

# Scroll scoring: rank V or IV, filtered by role
SCROLL_SCORES: dict[str, dict[str, float]] = {
    # role -> consumable_name -> score
    "melee_dps": {
        "Scroll of Agility V":    1.0,
        "Scroll of Agility IV":   0.75,
        "Scroll of Strength V":   1.0,
        "Scroll of Strength IV":  0.75,
        # protection/stamina/spirit/intellect scrolls useless for melee dps
        "Scroll of Protection V":   0.0,
        "Scroll of Protection IV":  0.0,
        "Scroll of Stamina V":      0.3,
        "Scroll of Spirit V":       0.0,
        "Scroll of Intellect V":    0.0,
    },
    "tank": {
        "Scroll of Protection V":   1.0,
        "Scroll of Protection IV":  0.75,
        "Scroll of Stamina V":      0.85,
        "Scroll of Stamina IV":     0.6,
        "Scroll of Agility V":      0.85,  # dodge
        "Scroll of Agility IV":     0.65,
        "Scroll of Strength V":     0.7,
        "Scroll of Strength IV":    0.5,
        "Scroll of Intellect V":    0.0,
        "Scroll of Spirit V":       0.0,
    },
    "caster_dps": {
        # Mages/Warlocks already have Arcane Brilliance (int) and Fortitude (sta)
        # so int/sta scrolls are redundant for them
        "Scroll of Stamina V":      0.0,   # have PW:F
        "Scroll of Intellect V":    0.0,   # have AB
        "Scroll of Spirit V":       0.0,
        "Scroll of Protection V":   0.3,   # situational (resist fights)
        "Scroll of Agility V":      0.0,
        "Scroll of Strength V":     0.0,
        "Scroll of Agility IV":     0.0,
        "Scroll of Strength IV":    0.0,
    },
    "healer": {
        "Scroll of Spirit V":       1.0,   # great for regen
        "Scroll of Spirit IV":      0.75,
        "Scroll of Intellect V":    0.85,  # mana pool
        "Scroll of Intellect IV":   0.65,
        "Scroll of Stamina V":      0.5,
        "Scroll of Protection V":   0.2,
        "Scroll of Agility V":      0.0,
        "Scroll of Strength V":     0.0,
    },
}
SCROLL_DEFAULT_SCORE = 0.4   # unknown scroll type gets partial credit

# Weapon buff scoring by role
WEAPON_BUFF_SCORES: dict[str, dict[str, float]] = {
    "melee_dps": {
        "Adamantite Sharpening Stone": 1.0,
        "Adamantite Weightstone":      1.0,
        "Elemental Sharpening Stone":  0.85,
        "Dense Sharpening Stone":      0.4,
        "Superior Wizard Oil":         0.0,
        "Brilliant Wizard Oil":        0.0,
        "Superior Mana Oil":           0.0,
        "Brilliant Mana Oil":          0.0,
    },
    "tank": {
        "Adamantite Sharpening Stone": 1.0,
        "Adamantite Weightstone":      1.0,
        "Elemental Sharpening Stone":  0.85,
        "Dense Sharpening Stone":      0.5,
    },
    "caster_dps": {
        "Superior Wizard Oil":   1.0,
        "Brilliant Wizard Oil":  0.85,
        "Superior Mana Oil":     0.5,
        "Brilliant Mana Oil":    0.4,
        "Adamantite Sharpening Stone": 0.0,
    },
    "healer": {
        "Brilliant Mana Oil":    1.0,
        "Superior Mana Oil":     0.85,
        "Brilliant Wizard Oil":  0.7,
        "Superior Wizard Oil":   0.6,
        "Adamantite Sharpening Stone": 0.0,
    },
}
WEAPON_BUFF_DEFAULT = 0.5

# Slot weights for overall score
SLOT_WEIGHTS = {
    "flask_or_elixir": 2.5,   # flask (both slots) or max(battle_score+guardian_score weighted)
    "potion":          2.0,
    "food":            1.5,
    "scroll":          0.5,    # bonus
    "weapon_buff":     0.5,    # bonus
    "bloodlust":       0.5,    # only applies to the Shaman/Pally who cast BL/Heroism
}

# Fight-specific Bloodlust windows: boss_name -> (ideal_start, ideal_end, note)
# For bosses not in this table, generic rules apply.
FIGHT_BL_WINDOWS: dict[str, tuple[int, int, str]] = {
    "High King Maulgar":      (0,  20, "burn from pull"),
    "Gruul the Dragonkiller": (0,  90, "pull or post-Shatter"),
    "Magtheridon":            (90, 150, "during/after first cube phase"),
    # T5 — add as we see them
    "Hydross the Unstable":   (0,  30, "pull phase"),
    "The Lurker Below":       (0,  30, "standard pull"),
    "Void Reaver":            (0,  30, "burn from pull"),
    "Lady Vashj":             (60, 150, "phase 2 transition"),
    "Kael'thas Sunstrider":   (0,  30, "phase 1 burn"),
}

# Letter grade thresholds
GRADE_THRESHOLDS = [
    (90, "S"),
    (75, "A"),
    (60, "B"),
    (45, "C"),
    (30, "D"),
    (0,  "F"),
]


# ---------------------------------------------------------------------------
# Score result dataclass
# ---------------------------------------------------------------------------

@dataclass
class SlotScore:
    score: float          # 0.0 – 1.0
    used: list[str]       # consumable names applied
    note: str = ""        # human-readable explanation

@dataclass
class PlayerScore:
    player: str
    cls: str
    role: str
    # individual slot scores
    flask:        SlotScore = field(default_factory=lambda: SlotScore(0.0, []))
    battle_elixir:SlotScore = field(default_factory=lambda: SlotScore(0.0, []))
    guardian_elixir:SlotScore = field(default_factory=lambda: SlotScore(0.0, []))
    potion:       SlotScore = field(default_factory=lambda: SlotScore(0.0, []))
    food:         SlotScore = field(default_factory=lambda: SlotScore(0.0, []))
    scroll:       SlotScore = field(default_factory=lambda: SlotScore(0.0, []))
    weapon_buff:  SlotScore = field(default_factory=lambda: SlotScore(0.0, []))
    bloodlust:    SlotScore = field(default_factory=lambda: SlotScore(0.0, [], "N/A"))
    # overall
    overall_score: float = 0.0
    grade: str = "F"

    def to_dict(self) -> dict:
        return {
            "player": self.player,
            "class": self.cls,
            "role": self.role,
            "overall_score": round(self.overall_score, 1),
            "grade": self.grade,
            "slots": {
                "flask":          {"score": round(self.flask.score, 2),          "used": self.flask.used,          "note": self.flask.note},
                "battle_elixir":  {"score": round(self.battle_elixir.score, 2),  "used": self.battle_elixir.used,  "note": self.battle_elixir.note},
                "guardian_elixir":{"score": round(self.guardian_elixir.score, 2),"used": self.guardian_elixir.used,"note": self.guardian_elixir.note},
                "potion":         {"score": round(self.potion.score, 2),          "used": self.potion.used,         "note": self.potion.note},
                "food":           {"score": round(self.food.score, 2),            "used": self.food.used,           "note": self.food.note},
                "scroll":         {"score": round(self.scroll.score, 2),          "used": self.scroll.used,         "note": self.scroll.note},
                "weapon_buff":    {"score": round(self.weapon_buff.score, 2),     "used": self.weapon_buff.used,    "note": self.weapon_buff.note},
            },
        }


# ---------------------------------------------------------------------------
# Scoring engine
# ---------------------------------------------------------------------------

def _grade(score_0_100: float) -> str:
    for threshold, letter in GRADE_THRESHOLDS:
        if score_0_100 >= threshold:
            return letter
    return "F"


def _best_quality(names: list[str], quality_table: dict[str, float], default: float) -> tuple[float, str]:
    """Return (best_score, best_name) from a list of consumable names."""
    best_score = 0.0
    best_name = ""
    for name in names:
        q = quality_table.get(name, default)
        if q > best_score:
            best_score = q
            best_name = name
    return best_score, best_name


def score_player(
    player: str,
    summary: dict[str, list[str]],  # category → [consumable names]
    spells_cast: set[int],
    duration_secs: float,
    bloodlust_time_secs: float | None = None,  # seconds into fight BL was cast
    potion_times: list[float] | None = None,   # seconds into fight each potion was used
    potion_deficits: list[tuple[float, float, float]] | None = None,
    # list of (deficit_frac, overflow_frac, elapsed_secs) from SPELL_ENERGIZE
    # deficit_frac  = (restored - overflow) / max_mana  -- how empty the player was
    # overflow_frac = overflow / max_mana                -- mana wasted past the cap
    # elapsed_secs  = seconds into fight when pot was used
    oom_times: list[float] | None = None,
    # elapsed seconds of each "Not enough mana" SPELL_CAST_FAILED event
) -> PlayerScore:
    """
    Score a single player's consumable usage for one encounter.
    summary      = encounter.get_summary()[player]
    spells_cast  = spell IDs cast by the player (for class inference)
    duration_secs= encounter length in seconds
    bloodlust_time_secs = when BL/Heroism was cast
    potion_times = seconds into fight for each potion cast
    potion_deficits = (deficit_frac, overflow_frac, elapsed) from SPELL_ENERGIZE
    """
    if potion_times is None:
        potion_times = []
    if potion_deficits is None:
        potion_deficits = []
    if oom_times is None:
        oom_times = []
    cls  = infer_class_from_spells(spells_cast)
    role = infer_role(cls, spells_cast)

    result = PlayerScore(player=player, cls=cls, role=role)

    flasks   = summary.get("Flask", [])
    battle   = summary.get("Elixir (Battle)", [])
    guardian = summary.get("Elixir (Guardian)", [])
    potions  = summary.get("Potion", [])
    foods    = summary.get("Food", [])
    scrolls  = summary.get("Scroll", [])
    wbuffs   = summary.get("Weapon Buff", [])

    # ── Flask / Elixir slots ──────────────────────────────────────────
    if flasks:
        # Flask fills both slots
        result.flask = SlotScore(1.0, flasks, "Fills both battle & guardian slot")
        result.battle_elixir  = SlotScore(1.0, [], "Covered by flask")
        result.guardian_elixir= SlotScore(1.0, [], "Covered by flask")
    else:
        result.flask = SlotScore(0.0, [], "No flask used")
        # Score battle elixir
        if battle:
            role_table = BATTLE_ELIXIR_QUALITY.get(role, {})
            bscore, _ = _best_quality(battle, role_table, BATTLE_ELIXIR_DEFAULT)
            # note if wrong type for role
            note = ""
            if role in ("melee_dps", "tank") and all(
                n in ("Elixir of Healing Power", "Adept's Elixir") for n in battle
            ):
                note = "⚠ Healer elixir on melee"
            elif role in ("caster_dps", "healer") and all(
                n in ("Elixir of Major Agility", "Elixir of Major Strength",
                       "Elixir of the Mongoose", "Onslaught Elixir") for n in battle
            ):
                note = "⚠ Melee elixir on caster"
            result.battle_elixir = SlotScore(bscore, battle, note)
        else:
            result.battle_elixir = SlotScore(0.0, [], "No battle elixir")

        # Score guardian elixir
        if guardian:
            gtable = (GUARDIAN_ELIXIR_TANK_OVERRIDES
                      if role == "tank" else GUARDIAN_ELIXIR_QUALITY)
            gscore, _ = _best_quality(guardian, gtable, GUARDIAN_ELIXIR_DEFAULT)
            result.guardian_elixir = SlotScore(gscore, guardian, "")
        else:
            result.guardian_elixir = SlotScore(0.0, [], "No guardian elixir")

    # ── Potion slot ───────────────────────────────────────────────────
    # Scoring rules (per spec):
    #
    # MELEE DPS / RANGE CASTER DPS:
    #   Fight > 150s: expect 2 pots → 2 uses = 100%, 1 use in line with BL = 100%,
    #                 1 use not in BL = 50%, 0 uses = 0%
    #   Fight ≤ 150s: any 1 use = 100%, 0 uses = 0%
    #   Caster DPS using Haste Potion → note warning (melee haste only in TBC)
    #
    # HEALERS:
    #   Score only on pot quality. No "expected uses" penalty.
    #   Only deduct if they went OOM (wand use detected = definitive OOM signal).
    #   OOM penalty: -0.30 per wand period if pot was available at the time.
    #
    # TANKS:
    #   Score on pot quality only. Tanks manage HP not mana; no usage pressure.
    #
    # ALL ROLES:
    #   Hard OOM via SPELL_CAST_FAILED "Not enough mana" → -0.25 per event
    #   Rune use adds RUNE_BONUS on top (runes have separate cooldown).

    POT_COOLDOWN = 120.0
    LONG_FIGHT   = 150.0   # threshold for "expect 2 pots" rule
    BL_WINDOW    = 10.0    # seconds either side of BL cast

    role_pots   = POTION_QUALITY.get(role, {})
    actual_pots = [p for p in potions if p not in RUNE_NAMES]
    runes_used  = [p for p in potions if p in RUNE_NAMES]
    uses        = len(actual_pots)

    MANA_POT_NAMES = {"Super Mana Potion", "Major Mana Potion", "Fel Mana Potion",
                      "Dark Rune", "Demonic Rune"}
    has_mana_pots = any(p in MANA_POT_NAMES for p in (actual_pots + runes_used))

    if actual_pots:
        quality, best_pot = _best_quality(actual_pots, role_pots, POTION_DEFAULT)
        pot_score = quality
        notes = []

        # ── Caster DPS: wrong potion type warnings ─────────────────
        # Haste Potion gives +400 attack speed rating = melee/ranged attack speed only.
        # It has zero effect on spell casting speed in TBC.
        # NOTE: check actual_pots directly — _best_quality returns best_name="" when
        # the best score is 0.0 (as it is for Haste Potion on caster_dps), so
        # `best_pot == "Haste Potion"` would never be True.
        if role == "caster_dps" and "Haste Potion" in actual_pots:
            notes.append("⚠ Haste Pot = attack speed only, use Destruction Potion")
        _MANA_POT_NAMES_CASTER = {"Super Mana Potion", "Fel Mana Potion", "Major Mana Potion"}
        if role == "caster_dps" and any(p in _MANA_POT_NAMES_CASTER for p in actual_pots):
            notes.append("⚠ Mana Pot = DPS loss vs Destruction Potion")

        # ── DPS usage check (melee + ranged + caster) ──────────────
        if role in ("melee_dps", "ranged_dps", "caster_dps"):
            long_fight = duration_secs > LONG_FIGHT

            # Check if any use was in BL window
            in_bl = (bloodlust_time_secs is not None and potion_times and
                     any(abs(t - bloodlust_time_secs) <= BL_WINDOW for t in potion_times))

            if long_fight:
                if uses >= 2:
                    pot_score = 1.0
                    notes.append("✓ 2 uses")
                elif uses == 1 and in_bl:
                    pot_score = 1.0
                    notes.append("✓ 1 use in BL window")
                elif uses == 1:
                    pot_score = quality * 0.5
                    notes.append("1 use (expected 2 on this fight length)")
                    if bloodlust_time_secs is not None:
                        closest = min(abs(t - bloodlust_time_secs) for t in potion_times)
                        notes.append(f"⚠ {closest:.0f}s from BL")
            else:
                # Short fight — any use is fine
                pot_score = quality
                notes.append(f"✓ used (fight <{LONG_FIGHT:.0f}s)")

            # BL sync bonus for the one-use case on short fights
            if not long_fight and in_bl:
                notes.append("+BL sync")

        # ── Healers and tanks: quality only, no usage pressure ─────
        # (handled via OOM check below for healers)

        if runes_used:
            pot_score = min(1.0, pot_score + RUNE_BONUS)
            notes.append("+rune")

        note = " · ".join(notes) if notes else f"{uses} use{'s' if uses != 1 else ''}"

        # ── OOM penalties (all roles) ───────────────────────────────
        # 1. Hard OOM: SPELL_CAST_FAILED "Not enough mana"
        # A player is NOT penalised if:
        #   (a) their last pot was within POT_COOLDOWN seconds before OOM (genuinely on CD), OR
        #   (b) they potted within OOM_REACT_GRACE seconds AFTER OOM (reacted correctly —
        #       SPELL_CAST_FAILED fires before the keybind press lands).
        # Fixes vs old code:
        #   • put <= oom_t (was <) so a pot at the same tick as OOM is credited.
        #   • grace window so a post-OOM pot within 15s isn't penalised.
        POT_CD          = POT_COOLDOWN
        OOM_REACT_GRACE = 15.0
        pot_use_times   = sorted(potion_times)

        for oom_t in sorted(oom_times):
            cd_available_at = 0.0
            for put in pot_use_times:
                if put <= oom_t:
                    cd_available_at = put + POT_CD
            pot_on_cd = oom_t < cd_available_at
            reacted   = any(oom_t < put <= oom_t + OOM_REACT_GRACE for put in pot_use_times)

            if pot_on_cd:
                note += f" · OOM at t={oom_t:.0f}s (pot on CD)"
            elif reacted:
                note += f" · OOM at t={oom_t:.0f}s (potted in reaction — ok)"
            else:
                note += f" · ⚠ OOM at t={oom_t:.0f}s (pot available!)"
                pot_score = max(0.0, pot_score - 0.25)



        result.potion = SlotScore(pot_score, actual_pots + runes_used, note)

    elif runes_used:
        result.potion = SlotScore(RUNE_BONUS, runes_used, "Rune only")
    else:
        # No potion used — only penalise DPS on long fights, or anyone who went OOM
        base_note = "No potion used"
        base_score = 0.0

        # OOM with no pot at all = worst case
        if oom_times:
            base_note += " · ⚠ went OOM with no pot!"
        elif role in ("melee_dps", "ranged_dps", "caster_dps") and duration_secs > LONG_FIGHT:
            base_note += f" (expected on {duration_secs:.0f}s fight)"



        result.potion = SlotScore(base_score, [], base_note)

    # ── Food ─────────────────────────────────────────────────────────
    if foods:
        result.food = SlotScore(FOOD_SCORE, foods, "")
    else:
        result.food = SlotScore(0.0, [], "No food buff")

    # ── Scrolls ───────────────────────────────────────────────────────
    if scrolls:
        scroll_table = SCROLL_SCORES.get(role, {})
        best_score = 0.0
        notes = []
        for s in scrolls:
            sq = scroll_table.get(s, SCROLL_DEFAULT_SCORE)
            best_score = max(best_score, sq)
            if sq == 0.0:
                notes.append(f"{s} not useful for {role}")
        note = "; ".join(notes) if notes else ""
        result.scroll = SlotScore(best_score, scrolls, note)
    else:
        result.scroll = SlotScore(0.0, [], "")

    # ── Weapon buff ───────────────────────────────────────────────────
    if wbuffs:
        wb_table = WEAPON_BUFF_SCORES.get(role, {})
        wb_score, _ = _best_quality(wbuffs, wb_table, WEAPON_BUFF_DEFAULT)
        note = ""
        if role in ("caster_dps", "healer") and any(
            "Sharpening" in w or "Weightstone" in w for w in wbuffs
        ):
            note = "⚠ Physical stone on caster"
        elif role == "melee_dps" and any("Oil" in w for w in wbuffs):
            note = "⚠ Spell oil on melee"
        result.weapon_buff = SlotScore(wb_score, wbuffs, note)
    else:
        result.weapon_buff = SlotScore(0.0, [], "")

    # ── Overall score ─────────────────────────────────────────────────
    # Flask/elixir combined score
    if flasks:
        flask_combined = 1.0   # flask = perfect in both slots
    else:
        # Weight battle elixir 60%, guardian 40% within the elixir category
        flask_combined = result.battle_elixir.score * 0.6 + result.guardian_elixir.score * 0.4

    # Scroll and weapon buff are bonus slots — they only add to the score when used,
    # never penalise for absence. Exclude them from the denominator if not used so a
    # melee DPS without a scroll isn't dragged below a player who used a bad one.
    # Gate on score > 0 only: a used-but-worthless scroll (score=0) must NOT remove
    # the slot from the denominator, or the overall score would be artificially inflated.
    scroll_used      = result.scroll.score > 0
    weapon_buff_used = result.weapon_buff.score > 0

    weighted_sum = (
        flask_combined            * SLOT_WEIGHTS["flask_or_elixir"] +
        result.potion.score       * SLOT_WEIGHTS["potion"] +
        result.food.score         * SLOT_WEIGHTS["food"] +
        (result.scroll.score      * SLOT_WEIGHTS["scroll"]      if scroll_used      else 0.0) +
        (result.weapon_buff.score * SLOT_WEIGHTS["weapon_buff"] if weapon_buff_used else 0.0)
        # bloodlust slot scored separately in score_encounter, not here
    )
    total_weight = (
        SLOT_WEIGHTS["flask_or_elixir"] +
        SLOT_WEIGHTS["potion"] +
        SLOT_WEIGHTS["food"] +
        (SLOT_WEIGHTS["scroll"]      if scroll_used      else 0.0) +
        (SLOT_WEIGHTS["weapon_buff"] if weapon_buff_used else 0.0)
    )
    result.overall_score = (weighted_sum / total_weight) * 100
    result.grade = _grade(result.overall_score)

    return result


def score_bloodlust(
    fight_name: str,
    fight_dur: float,
    bl_time: float | None,
) -> SlotScore:
    """
    Score the Shaman (or Paladin) who cast Bloodlust/Heroism.
    Returns a SlotScore with score 0–1 and a note explaining the timing.

    Rules (per user spec + community research):
      • Short fight (≤90s): any use = 1.0, no use = 0.0
      • Fight <2min but >90s: use anywhere = 1.0
      • Long fight (>2min):
          – Generic: ideal t≤30s (debuffs up, max DPS time); latest acceptable first use t=30s
          – If missed: 2nd CD window at t≈120-150s = acceptable (0.60)
          – Very late (>150s) or not used = poor/zero
      • Fight-specific windows (FIGHT_BL_WINDOWS) override the generic rule entirely.
        e.g. Magtheridon ideal = t=90-150s (cube phase); Gruul = t=0-90s (pull or post-Shatter)
    """
    used = ["Bloodlust/Heroism"] if bl_time is not None else []

    if bl_time is None:
        return SlotScore(0.0, [], "Not used")

    # Short fight or fight < 2 min: anywhere is fine
    if fight_dur <= 120:
        return SlotScore(1.0, used, f"✓ t={bl_time:.0f}s (fight <2min, any timing ok)")

    # Fight-specific window overrides
    if fight_name in FIGHT_BL_WINDOWS:
        ideal_s, ideal_e, ctx = FIGHT_BL_WINDOWS[fight_name]
        if ideal_s <= bl_time <= ideal_e:
            return SlotScore(1.0, used, f"✓ t={bl_time:.0f}s — ideal for {fight_name} ({ctx})")
        # Used early on a fight where later is correct (e.g. BL at pull on Magtheridon).
        # MUST be checked before the "slightly late" branch below — both conditions can
        # overlap when ideal_s > 0 and bl_time < ideal_s <= ideal_e + 15.
        elif bl_time < ideal_s:
            return SlotScore(0.50, used,
                f"⚠ t={bl_time:.0f}s — too early for {fight_name} (ideal t={ideal_s}-{ideal_e}s: {ctx})")
        # Within 15s of ideal end = slightly late (bl_time > ideal_e here)
        elif bl_time <= ideal_e + 15:
            return SlotScore(0.85, used, f"t={bl_time:.0f}s — slightly late for {fight_name} (ideal t={ideal_s}-{ideal_e}s)")
        # Missed ideal, within 2nd CD window (t≈120-150s)?
        elif bl_time <= 150 and fight_dur > 240:
            return SlotScore(0.60, used,
                f"t={bl_time:.0f}s — missed ideal window for {fight_name}, used at 2nd CD")
        else:
            return SlotScore(0.25, used,
                f"⚠ t={bl_time:.0f}s — very late for {fight_name} (ideal t={ideal_s}-{ideal_e}s)")

    # Generic long-fight rules
    if bl_time <= 10:
        return SlotScore(1.0,  used, f"✓ t={bl_time:.0f}s — perfect pull timing")
    elif bl_time <= 30:
        return SlotScore(0.95, used, f"✓ t={bl_time:.0f}s — good timing (debuffs up)")
    elif bl_time <= 90:
        return SlotScore(0.65, used, f"t={bl_time:.0f}s — late first use (ideal ≤30s)")
    elif bl_time <= 150 and fight_dur > 240:
        return SlotScore(0.55, used, f"t={bl_time:.0f}s — missed ideal window, used at 2nd CD")
    else:
        return SlotScore(0.20, used, f"⚠ t={bl_time:.0f}s — very late (fight={fight_dur:.0f}s)")


# Bloodlust / Heroism spell IDs
_BLOODLUST_SPELLS = {2825, 32182}
# Potion use spell IDs (from consumables_db DETECT_ON_CAST)
from consumables_db import DETECT_ON_CAST as _DETECT_ON_CAST


def score_encounter(
    encounter,
    player_spells: dict[str, set[int]],
    duration_secs: float,
) -> dict[str, "PlayerScore"]:
    """
    Score all players in an encounter.
    Extracts Bloodlust timing and per-player potion timestamps from
    encounter.potion_events (set by parser) for timing-aware scoring.
    Returns {player_name: PlayerScore}
    """
    summary_all = encounter.get_summary()

    # Find Bloodlust cast time AND the caster
    bloodlust_time: float | None = None
    bloodlust_caster: str | None = None
    potion_event_times: dict[str, list[float]] = {}  # player -> [secs_into_fight]

    enc_events = getattr(encounter, "timed_events", [])
    # player -> list of (deficit_frac, overflow_frac, elapsed_secs) per SPELL_ENERGIZE
    potion_deficits: dict[str, list[tuple[float, float, float]]] = {}

    for event in enc_events:
        elapsed_secs, player, spell_id = event[0], event[1], event[2]
        if spell_id > 0:
            # Regular cast event (positive spell_id)
            if spell_id in _BLOODLUST_SPELLS and bloodlust_time is None:
                bloodlust_time = elapsed_secs
                bloodlust_caster = player
            if spell_id in _DETECT_ON_CAST:
                potion_event_times.setdefault(player, []).append(elapsed_secs)
        else:
            # SPELL_ENERGIZE event encoded with negative spell_id
            # event = (elapsed, player, -sid, deficit_frac, overflow_frac)
            deficit_frac   = event[3] if len(event) > 3 else 0.0
            overflow_frac  = event[4] if len(event) > 4 else 0.0
            potion_deficits.setdefault(player, []).append(
                (deficit_frac, overflow_frac, elapsed_secs)
            )

    # OOM events: player_name -> list of elapsed times when "Not enough mana" fired
    oom_event_times: dict[str, list[float]] = {}
    for (el, player) in getattr(encounter, "oom_events", []):
        oom_event_times.setdefault(player, []).append(el)



    fight_name = getattr(encounter, "encounter_name", "") or ""

    scores = {}
    for player in encounter.roster or list(summary_all.keys()):
        summary  = summary_all.get(player, {})
        spells   = player_spells.get(player, set())
        ptimes   = potion_event_times.get(player, [])
        deficits = potion_deficits.get(player, [])
        oom_times = oom_event_times.get(player, [])
        ps = score_player(
            player, summary, spells, duration_secs,
            bloodlust_time_secs=bloodlust_time,
            potion_times=ptimes,
            potion_deficits=deficits,
            oom_times=oom_times,
        )

        # Score Bloodlust for the player who cast it.
        # TBC Anniversary: BL is raid-wide — only ONE Shaman needs to cast it.
        # Only the caster gets scored. If nobody cast BL, we flag one Shaman.
        if player == bloodlust_caster:
            ps.bloodlust = score_bloodlust(fight_name, duration_secs, bloodlust_time)
        # "No BL caster" case handled after the loop

        # Fold BL score into overall if this player has a BL score
        if ps.bloodlust.note != "N/A":
            bl_contribution = ps.bloodlust.score * SLOT_WEIGHTS["bloodlust"]
            base_weight = sum(v for k, v in SLOT_WEIGHTS.items() if k != "bloodlust")
            total_weight = base_weight + SLOT_WEIGHTS["bloodlust"]
            # Re-derive overall: ((base_score/100 * base_weight) + bl_contribution) / total_weight * 100
            base_pts = (ps.overall_score / 100.0) * base_weight
            ps.overall_score = ((base_pts + bl_contribution) / total_weight) * 100
            ps.grade = _grade(ps.overall_score)

        scores[player] = ps

    # If no Shaman cast BL, flag the first Shaman in the roster (TBC Anniversary:
    # only one needs to cast it, so one person is responsible)
    if bloodlust_time is None:
        for player, ps in scores.items():
            if ps.cls == "Shaman":
                ps.bloodlust = SlotScore(0.0, [], "⚠ No BL used this fight (TBC Anniversary: 1 cast covers whole raid)")
                # Re-fold into overall score
                bl_contribution = 0.0
                base_weight = sum(v for k, v in SLOT_WEIGHTS.items() if k != "bloodlust")
                total_weight = base_weight + SLOT_WEIGHTS["bloodlust"]
                base_pts = (ps.overall_score / 100.0) * base_weight
                ps.overall_score = ((base_pts + bl_contribution) / total_weight) * 100
                ps.grade = _grade(ps.overall_score)
                break  # only flag the first Shaman

    return scores
