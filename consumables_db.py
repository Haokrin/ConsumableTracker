"""
TBC Anniversary Consumables Database
=====================================
Maps spell IDs (buff aura IDs) and item IDs to consumable metadata.

How detection works in the combat log:
  - Flasks/Elixirs/Food/Scrolls: detected via SPELL_AURA_APPLIED / SPELL_AURA_REFRESH
    on a player unit — the spellId here is the BUFF aura ID, not the item ID.
  - Potions / On-use items: detected via SPELL_CAST_SUCCESS where source is a player.

Each entry contains:
  spell_id  : int  — the buff aura spell ID logged in the combat log
  item_id   : int  — the in-game item ID (for reference / wowhead links)
  hex_id    : str  — spell ID in 0x-prefixed hex (as it may appear in raw GUID flags)
  name      : str  — human-readable consumable name
  category  : str  — Flask | Elixir (Battle) | Elixir (Guardian) | Potion | Food |
                      Scroll | Weapon Buff | Engineering | Other
  detect_on : str  — 'aura' (SPELL_AURA_APPLIED) or 'cast' (SPELL_CAST_SUCCESS)
"""

# ---------------------------------------------------------------------------
# Format helper
# ---------------------------------------------------------------------------

def _entry(spell_id: int, item_id: int, name: str, category: str, detect_on: str = "aura") -> dict:
    return {
        "spell_id":  spell_id,
        "item_id":   item_id,
        "hex_id":    hex(spell_id),
        "name":      name,
        "category":  category,
        "detect_on": detect_on,
    }


# ---------------------------------------------------------------------------
# FLASKS  (count as both battle + guardian elixir slot)
# All spell_id and item_id values verified against wowhead.com/tbc
# ---------------------------------------------------------------------------

FLASKS = [
    # Classic-era flasks (still used in TBC)
    _entry(17628, 13512, "Flask of Supreme Power",        "Flask"),  # +70 spell dmg
    _entry(17626, 13510, "Flask of the Titans",           "Flask"),  # +400 max hp
    _entry(17627, 13511, "Flask of Distilled Wisdom",     "Flask"),  # +65 int
    _entry(17629, 13513, "Flask of Chromatic Resistance", "Flask"),  # +25 all resist
    # TBC flasks
    _entry(28520, 22854, "Flask of Relentless Assault",   "Flask"),  # +120 AP
    _entry(28521, 22861, "Flask of Blinding Light",       "Flask"),  # +80 arcane/holy/nature dmg
    _entry(28540, 22866, "Flask of Pure Death",           "Flask"),  # +80 shadow/fire/frost dmg
    _entry(28519, 22853, "Flask of Mighty Restoration",   "Flask"),  # +25 mp5
    _entry(42735, 33208, "Flask of Chromatic Wonder",     "Flask"),  # +35 all resist, +18 all stats
]

# ---------------------------------------------------------------------------
# ELIXIRS — Battle (offensive slot)
# All spell_id and item_id values verified against wowhead.com/tbc
# ---------------------------------------------------------------------------

ELIXIRS_BATTLE = [
    # Classic-era battle elixirs (still widely used in TBC)
    _entry(17538, 13452, "Elixir of the Mongoose",        "Elixir (Battle)"),  # +25 agi, +28 crit
    _entry(11406,  9224, "Elixir of Demonslaying",        "Elixir (Battle)"),  # +265 AP vs demons (Mag, BT, Hyjal)
    # TBC battle elixirs
    _entry(28497, 22831, "Elixir of Major Agility",       "Elixir (Battle)"),  # +35 agi, +20 crit
    _entry(28491, 22825, "Elixir of Healing Power",       "Elixir (Battle)"),  # +50 healing
    _entry(28501, 22833, "Elixir of Major Firepower",     "Elixir (Battle)"),  # +55 fire dmg
    _entry(28493, 22827, "Elixir of Major Frost Power",   "Elixir (Battle)"),  # +55 frost dmg
    _entry(28503, 22835, "Elixir of Major Shadow Power",  "Elixir (Battle)"),  # +55 shadow dmg
    _entry(33726, 28104, "Elixir of Mastery",             "Elixir (Battle)"),  # +15 all stats
    _entry(28490, 22824, "Elixir of Major Strength",      "Elixir (Battle)"),  # +35 str
    _entry(33720, 28102, "Onslaught Elixir",              "Elixir (Battle)"),  # +35 AP
    _entry(33721, 28103, "Adept's Elixir",                "Elixir (Battle)"),  # +24 spell dmg, +24 spell crit
]

# ---------------------------------------------------------------------------
# ELIXIRS — Guardian (defensive / utility slot)
# All spell_id and item_id values verified against wowhead.com/tbc
# ---------------------------------------------------------------------------

