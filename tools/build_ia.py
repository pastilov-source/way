#!/usr/bin/env python3
"""Збирає wireframes/ia.html із wireframes/sitemap.md і wireframes/flows.md.

Запуск із кореня репозиторію:  python3 tools/build_ia.py
Стилі береться з research/personas.html, щоб сторінки сайту виглядали однаково.
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
SITEMAP = (ROOT / "wireframes/sitemap.md").read_text(encoding="utf-8")
FLOWS = (ROOT / "wireframes/flows.md").read_text(encoding="utf-8")
PERSONAS = (ROOT / "research/personas.html").read_text(encoding="utf-8")
BASE_CSS = re.search(r"<style>\n(.*?)</style>", PERSONAS, flags=re.S).group(1)
BASE_CSS = BASE_CSS.split("/* ================= personas.html")[0]

# ---------------------------------------------------------------- inline markdown
def inline(text: str) -> str:
    slots = []

    def keep(s):
        slots.append(s)
        return f"\x00{len(slots) - 1}\x00"

    text = re.sub(r"`([^`]+)`", lambda m: keep(f'<code class="mono">{html.escape(m.group(1))}</code>'), text)

    def link(m):
        label, url = m.group(1), m.group(2)
        parts = re.split(r"(\x00\d+\x00)", label)
        inner = "".join(slots[int(x[1:-1])] if re.fullmatch(r"\x00\d+\x00", x) else html.escape(x, quote=False) for x in parts)
        if url.startswith("http"):
            return keep(f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{inner}</a>')
        return keep(f'<span class="ref">{inner}</span>')

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", text)
    text = text.replace("[?]", '<span class="chip unk" title="припущення">?</span>')
    text = text.replace("<b>Н</b>", '<span class="chip ours" title="наша оцінка">Н</span>')
    text = re.sub(r"\x00(\d+)\x00", lambda m: slots[int(m.group(1))], text)
    return text


# ---------------------------------------------------------------- block markdown
def table(lines, cls="", row_class=None, cell_class=None):
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines]
    head, align, body = rows[0], rows[1], rows[2:]
    centers = [a.startswith(":") and a.endswith(":") for a in align]
    out = [f'<div class="tw"><table class="{cls}"><thead><tr>']
    for i, h in enumerate(head):
        out.append(f'<th{" class=c" if centers[i] else ""}>{inline(h)}</th>')
    out.append("</tr></thead><tbody>")
    for r, row in enumerate(body):
        rc = row_class(r, row) if row_class else ""
        tr_attr = ' class="%s"' % rc if rc else ""
        out.append(f"<tr{tr_attr}>")
        for i, c in enumerate(row):
            cc = cell_class(r, i, row) if cell_class else ""
            classes = " ".join(x for x in ["c" if centers[i] else "", cc] if x)
            val = '<span class="tick">✓</span>' if c == "✓" else inline(c)
            td_attr = ' class="%s"' % classes if classes else ""
            out.append(f"<td{td_attr}>{val}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def blocks(md: str) -> str:
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s or s == "---":
            i += 1
            continue
        if s.startswith("```"):
            j = i + 1
            while not lines[j].strip().startswith("```"):
                j += 1
            code = "\n".join(lines[i + 1:j])
            out.append(f'<pre class="ascii">{html.escape(code)}</pre>')
            i = j + 1
            continue
        if s.startswith("|"):
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            out.append(table(lines[i:j]))
            i = j
            continue
        if s.startswith("#### "):
            out.append(f"<h4>{inline(s[5:])}</h4>")
            i += 1
            continue
        if s.startswith("### "):
            out.append(f"<h3>{inline(s[4:])}</h3>")
            i += 1
            continue
        if s.startswith(">"):
            j = i
            buf = []
            while j < len(lines) and lines[j].strip().startswith(">"):
                buf.append(lines[j].strip()[1:].strip())
                j += 1
            out.append(f'<blockquote class="job">{inline(" ".join(buf))}</blockquote>')
            i = j
            continue
        if re.match(r"^(\s*)(-|\d+\.)\s", ln):
            j = i
            items = []
            while j < len(lines) and re.match(r"^(\s*)(-|\d+\.)\s", lines[j]):
                m = re.match(r"^(\s*)(-|\d+\.)\s(.*)$", lines[j])
                items.append((len(m.group(1)), m.group(2) != "-", m.group(3)))
                j += 1
            out.append(render_list(items))
            i = j
            continue
        j = i
        buf = []
        while j < len(lines) and lines[j].strip() and not re.match(r"^(\s*)(-|\d+\.)\s|^\s*[|#>`]", lines[j]):
            buf.append(lines[j].strip())
            j += 1
        out.append(f"<p>{inline(' '.join(buf))}</p>")
        i = j
    return "\n".join(out)


def render_list(items):
    out, stack = [], []
    for indent, ordered, text in items:
        tag = "ol" if ordered else "ul"
        while stack and stack[-1][0] > indent:
            out.append(f"</li></{stack.pop()[1]}>")
        if not stack or stack[-1][0] < indent:
            out.append(f"<{tag}>")
            stack.append((indent, tag))
        else:
            out.append("</li>")
        out.append(f"<li>{inline(text)}")
    while stack:
        out.append(f"</li></{stack.pop()[1]}>")
    return "".join(out)


# ---------------------------------------------------------------- sitemap parts
def section(md, title):
    m = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", md, flags=re.S | re.M)
    return m.group(1)


def sub(md, title):
    m = re.search(rf"^### {re.escape(title)}\n(.*?)(?=^### |\Z)", md, flags=re.S | re.M)
    return m.group(1)


def first_table(md):
    lines = md.split("\n")
    i = next(k for k, l in enumerate(lines) if l.strip().startswith("|"))
    j = i
    while j < len(lines) and lines[j].strip().startswith("|"):
        j += 1
    return lines[i:j], "\n".join(lines[:i]), "\n".join(lines[j:])


def chips(jobs: str) -> str:
    if not jobs:
        return ""
    out = []
    for tok in [t.strip() for t in jobs.split(",") if t.strip()]:
        if tok == "Н":
            out.append('<span class="chip ours" title="наша оцінка">Н</span>')
        elif tok.startswith("→"):
            out.append(f'<span class="chip feed" title="подає дані; job закривається на іншому екрані">{html.escape(tok)}</span>')
        else:
            out.append(f'<span class="chip q">{html.escape(tok)}</span>')
    return " ".join(out)


def tree_html(md):
    code = re.search(r"### Дерево\n\n```\n(.*?)```", md, flags=re.S).group(1)
    groups = []
    for ln in code.split("\n"):
        m = re.match(r"^([│├└─\s]*)(.*)$", ln)
        prefix, content = m.group(1), m.group(2).strip()
        if not content or content == "WAY":
            continue
        depth = len(prefix) // 3
        mm = re.match(r"^(?P<name>.+?)\s{2,}\((?P<jobs>[^)]*)\)\s*(?P<note>.*)$", content)
        name, jobs, note = (mm.group("name"), mm.group("jobs"), mm.group("note")) if mm else (content, "", "")
        if depth == 1:
            title, _, tail = name.partition(" · ")
            groups.append({"title": title, "tail": tail, "screens": []})
        elif depth == 2:
            groups[-1]["screens"].append({"name": name, "jobs": jobs, "note": note, "secs": []})
        else:
            groups[-1]["screens"][-1]["secs"].append((name, jobs, note))
    out = ['<div class="tree">']
    for g in groups:
        out.append(f'<div class="tg"><div class="tg-h"><span class="tg-t">{html.escape(g["title"])}</span>'
                   f'<span class="tg-s">{inline(g["tail"])}</span></div><div class="tg-screens">')
        for s in g["screens"]:
            out.append(f'<article class="scr"><div class="scr-h"><h4>{html.escape(s["name"])}</h4>{chips(s["jobs"])}</div>'
                       f'<div class="scr-note">{inline(s["note"])}</div><ul class="secs">')
            for n, j, note in s["secs"]:
                out.append(f'<li><span class="sec-n">{inline(n)}</span> {chips(j)}'
                           f'{f"<span class=sec-note>{inline(note)}</span>" if note else ""}</li>')
            out.append("</ul></article>")
        out.append("</div></div>")
    out.append("</div>")
    return "".join(out)


def matrix(md_table_lines, weak_rows=True):
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in md_table_lines]
    body = rows[2:]
    data = [r for r in body if not r[0].startswith("**Jobs")]
    ncols = len(rows[0]) - 2
    col_tot = [sum(1 for r in data if r[1 + k] == "✓") for k in range(ncols)]
    row_tot = [sum(1 for c in r[1:1 + ncols] if c == "✓") for r in data]

    def row_class(ri, row):
        if row[0].startswith("**Jobs"):
            return "tot"
        n = row_tot[ri]
        return "orphan" if n == 0 else ("thin" if n == 1 and weak_rows else "")

    def cell_class(ri, ci, row):
        if 1 <= ci <= ncols:
            t = col_tot[ci - 1]
            if t == 0:
                return "orphan-col"
            if t == 1:
                return "thin-col"
        return ""

    return table(md_table_lines, "matrix", row_class, cell_class)


# ---------------------------------------------------------------- flows
def flow_sections(md):
    parts = re.split(r"^## ", md, flags=re.M)
    flows, tail = [], ""
    for p in parts[1:]:
        title, _, body = p.partition("\n")
        if re.match(r"J\d", title):
            flows.append((title.strip(), body))
        elif title.startswith("Що видно"):
            tail = body
    return flows, tail


DARK = {
    "state": "fill:#232E27,stroke:#7E8D85,color:#E5ECE6",
    "good": "fill:#16271E,stroke:#77C79A,color:#A7E3C0",
    "dead": "fill:#2B1916,stroke:#E08B7C,color:#F2B7AB",
    "exit": "fill:#1A211D,stroke:#7E8D85,color:#B2C0B7,stroke-dasharray:4 3",
}


def flow_html(idx, title, body):
    m = re.search(r"```mermaid\n(.*?)```", body, flags=re.S)
    code = m.group(1)
    code = re.sub(r"classDef (\w+) [^\n]+", lambda mm: f"classDef {mm.group(1)} {DARK.get(mm.group(1), '')}", code)
    before, after = body[:m.start()], body[m.end():]
    return (f'<article class="flow" id="flow-{idx}"><div class="flow-h"><span class="flow-n">{idx:02d}</span>'
            f'<h3>{inline(title)}</h3></div>{blocks(before)}'
            f'<div class="diagram"><pre class="mermaid">{html.escape(code, quote=False)}</pre></div>'
            f'<div class="flow-notes">{blocks(after)}</div></article>')


# ---------------------------------------------------------------- assemble
ent = section(SITEMAP, "Сутності")
ent_table, _, _ = first_table(ent)
scr = section(SITEMAP, "Екрани")
nav = section(SITEMAP, "Навігація")
trace = section(SITEMAP, "Трасування")
dec = section(SITEMAP, "Рішення виконавця")
opn = section(SITEMAP, "Відкрите")
flows, flows_tail = flow_sections(FLOWS)

cur_lines = [l for l in sub(trace, "Матриця — поточна").split("\n") if l.strip().startswith("|")]
old_lines = [l for l in sub(trace, "Матриця до рішень").split("\n") if l.strip().startswith("|")]
dead_ends = len(re.findall(r'\(\["Тупик', FLOWS))

toc = [("korotko", "Коротко"), ("sutnosti", "Сутності"), ("tree", "Дерево екранів"), ("nav", "Навігація"),
       ("flows", "User flows"), ("trace", "Трасування"), ("rishennia", "Рішення виконавця"), ("open", "Відкрите")]

flow_toc = "".join(f'<li><a class="fl" href="#flow-{i + 1}">{inline(t)}</a></li>' for i, (t, _) in enumerate(flows))

CSS_IA = """
/* ================= ia.html: додано до стилів personas.html ================= */
main{min-width:0}
code.mono{font-size:.86em;color:var(--ink-2);background:var(--surface-2);border:1px solid var(--line);border-radius:4px;padding:1px 5px}
.chip.unk{background:var(--signal-soft);color:var(--signal);border:1px solid rgba(224,164,92,.38)}
.chip.feed{background:transparent;color:var(--muted);border:1px dashed var(--line-2)}
.ref{color:var(--ink-2)}
ul,ol{margin:0 0 15px;padding-left:22px;max-width:80ch}
li{margin-bottom:6px}
li>ul,li>ol{margin:6px 0 0}
th.c,td.c{text-align:center}
blockquote.job{margin:0 0 18px;padding:14px 20px;border-left:3px solid var(--accent-dim);background:var(--surface);border-radius:0 var(--radius) var(--radius) 0;color:var(--ink-2);font-style:italic;max-width:80ch}
pre.ascii{background:var(--surface);border:1px solid var(--line-2);border-radius:var(--radius);padding:18px 20px;overflow-x:auto;font-family:"JetBrains Mono",monospace;font-size:12.5px;line-height:1.55;color:var(--ink-2);margin:0 0 16px}
details{margin:14px 0;border:1px solid var(--line-2);border-radius:var(--radius);background:var(--surface)}
details>summary{cursor:pointer;padding:13px 18px;font-weight:600;color:var(--ink);list-style:none}
details>summary::-webkit-details-marker{display:none}
details>summary::before{content:"▸";color:var(--accent);margin-right:10px;display:inline-block;transition:transform .15s}
details[open]>summary::before{transform:rotate(90deg)}
details>.in{padding:4px 18px 8px}
details .tw{background:var(--surface-2)}

