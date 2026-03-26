"""HTML Report Generator with scoring."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path

from parser import EncounterData
from scoring import score_encounter, PlayerScore

CATEGORY_ORDER = ["Flask","Elixir (Battle)","Elixir (Guardian)","Potion","Food","Scroll","Weapon Buff","Engineering","Other"]
CATEGORY_ICONS = {"Flask":"⚗️","Elixir (Battle)":"⚔️","Elixir (Guardian)":"🛡️","Potion":"🧪","Food":"🍖","Scroll":"📜","Weapon Buff":"🗡️","Engineering":"⚙️","Other":"✨"}

def _slug(cat): return cat.lower().replace(" ","_").replace("(","").replace(")","").replace("/","_")

def _grade_color(grade):
    return {"S":"#ffd700","A":"#4caf82","B":"#5b9bd5","C":"#e0a84a","D":"#c07a3a","F":"#c05252"}.get(grade,"#888")

def _score_bar(score_0_1):
    pct = int(score_0_1 * 100)
    color = "#4caf82" if pct>=75 else "#e0a84a" if pct>=50 else "#c05252"
    return f'<div class="score-bar"><div class="score-fill" style="width:{pct}%;background:{color}"></div></div>'

def _render_slot_row(label, icon, slot):
    if not slot.used and slot.score == 0.0:
        return f'<div class="slot-row empty"><span class="slot-icon">{icon}</span><span class="slot-label">{label}</span><span class="slot-none">—</span></div>'
    pills = "".join(f'<span class="item-pill {_slug(label)}">{i}</span>' for i in slot.used)
    note_html = f'<span class="slot-note">{slot.note}</span>' if slot.note else ""
    bar = _score_bar(slot.score)
    return f'''<div class="slot-row">
      <span class="slot-icon">{icon}</span>
      <span class="slot-label">{label}</span>
      <div class="slot-content">
        <div class="slot-pills">{pills}</div>
        {note_html}
        {bar}
      </div>
      <span class="slot-score">{slot.score:.0%}</span>
    </div>'''

def _render_player_card(player, summary, ps: PlayerScore | None):
    if ps is None:
        # fallback if scoring failed
        if not summary:
            return f'<div class="player-card empty"><div class="player-header"><span class="player-name">{player}</span></div><div class="no-cons">No consumables detected</div></div>'

    grade_col = _grade_color(ps.grade) if ps else "#888"
    overall   = f"{ps.overall_score:.0f}" if ps else "—"
    grade     = ps.grade if ps else "?"
    cls_role  = f"{ps.cls} · {ps.role.replace('_',' ').title()}" if ps else ""

    slot_rows = ""
    if ps:
        if ps.flask.used:
            slot_rows += _render_slot_row("Flask", "⚗️", ps.flask)
        else:
            slot_rows += _render_slot_row("Battle Elixir",   "⚔️", ps.battle_elixir)
            slot_rows += _render_slot_row("Guardian Elixir", "🛡️", ps.guardian_elixir)
        slot_rows += _render_slot_row("Potion",      "🧪", ps.potion)
        slot_rows += _render_slot_row("Food",        "🍖", ps.food)
        if ps.scroll.used or ps.scroll.score > 0:
            slot_rows += _render_slot_row("Scroll",  "📜", ps.scroll)
        if ps.weapon_buff.used or ps.weapon_buff.score > 0:
            slot_rows += _render_slot_row("Weapon",  "🗡️", ps.weapon_buff)

    return f'''
    <div class="player-card">
      <div class="player-header">
        <span class="player-name">{player}</span>
        <span class="player-class">{cls_role}</span>
        <span class="overall-badge" style="color:{grade_col};border-color:{grade_col}">{overall}<span class="grade-letter">{grade}</span></span>
      </div>
      <div class="slot-list">{slot_rows}</div>
    </div>'''

def _duration_str(start, end):
    try:
        fmt = "%m/%d/%Y %H:%M:%S.%f"
        d = (datetime.strptime(end, fmt) - datetime.strptime(start, fmt)).total_seconds()
        return f"{int(d//60)}m {int(d%60)}s"
    except:
        return ""

def _render_encounter(enc: EncounterData, index: int) -> str:
    result_cls = "kill" if enc.success else "wipe"
    result_label = "★ KILL" if enc.success else "✗ WIPE"
    summary_all = enc.get_summary()
    player_spells = getattr(enc, "player_spells", {})

    try:
        fmt = "%m/%d/%Y %H:%M:%S.%f"
        duration_secs = (datetime.strptime(enc.end_time, fmt) - datetime.strptime(enc.start_time, fmt)).total_seconds()
    except:
        duration_secs = 300.0

    scores = score_encounter(enc, player_spells, duration_secs)
    dur_str = _duration_str(enc.start_time, enc.end_time)

    # Sort: highest score first
    sorted_players = sorted(
        enc.roster or list(summary_all.keys()),
        key=lambda p: -(scores[p].overall_score if p in scores else 0)
    )

    cards = "".join(_render_player_card(p, summary_all.get(p,{}), scores.get(p)) for p in sorted_players)

    # Raid average score
    valid_scores = [s.overall_score for s in scores.values()]
    avg = sum(valid_scores)/len(valid_scores) if valid_scores else 0

    return f'''
  <section class="encounter" id="enc-{index}">
    <div class="enc-header {result_cls}">
      <div class="enc-title-block">
        <span class="enc-index">#{index}</span>
        <span class="enc-name">{enc.encounter_name}</span>
        <span class="enc-difficulty">{enc.difficulty}</span>
      </div>
      <div class="enc-meta">
        <span class="enc-result {result_cls}">{result_label}</span>
        <span class="enc-dur">⏱ {dur_str}</span>
        <span class="enc-avg">Raid avg <strong>{avg:.0f}</strong></span>
      </div>
    </div>
    <div class="player-grid">{cards}</div>
  </section>'''

def generate_html_report(encounters, output_path, log_filename=""):
    output_path = Path(output_path)
    kills = sum(1 for e in encounters if e.success)
    wipes = len(encounters) - kills

    nav = "".join(
        f'<a href="#enc-{i+1}" class="nav-item {"kill" if e.success else "wipe"}">'
        f'#{i+1} {e.encounter_name}</a>'
        for i, e in enumerate(encounters)
    )
    sections = "".join(_render_encounter(e, i+1) for i, e in enumerate(encounters))

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Consumable Report — {log_filename}</title>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=Barlow:wght@300;400;500;600&family=Barlow+Condensed:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{{
  --bg:#0d0f14;--bg2:#13161e;--bg3:#1a1e2a;--bg4:#1e2333;
  --border:#252a38;--border-hi:#3a4260;
  --text:#c8cedf;--text-dim:#5a6282;--text-bright:#e8ecf5;
  --gold:#c8a94a;--gold-glow:rgba(200,169,74,.25);
  --kill:#4caf82;--kill-dim:#1a3d2c;
  --wipe:#c05252;--wipe-dim:#3d1c1c;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:'Barlow',sans-serif;font-size:14px;line-height:1.5}}
body::before{{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 80% 50% at 15% 0%,rgba(155,111,212,.06),transparent 55%),radial-gradient(ellipse 60% 40% at 85% 100%,rgba(76,175,130,.05),transparent 55%);pointer-events:none;z-index:0}}
.page{{position:relative;z-index:1;max-width:1400px;margin:0 auto;padding:0 24px 80px}}

/* Header */
.site-header{{padding:44px 0 28px;border-bottom:1px solid var(--border);margin-bottom:28px}}
.site-header h1{{font-family:'Cinzel',serif;font-size:26px;color:var(--gold);letter-spacing:.04em;text-shadow:0 0 40px var(--gold-glow);margin-bottom:4px}}
.subtitle{{font-size:12px;color:var(--text-dim);letter-spacing:.08em;text-transform:uppercase}}
.hstats{{display:flex;gap:28px;margin-top:18px}}
.hstat{{display:flex;flex-direction:column;gap:2px}}
.hstat-v{{font-family:'Cinzel',serif;font-size:20px;color:var(--text-bright)}}
.hstat-v.kill{{color:var(--kill)}}.hstat-v.wipe{{color:var(--wipe)}}
.hstat-l{{font-size:11px;color:var(--text-dim);text-transform:uppercase;letter-spacing:.1em}}

/* Nav */
.enc-nav{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:36px}}
.nav-item{{font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;padding:5px 14px;border-radius:4px;border:1px solid var(--border);background:var(--bg2);color:var(--text-dim);text-decoration:none;transition:all .15s}}
.nav-item:hover{{border-color:var(--border-hi);color:var(--text-bright)}}
.nav-item.kill{{border-color:var(--kill-dim);color:var(--kill)}}.nav-item.kill:hover{{background:var(--kill-dim)}}
.nav-item.wipe{{border-color:var(--wipe-dim);color:var(--wipe)}}.nav-item.wipe:hover{{background:var(--wipe-dim)}}

/* Encounter */
.encounter{{margin-bottom:44px;border:1px solid var(--border);border-radius:8px;overflow:hidden}}
.enc-header{{display:flex;align-items:center;justify-content:space-between;padding:16px 22px;background:var(--bg3);border-bottom:1px solid var(--border);flex-wrap:wrap;gap:10px}}
.enc-header.kill{{border-left:3px solid var(--kill)}}.enc-header.wipe{{border-left:3px solid var(--wipe)}}
.enc-title-block{{display:flex;align-items:baseline;gap:12px}}
.enc-index{{font-family:'Cinzel',serif;font-size:12px;color:var(--text-dim)}}
.enc-name{{font-family:'Cinzel',serif;font-size:19px;color:var(--text-bright);letter-spacing:.02em}}
.enc-difficulty{{font-size:11px;color:var(--text-dim);font-family:'Barlow Condensed',sans-serif;letter-spacing:.08em;text-transform:uppercase;border:1px solid var(--border);padding:2px 8px;border-radius:3px}}
.enc-meta{{display:flex;align-items:center;gap:16px}}
.enc-result{{font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:600;letter-spacing:.15em;text-transform:uppercase;padding:4px 12px;border-radius:3px}}
.enc-result.kill{{background:var(--kill-dim);color:var(--kill)}}.enc-result.wipe{{background:var(--wipe-dim);color:var(--wipe)}}
.enc-dur,.enc-avg{{font-size:12px;color:var(--text-dim)}}
.enc-avg strong{{color:var(--text-bright)}}

/* Player grid */
.player-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:1px;background:var(--border)}}
.player-card{{background:var(--bg);padding:14px 18px;transition:background .15s}}
.player-card:hover{{background:var(--bg2)}}
.player-card.empty{{opacity:.5}}

/* Player header */
.player-header{{display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap}}
.player-name{{font-family:'Barlow Condensed',sans-serif;font-size:15px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--gold);flex:1;min-width:0}}
.player-class{{font-size:11px;color:var(--text-dim);white-space:nowrap}}
.overall-badge{{font-family:'Barlow Condensed',sans-serif;font-size:14px;font-weight:600;padding:2px 10px;border-radius:4px;border:1px solid;display:flex;align-items:center;gap:4px;white-space:nowrap}}
.grade-letter{{font-family:'Cinzel',serif;font-size:13px;font-weight:700}}
.no-cons{{font-size:12px;color:var(--text-dim);font-style:italic;padding:4px 0}}

/* Slot rows */
.slot-row{{display:flex;align-items:center;gap:8px;padding:4px 0;border-bottom:1px solid var(--border);min-height:32px}}
.slot-row:last-child{{border-bottom:none}}
.slot-row.empty{{opacity:.38}}
.slot-icon{{font-size:13px;width:18px;text-align:center;flex-shrink:0}}
.slot-label{{font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--text-dim);width:100px;flex-shrink:0}}
.slot-none{{font-size:12px;color:var(--text-dim);font-style:italic}}
.slot-content{{flex:1;min-width:0;display:flex;flex-direction:column;gap:3px}}
.slot-pills{{display:flex;flex-wrap:wrap;gap:3px}}
.slot-note{{font-size:10px;color:#c09050;letter-spacing:.02em}}
.slot-score{{font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:600;color:var(--text-dim);width:34px;text-align:right;flex-shrink:0}}

/* Score bar */
.score-bar{{height:3px;background:var(--bg4);border-radius:2px;overflow:hidden;margin-top:1px}}
.score-fill{{height:100%;border-radius:2px;transition:width .3s}}

/* Item pills */
.item-pill{{font-size:10px;font-weight:500;padding:2px 7px;border-radius:3px;border:1px solid transparent;white-space:nowrap}}
.flask{{background:rgba(155,111,212,.12);border-color:rgba(155,111,212,.3);color:#b48de0}}
.elixir_battle{{background:rgba(212,131,74,.12);border-color:rgba(212,131,74,.3);color:#e0a06a}}
.elixir_guardian{{background:rgba(74,155,212,.12);border-color:rgba(74,155,212,.3);color:#6ab4e0}}
.battle_elixir{{background:rgba(212,131,74,.12);border-color:rgba(212,131,74,.3);color:#e0a06a}}
.guardian_elixir{{background:rgba(74,155,212,.12);border-color:rgba(74,155,212,.3);color:#6ab4e0}}
.potion{{background:rgba(212,74,130,.12);border-color:rgba(212,74,130,.3);color:#e06898}}
.food{{background:rgba(130,196,74,.12);border-color:rgba(130,196,74,.3);color:#a0d468}}
.scroll{{background:rgba(196,164,74,.12);border-color:rgba(196,164,74,.3);color:#d4be6a}}
.weapon{{background:rgba(212,98,74,.12);border-color:rgba(212,98,74,.3);color:#e0886a}}
.weapon_buff{{background:rgba(212,98,74,.12);border-color:rgba(212,98,74,.3);color:#e0886a}}

/* Footer */
.site-footer{{margin-top:56px;padding-top:20px;border-top:1px solid var(--border);font-size:11px;color:var(--text-dim);text-align:center;letter-spacing:.05em}}

@media(max-width:640px){{
  .player-grid{{grid-template-columns:1fr}}
  .slot-label{{width:80px}}
}}
</style>
</head>
<body>
<div class="page">
  <header class="site-header">
    <h1>TBC Anniversary — Consumable Report</h1>
    <div class="subtitle">{f"Source: {log_filename} &nbsp;·&nbsp;" if log_filename else ""}{len(encounters)} encounter{"s" if len(encounters)!=1 else ""}</div>
    <div class="hstats">
      <div class="hstat"><span class="hstat-v">{len(encounters)}</span><span class="hstat-l">Encounters</span></div>
      <div class="hstat"><span class="hstat-v kill">{kills}</span><span class="hstat-l">Kills</span></div>
      <div class="hstat"><span class="hstat-v wipe">{wipes}</span><span class="hstat-l">Wipes</span></div>
    </div>
  </header>
  <nav class="enc-nav">{nav}</nav>
  {sections}
  <footer class="site-footer">TBC Consumable Tracker &nbsp;·&nbsp; WoW Anniversary TBC</footer>
</div>
</body>
</html>'''

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] HTML report written to: {output_path}")