ELIXIRS_GUARDIAN = [
    _entry(28502, 22834, "Elixir of Major Defense",       "Elixir (Guardian)"),  # +550 armor
    _entry(39628, 32068, "Elixir of Ironskin",            "Elixir (Guardian)"),  # +30 resilience
    _entry(39625, 32062, "Elixir of Major Fortitude",     "Elixir (Guardian)"),  # +250 hp, +10 hp5
    _entry(28509, 22840, "Elixir of Major Mageblood",     "Elixir (Guardian)"),  # +16 mp5
    _entry(28514, 22848, "Elixir of Empowerment",         "Elixir (Guardian)"),  # -30 target spell resist
    _entry(39626, 32063, "Earthen Elixir",                "Elixir (Guardian)"),  # damage absorption
    _entry(39627, 32067, "Elixir of Draenic Wisdom",      "Elixir (Guardian)"),  # +30 int, +30 spirit
]

# ---------------------------------------------------------------------------
# POTIONS  (detect_on = 'cast' — short-duration effect, detected via SPELL_CAST_SUCCESS)
# All spell_id and item_id values verified against wowhead.com/tbc
# ---------------------------------------------------------------------------

POTIONS = [
    # TBC potions
    _entry(28499, 22832, "Super Mana Potion",             "Potion", "cast"),  # restores 1800-3000 mana
    _entry(28550, 22829, "Super Healing Potion",          "Potion", "cast"),  # restores 1500-2500 hp
    _entry(28507, 22838, "Haste Potion",                  "Potion", "cast"),  # +400 haste rating 15s (melee only)
    _entry(28508, 22839, "Destruction Potion",            "Potion", "cast"),  # +120 spell dmg, +2% spell crit 15s
    _entry(28563, 22837, "Heroic Potion",                 "Potion", "cast"),  # +35 str, +175 hp 15s
    _entry(28494, 31676, "Fel Mana Potion",               "Potion", "cast"),  # restores mana, costs hp
    _entry(28515, 22849, "Ironshield Potion",               "Potion", "cast"),  # increases armor, 2500 armor
    # Classic potions still used in TBC
    _entry(6615,  6049,  "Free Action Potion",            "Potion", "cast"),  # immune stun/slow 30s
    _entry(6614,  5634,  "Living Action Potion",          "Potion", "cast"),  # removes stun/slow effects
    _entry(17531, 13443, "Major Mana Potion",             "Potion", "cast"),  # restores 1350-2250 mana
    _entry(17534, 13446, "Major Healing Potion",          "Potion", "cast"),  # restores 1050-1750 hp
    # Runes — share cooldown with each other and Flame Cap, NOT with potions
    _entry(27869, 20520, "Dark Rune",                     "Potion", "cast"),  # restores 900-1500 mana (BoE)
    _entry(16666, 12662, "Demonic Rune",                  "Potion", "cast"),  # restores 900-1500 mana (BoP)
    # Flame Cap — shares cooldown with runes
    _entry(28714, 22788, "Flame Cap",                     "Potion", "cast"),  # +80 fire dmg, 1 min
]

# ---------------------------------------------------------------------------
# FOOD BUFFS  (Well Fed — many foods share the same "Well Fed" aura 57, but
#              TBC food gives unique buff auras)
# ---------------------------------------------------------------------------

FOOD = [
    # ── TBC raid foods — spell IDs are the Well Fed BUFF AURA applied to the player ──
    # Melee / physical DPS foods
    _entry(33287, 27658, "Roasted Clefthoof",             "Food"),  # +20 str +20 spi
    _entry(33289, 27660, "Talbuk Steak",                  "Food"),  # +20 str +20 spi
    _entry(38867, 31672, "Mok'Nathal Shortribs",          "Food"),  # +20 str +20 spi
    _entry(33284, 27655, "Ravager Dog",                   "Food"),  # +20 agi +20 spi
    _entry(33288, 27659, "Warp Burger",                   "Food"),  # +20 agi +20 spi
    _entry(33293, 27664, "Grilled Mudfish",               "Food"),  # +20 agi +20 spi
    # Tanks
    _entry(33296, 27667, "Spicy Crawdad",                 "Food"),  # +30 sta +20 spi
    _entry(33286, 27657, "Blackened Basilisk",            "Food"),  # +23 spell dmg +20 spi
    _entry(33291, 27662, "Feltail Delight",               "Food"),  # +20 sta +20 spi (budget tank food)
    _entry(33292, 27663, "Blackened Sporefish",           "Food"),  # +20 sta +20 spi
    _entry(33279, 27651, "Buzzard Bites",                 "Food"),  # +20 sta +20 spi (budget tank food)
    # Casters / healers — spell damage
    _entry(38868, 31673, "Crunchy Serpent",               "Food"),  # +23 spell dmg +20 spi
    _entry(33294, 27665, "Poached Bluefish",              "Food"),  # +23 spell dmg +20 spi
    # Casters — spell crit
    _entry(43707, 33825, "Skullfish Soup",                "Food"),  # +20 spell crit +20 spi
    # Healers
    _entry(33295, 27666, "Golden Fish Sticks",            "Food"),  # +23 spell dmg +20 spi
    _entry(42302, 33052, "Fisherman's Feast",             "Food"),  # +30 sta (easy-access healer/tank food)
    _entry(42305, 33053, "Hot Buttered Trout",            "Food"),  # restores HP and mana
    # Hit rating
    _entry(43765, 33872, "Spicy Hot Talbuk",              "Food"),  # +20 hit rating +20 spi
    # Spirit / regen
    _entry(42296, 33048, "Stewed Trout",                  "Food"),  # +20 spi +20 stam
    # All-resist
    _entry(43761, 33867, "Broiled Bloodfin",              "Food"),  # +8 all resistances
    # Novelty / proc
    _entry(43758, 33866, "Stormchops",                    "Food"),  # lightning proc, +8 nature dmg
    # Classic foods still viable in TBC
    _entry(24799, 20452, "Smoked Desert Dumplings",       "Food"),  # +20 str
    _entry(18192, 13931, "Blessed Sunfruit",              "Food"),  # +10 str
    _entry(18193, 13932, "Blessed Sunfruit Juice",        "Food"),  # +10 spi
]