/* stat tiles */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:6px 0 26px}
.stat{background:var(--surface);border:1px solid var(--line-2);border-radius:var(--radius);padding:16px 18px}
.stat b{display:block;font-family:"Unbounded",sans-serif;font-size:26px;letter-spacing:-.03em;color:var(--accent);line-height:1.1}
.stat span{font-size:13px;color:var(--ink-2)}

/* tree */
.tree{display:grid;gap:16px;margin:10px 0 18px}
.tg{border:1px solid var(--line-2);border-radius:var(--radius);background:linear-gradient(180deg,var(--surface),var(--ground));padding:16px}
.tg-h{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:2px 4px 14px}
.tg-t{font-family:"Unbounded",sans-serif;font-size:13px;font-weight:700;letter-spacing:.12em;color:var(--accent)}
.tg-s{font-size:14px;color:var(--muted)}
.tg-screens{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}
.scr{background:var(--surface-2);border:1px solid var(--line-2);border-radius:10px;padding:16px 18px}
.scr-h{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:4px}
.scr-h h4{margin:0 8px 0 0;font-size:17px}
.scr-note{font-size:12.5px;color:var(--muted);font-family:"JetBrains Mono",monospace;margin-bottom:10px}
.secs{list-style:none;margin:0;padding:0;border-top:1px solid var(--line)}
.secs li{padding:8px 0;border-bottom:1px solid var(--line);margin:0;font-size:14px;line-height:1.45}
.secs li:last-child{border-bottom:0}
.sec-n{color:var(--ink)}
.sec-note{display:block;color:var(--muted);font-size:12.5px;margin-top:2px}

/* flows */
.flow-toc{list-style:none;padding:0;margin:0 0 20px;display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:8px;max-width:none}
.flow-toc a.fl{display:block;background:var(--surface);border:1px solid var(--line-2);border-radius:10px;padding:10px 14px;font-size:14px;color:var(--ink-2)}
.flow-toc a.fl:hover{border-color:var(--accent-dim);color:var(--ink)}
.flow{border-top:1px solid var(--line-2);padding-top:34px;margin-top:40px;scroll-margin-top:20px}
.flow-h{display:flex;align-items:baseline;gap:14px;margin-bottom:12px}
.flow-h h3{margin:0}
.flow-n{font-family:"Unbounded",sans-serif;font-size:12px;color:var(--accent);letter-spacing:.06em}
.diagram{background:var(--surface);border:1px solid var(--line-2);border-radius:var(--radius);padding:22px 16px;margin:6px 0 18px;overflow-x:auto;text-align:center}
.diagram pre.mermaid{margin:0;font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--muted);text-align:left;white-space:pre}
.diagram pre.mermaid[data-processed]{white-space:normal;text-align:center}
.diagram svg{max-width:100%;height:auto}
.legend{display:flex;flex-wrap:wrap;gap:10px 18px;font-size:13px;color:var(--ink-2);margin:0 0 18px}
.legend i{display:inline-block;width:14px;height:14px;border-radius:4px;vertical-align:-2px;margin-right:7px;border:1px solid}
.lg-screen{background:#1f2937;border-color:#81B29A}
.lg-state{background:#232E27;border-color:#7E8D85;border-radius:9px!important}
.lg-good{background:#16271E;border-color:#77C79A;border-radius:9px!important}
.lg-dead{background:#2B1916;border-color:#E08B7C;border-radius:9px!important}
.lg-exit{background:#1A211D;border-color:#7E8D85;border-style:dashed!important;border-radius:9px!important}
.flow-notes p,.flow-notes li{font-size:14.5px;color:var(--ink-2)}
.flow-notes b{color:var(--ink)}

/* matrix */
table.matrix{min-width:640px}
table.matrix td,table.matrix th{white-space:nowrap}
table.matrix td:first-child{white-space:normal;min-width:240px}
.tick{color:var(--accent);font-weight:700}
tr.orphan td{background:rgba(224,139,124,.10)}
tr.orphan td:first-child{box-shadow:inset 3px 0 0 var(--danger)}
tr.thin td:first-child{box-shadow:inset 3px 0 0 var(--signal)}
td.orphan-col{background:rgba(224,139,124,.10)}
td.thin-col{background:rgba(224,164,92,.07)}
tr.tot td{background:var(--surface-2);font-family:"JetBrains Mono",monospace;font-weight:600;color:var(--ink)}
.mx-legend{display:flex;flex-wrap:wrap;gap:8px 18px;font-size:13px;color:var(--ink-2);margin:4px 0 14px}
.mx-legend span::before{content:"";display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:7px;vertical-align:-1px}
.mx-legend .o::before{background:rgba(224,139,124,.35);box-shadow:inset 3px 0 0 var(--danger)}
.mx-legend .t::before{background:rgba(224,164,92,.25);box-shadow:inset 3px 0 0 var(--signal)}
"""

meta = ["чернетка", "2026-09-30", "5 екранів · 8 flows", "до main job — 1 тап", f"тупиків у flows — {dead_ends}",
        "рішення виконавця не узгоджено із замовником"]

page = f"""<!doctype html>
<html lang="uk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WAY — структура й сценарії</title>
<meta name="description" content="Інформаційна архітектура WAY: дерево екранів із jobs, навігація, вісім user flows і матриця трасування.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Unbounded:wght@500;700&family=Commissioner:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
{BASE_CSS}{CSS_IA}
</style>
</head>
<body>
<div class="shell">

<nav class="toc" aria-label="Зміст">
  <div class="toc-mark">WAY</div>
  <div class="toc-sub">СТРУКТУРА Й СЦЕНАРІЇ · 2026-09-30</div>
  <ol>
    {"".join(f'<li><a href="#{a}"><span class="n">{i + 1:02d}</span>{t}</a></li>' for i, (a, t) in enumerate(toc))}
  </ol>
</nav>

<main>
<header class="doc">
  <h1>Структура й сценарії</h1>
  <p class="lede">Інформаційна архітектура WAY: з чим людина має справу, які екрани це тримають, як між ними рухатися і як кожна потреба проходить крізь продукт — з усіма станами й тупиками.</p>
  <div class="meta">{"".join(f"<span>{html.escape(m)}</span>" for m in meta)}</div>
  <div class="rule"><b>Звідки ця сторінка.</b> Її зібрано скриптом із двох файлів у репозиторії — <code class="mono">wireframes/sitemap.md</code> і <code class="mono">wireframes/flows.md</code>. Джерело правди — вони. Позначки: <span class="chip q">J4</span> job, яку закриває екран чи секція; <span class="chip feed">→ J0</span> секція лише подає дані; <span class="chip unk">?</span> припущення; <span class="chip ours">Н</span> наша оцінка.</div>
</header>

<section id="korotko">
  <div class="sec-h"><span class="sec-n">01</span><h2>Коротко</h2></div><div class="sec-rule"></div>
  <div class="stats">
    <div class="stat"><b>5</b><span>екранів у трьох групах</span></div>
    <div class="stat"><b>3 + 1</b><span>глобальні пункти й плаваючий крок дня</span></div>
    <div class="stat"><b>1 тап</b><span>до main job — «бачити свій рух»</span></div>
    <div class="stat"><b>8</b><span>user flows, {dead_ends} тупиків</span></div>
    <div class="stat"><b>0</b><span>екранів і jobs-сиріт</span></div>
    <div class="stat"><b>21</b><span>рішення виконавця</span></div>
  </div>
  <ul>
    <li><b>Перший екран — «Сьогодні».</b> Продукт відкривають щодня, а «не загубити сьогоднішню дію» — перша в ядрі MVP.</li>
    <li><b>Main job тримається на одному екрані — «Дорога».</b> Там пройдене, позиція й фініш; це й найдорожчий рядок оцінки.</li>
    <li><b>Крок дня висить на кожному екрані</b> й живе поза вкладкою — у вікні поверх інших програм і в сповіщеннях. Це тимчасове рішення; цільове — застосунки й віджет.</li>
    <li><b>Жоден тупик не виникає через дірку в діаграмі.</b> Лишились ті, що стоять на відкритих питаннях, на межі можливого для продукту або на свідомих рішеннях.</li>
    <li><b>Усі рішення ухвалив виконавець</b> 2026-09-30; із замовником їх ще не узгоджено.</li>
  </ul>
</section>

<section id="sutnosti">
  <div class="sec-h"><span class="sec-n">02</span><h2>Сутності</h2></div><div class="sec-rule"></div>
  <p class="sub">Головні об'єкти, з якими людина має справу, щоб закрити свої jobs.</p>
  {table(ent_table)}
</section>

<section id="tree">
  <div class="sec-h"><span class="sec-n">03</span><h2>Дерево екранів</h2></div><div class="sec-rule"></div>
  <p class="sub">Біля екрана — jobs, які він закриває; вони збігаються з матрицею трасування. Стани екранів — не окремі екрани, вони в таблиці нижче.</p>
  {tree_html(scr)}
  <details><summary>Стани екранів</summary><div class="in">{blocks(sub(scr, "Стани, а не екрани"))}</div></details>
  <details><summary>Primary і secondary</summary><div class="in">{blocks(sub(scr, "Primary і secondary"))}</div></details>
</section>

<section id="nav">
  <div class="sec-h"><span class="sec-n">04</span><h2>Навігація</h2></div><div class="sec-rule"></div>
  <h3>Глобальна навігація</h3>
  {blocks(sub(nav, "Глобальна навігація"))}
  <h3>Глибина</h3>
  {blocks(sub(nav, "Глибина"))}
  <h3>Глобальне, контекстне, глибоке</h3>
  {blocks(sub(nav, "Глобальне, контекстне, глибоке"))}
  <details><summary>Схема переходів</summary><div class="in">{blocks(sub(nav, "Схема переходів"))}</div></details>
  <details><summary>Крок дня поза вкладкою: вікно, сповіщення, інструкції</summary><div class="in">{blocks(sub(nav, "Крок дня поза вкладкою"))}</div></details>
</section>

<section id="flows">
  <div class="sec-h"><span class="sec-n">05</span><h2>User flows</h2></div><div class="sec-rule"></div>
  <p class="sub">Вісім діаграм: main job, її фінал і шість related jobs. Кожна — з рішеннями, станами й обома кінцями: успіхом і тупиками.</p>
  <div class="legend">
    <span><i class="lg-screen"></i>екран або секція</span>
    <span><i class="lg-state"></i>стан екрана</span>
    <span><i class="lg-good"></i>успіх</span>
    <span><i class="lg-dead"></i>тупик</span>
    <span><i class="lg-exit"></i>вихід в інший flow</span>
    <span>ромб — рішення «так / ні»</span>
  </div>
  <ol class="flow-toc">{flow_toc}</ol>
  {"".join(flow_html(i + 1, t, b) for i, (t, b) in enumerate(flows))}
  <h3>Що видно з восьми flows</h3>
  {blocks(flows_tail)}
</section>

<section id="trace">
  <div class="sec-h"><span class="sec-n">06</span><h2>Трасування</h2></div><div class="sec-rule"></div>
  <p class="sub">Рядки — jobs, колонки — екрани. ✓ — екран справді бере участь у закритті job; прохідні екрани й екрани, де лише вводять дані, ✓ не отримують.</p>
  <div class="mx-legend"><span class="o">сирота: рядок чи колонка без жодної ✓</span><span class="t">тримається на одній ✓</span></div>
  <h3>Поточна матриця</h3>
  {matrix(cur_lines)}
  <p class="sub">Порожніх рядків і колонок немає. Жовтим — jobs, які закриває лише один екран: main job J0 і J2 тримаються тільки на «Дорозі».</p>
  <h3>До рішень 2026-09-30 — із сиротами</h3>
  {matrix(old_lines)}
  {blocks(sub(trace, "Сироти, знайдені раніше, і що з ними сталося"))}
  <h3>Що показує матриця</h3>
  {blocks(sub(trace, "Що показує матриця"))}
</section>

<section id="rishennia">
  <div class="sec-h"><span class="sec-n">07</span><h2>Рішення виконавця</h2></div><div class="sec-rule"></div>
  {blocks(dec)}
</section>

<section id="open">
  <div class="sec-h"><span class="sec-n">08</span><h2>Відкрите</h2></div><div class="sec-rule"></div>
  {blocks(opn)}
</section>

<footer>
  WAY · структура й сценарії, 2026-09-30 · джерело правди — <code class="mono">wireframes/sitemap.md</code> і <code class="mono">wireframes/flows.md</code> · критика — <code class="mono">wireframes/audit.md</code> · технічні факти — <code class="mono">research/research.md</code> §7
</footer>
</main>
</div>

<script type="module">
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
mermaid.initialize({{
  startOnLoad: false,
  theme: "dark",
  securityLevel: "strict",
  themeVariables: {{
    background: "#151C18", primaryColor: "#1F2B24", primaryTextColor: "#E5ECE6",
    primaryBorderColor: "#3E7A5B", lineColor: "#7E8D85", secondaryColor: "#1C2520",
    tertiaryColor: "#151C18", edgeLabelBackground: "#151C18",
    fontFamily: "Commissioner, Helvetica Neue, Arial, sans-serif", fontSize: "14px"
  }},
  flowchart: {{ htmlLabels: true, curve: "basis", useMaxWidth: true, nodeSpacing: 28, rankSpacing: 38 }}
}});
await mermaid.run({{ querySelector: "pre.mermaid" }});
</script>
</body>
</html>
"""
(ROOT / "wireframes/ia.html").write_text(page, encoding="utf-8")
print("ia.html:", len(page), "bytes;", len(flows), "flows;", dead_ends, "dead-ends")