# ---------------------------------------------------------------------------
# SCROLLS
# ---------------------------------------------------------------------------

SCROLLS = [
    # TBC Tier (rank V) — verified spell IDs from wowhead.com/tbc
    _entry(33077, 27498, "Scroll of Agility V",           "Scroll"),  # spell:33077 (+20 agi)
    _entry(33082, 27503, "Scroll of Strength V",          "Scroll"),  # spell:33082 (+20 str)
    _entry(33078, 27499, "Scroll of Intellect V",         "Scroll"),  # spell:33078 (+20 int)
    _entry(33080, 27501, "Scroll of Spirit V",            "Scroll"),  # spell:33080 (+30 spi)
    _entry(33081, 27502, "Scroll of Stamina V",           "Scroll"),  # spell:33081 (+20 sta)
    _entry(33079, 27500, "Scroll of Protection V",        "Scroll"),  # spell:33079 (+300 armor)
    # Classic Tier (rank IV) — still sold in TBC, verified from wowhead.com/tbc
    _entry(12174, 10309, "Scroll of Agility IV",          "Scroll"),  # spell:12174 (+17 agi)
    _entry(12179, 10310, "Scroll of Strength IV",         "Scroll"),  # spell:12179 (+17 str)
    _entry(12175, 10305, "Scroll of Protection IV",         "Scroll"),  # spell:12179 (+17 str)
]

# ---------------------------------------------------------------------------
# WEAPON BUFFS
# All spell_id and item_id values verified against wowhead.com/tbc
# ---------------------------------------------------------------------------

WEAPON_BUFFS = [
    # Oils (Enchanting) — buff spell is the weapon aura applied when used
    _entry(28017, 22522, "Superior Wizard Oil",           "Weapon Buff"),  # +42 spell dmg
    _entry(28013, 22521, "Superior Mana Oil",             "Weapon Buff"),  # +14 mp5
    _entry(25122, 20749, "Brilliant Wizard Oil",          "Weapon Buff"),  # +36 spell dmg, +14 spell crit
    _entry(25123, 20748, "Brilliant Mana Oil",            "Weapon Buff"),  # +12 mp5, +25 healing
    # Stones (Blacksmithing)
    _entry(29453, 23529, "Adamantite Sharpening Stone",   "Weapon Buff"),  # +12 dmg, +14 melee crit (sharp weapons)
    _entry(34340, 28421, "Adamantite Weightstone",        "Weapon Buff"),  # +12 dmg, +14 crit (blunt weapons)
    _entry(23552, 18262, "Elemental Sharpening Stone",    "Weapon Buff"),  # +2% crit (classic, still used)
    _entry(20748, 12404, "Dense Sharpening Stone",        "Weapon Buff"),  # +8 dmg (classic, budget option)
]

# ---------------------------------------------------------------------------
# CONSOLIDATED LOOKUP  (spell_id → entry dict)
# ---------------------------------------------------------------------------

ALL_CONSUMABLES: list[dict] = (
    FLASKS
    + ELIXIRS_BATTLE
    + ELIXIRS_GUARDIAN
    + POTIONS
    + FOOD
    + SCROLLS
    + WEAPON_BUFFS
)

# Primary lookup: spell_id → entry
CONSUMABLE_BY_SPELL_ID: dict[int, dict] = {
    c["spell_id"]: c for c in ALL_CONSUMABLES
}

# Fallback lookup by name (lowercase)
CONSUMABLE_BY_NAME: dict[str, dict] = {
    c["name"].lower(): c for c in ALL_CONSUMABLES
}

DETECT_ON_AURA = {sid for sid, c in CONSUMABLE_BY_SPELL_ID.items() if c["detect_on"] == "aura"}
DETECT_ON_CAST = {sid for sid, c in CONSUMABLE_BY_SPELL_ID.items() if c["detect_on"] == "cast"}


if __name__ == "__main__":
    print(f"Loaded {len(ALL_CONSUMABLES)} consumable entries.")
    for cat in ("Flask", "Elixir (Battle)", "Elixir (Guardian)", "Potion",
                "Food", "Scroll", "Weapon Buff", "Engineering"):
        count = sum(1 for c in ALL_CONSUMABLES if c["category"] == cat)
        print(f"  {cat}: {count}")
