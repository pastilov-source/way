"""Збирає версію 4 (score-graph.html) з score-graph.src.html.

- граф рахується з даних кроків нижче і токена --way-graph-day з concept/tokens.css;
- іконки Solar Linear з icons/ ідуть один раз у спрайт <symbol>, на місці — <use>.

Запуск з кореня репозиторію: python3 concept/directions/_build_v4.py
"""
import re
from html import escape
from pathlib import Path

HERE = Path(__file__).parent
TOKENS = (HERE.parent / "tokens.css").read_text()


def token_px(name):
    m = re.search(rf"--{name}:\s*([\d.]+)px", TOKENS)
    if not m:
        raise SystemExit(f"токена --{name} немає в tokens.css")
    return float(m.group(1))


DAY = token_px("way-graph-day")  # один день по вертикалі, у px

# Дорога «Портфоліо». day — скільки днів від старту до кроку, took — скільки днів зайняв крок.
START = {"x": 300, "label": "Старт", "sub": "Кейсів немає, є лише старий Behance"}
STEPS = [
    {"id": "s1", "day": 2, "took": 2, "x": 288, "kind": "done", "label": ["Обрати три проєкти для кейсів"]},
    {"id": "s2", "day": 6, "took": 4, "x": 318, "kind": "done", "label": ["Зібрати матеріали першого кейсу"]},
    {"id": "s3", "day": 12, "took": 6, "x": 294, "kind": "done", "label": ["Перший кейс на сайті"], "label_below": True},
    {"id": "s4", "day": 13, "took": 1, "x": 386, "kind": "retro", "from": "s3", "label": ["Структура другого кейсу"], "sub": "записано заднім числом, сьогодні"},
    {"id": "s5", "day": 14, "took": 1, "x": 306, "kind": "go", "from": "s3", "label": ["Дописати вступ до кейсу", "про застосунок для бігу"], "sub": "у роботі · почато щойно", "now": True},
]
SATELLITES = [
    {"x": 168, "day": 2.6, "label": ["Старий Behance"], "links": ["start", "s1"]},
    {"x": 176, "day": 9.5, "label": ["Що роботодавці", "дивляться в кейсах"], "links": ["s2", "s3"]},
]
STAGES = [  # межа етапу — день, з якого він починається
    {"name": "Відбір проєктів · пройдено", "from": 0},
    {"name": "Кейси · тут зараз", "from": 6, "now": True},
    {"name": "Сайт · попереду", "ahead": True},
]
FINISH = {"x": 306, "y": 150, "label": "Фініш", "sub": ["Три кейси на сайті, з якими", "не соромно йти на співбесіду"]}

Y0 = 616          # y старту в координатах viewBox
WIDTH = 664
KIND_WORD = {"done": "зроблено", "retro": "записано заднім числом", "go": "у роботі"}


def y_of(day):
    return round(Y0 - day * DAY, 1)


def radius(took):
    return round(3.5 + took * 0.6, 1)


def curve(x1, y1, x2, y2):
    mid = round((y1 + y2) / 2, 1)
    return f"M{x1} {y1} C {x1} {mid}, {x2} {mid}, {x2} {y2}"


def days_word(n):
    return f"{n} дн"


def graph():
    pos = {"start": (START["x"], Y0)}
    for s in STEPS:
        pos[s["id"]] = (s["x"], y_of(s["day"]))
    top_now = min(pos[s["id"]][1] for s in STEPS) - 60
    now_from = y_of(next(st["from"] for st in STAGES if st.get("now")))
    out = []
    a = out.append
    a(f'<svg viewBox="0 {FINISH["y"] - 46} {WIDTH} {Y0 + 50 - (FINISH["y"] - 46)}" role="group" aria-labelledby="sg-graph-t">')
    a('<title id="sg-graph-t">Дорога «Портфоліо»: від старту внизу до фінішу вгорі</title>')
    # stage band and bar lines
    a(f'<rect class="band" x="0" y="{top_now}" width="{WIDTH}" height="{round(now_from - top_now, 1)}"/>')
    a(f'<line class="bar-line" x1="0" y1="{now_from}" x2="{WIDTH}" y2="{now_from}"/>')
    a(f'<line class="bar-line" x1="0" y1="{Y0}" x2="{WIDTH}" y2="{Y0}"/>')
    for st in STAGES:
        if st.get("now"):
            a(f'<text class="apx apx--now" x="16" y="{top_now + 20}">{escape(st["name"])}</text>')
        elif st.get("ahead"):
            a(f'<text class="apx" x="16" y="{round((FINISH["y"] + top_now) / 2 + 30)}">{escape(st["name"])}</text>')
        else:
            a(f'<text class="apx" x="16" y="{Y0 - 8}">{escape(st["name"])}</text>')
    # edges
    for sat in SATELLITES:
        sx, sy = sat["x"], y_of(sat["day"])
        for l in sat["links"]:
            x, y = pos[l]
            a(f'<path class="e e--sat" d="{curve(x, y, sx, sy)}"/>')
    prev = "start"
    for s in STEPS:
        src = s.get("from", prev)
        x1, y1 = pos[src]
        x2, y2 = pos[s["id"]]
        cls = {"done": "e--done", "retro": "e--side", "go": "e--go"}[s["kind"]]
        a(f'<path class="e {cls}" d="{curve(x1, y1, x2, y2)}"/>')
        if s["kind"] == "done":
            prev = s["id"]
    # satellites
    for sat in SATELLITES:
        sx, sy = sat["x"], y_of(sat["day"])
        name = " ".join(sat["label"])
        a(f'<g class="n n--sat" tabindex="0" aria-label="Ресурс: {escape(name)}">')
        a(f'<circle class="ring" cx="{sx}" cy="{sy}" r="8"/><circle class="core" cx="{sx}" cy="{sy}" r="3.5"/>')
        for i, line in enumerate(sat["label"]):
            a(f'<text class="satlbl" x="{sx - 12}" y="{sy + 4 - (len(sat["label"]) - 1) * 7.5 + i * 15}" text-anchor="end">{escape(line)}</text>')
        a("</g>")
    # start
    sx, sy = pos["start"]
    a(f'<g class="n n--start" tabindex="0" aria-label="Старт: {escape(START["sub"])}">')
    a(f'<circle class="ring" cx="{sx}" cy="{sy}" r="11"/><circle class="core" cx="{sx}" cy="{sy}" r="6"/>')
    a(f'<text class="lbl" x="{sx + 18}" y="{sy + 24}">{START["label"]}</text>')
    a(f'<text class="sub" x="{sx + 18}" y="{sy + 40}">{escape(START["sub"])}</text>')
    a("</g>")
    # steps
    for s in STEPS:
        x, y = pos[s["id"]]
        r = radius(s["took"])
        name = " ".join(s["label"])
        aria = f'Крок: {name}, {KIND_WORD[s["kind"]]}, {days_word(s["took"])}'
        a(f'<g class="n n--{s["kind"]}" tabindex="0" aria-label="{escape(aria)}">')
        if s.get("now"):
            a(f'<circle class="halo" cx="{x}" cy="{y}" r="12"/>')
        a(f'<circle class="ring" cx="{x}" cy="{y}" r="{r + 5}"/><circle class="core" cx="{x}" cy="{y}" r="{r}"/>')
        if s["kind"] != "retro":
            a(f'<text class="days" x="{x - r - 12}" y="{y + 4}" text-anchor="end">{days_word(s["took"])}</text>')
        tx = x + r + 12
        cls = "lbl lbl--now" if s.get("now") else "lbl"
        if s.get("label_below"):
            ty = y + 28
        elif len(s["label"]) > 1:
            ty = y - 26
        else:
            ty = y + 4
        for i, line in enumerate(s["label"]):
            a(f'<text class="{cls}" x="{tx}" y="{ty + i * 18}">{escape(line)}</text>')
        if s.get("sub"):
            a(f'<text class="sub" x="{tx}" y="{ty + len(s["label"]) * 18 - 1}">{escape(s["sub"])}</text>')
        a("</g>")
    # finish: visible, no road drawn to it (O15)
    fx, fy = FINISH["x"], FINISH["y"]
    a(f'<g class="n n--finish" tabindex="0" aria-label="Фініш: {escape(" ".join(FINISH["sub"]))}">')
    a(f'<circle class="ring" cx="{fx}" cy="{fy}" r="14"/><circle class="core" cx="{fx}" cy="{fy}" r="9"/><circle class="in" cx="{fx}" cy="{fy}" r="3"/>')
    a(f'<text class="lbl lbl--now" x="{fx + 20}" y="{fy - 4}">{FINISH["label"]}</text>')
    for i, line in enumerate(FINISH["sub"]):
        a(f'<text class="sub" x="{fx + 20}" y="{fy + 13 + i * 15}">{escape(line)}</text>')
    a("</g>")
    a("</svg>")
    return "\n".join("        " + line for line in out)


def icon_symbol(name):
    svg = (HERE / "icons" / f"{name}.svg").read_text()
    vb = re.search(r'viewBox="([^"]+)"', svg).group(1)
    inner = re.sub(r"^<svg[^>]*>|</svg>\s*$", "", svg.strip())
    return f'<symbol id="sg-i-{name}" viewBox="{vb}">{inner}</symbol>'


src = (HERE / "score-graph.src.html").read_text()
used = sorted(set(re.findall(r"\{\{i:([a-z0-9-]+)\}\}", src)))
sprite = ('<svg class="sr" aria-hidden="true" focusable="false">'
          + "".join(icon_symbol(n) for n in used) + "</svg>")
out = re.sub(r"\{\{i:([a-z0-9-]+)\}\}",
             lambda m: f'<svg class="ic" aria-hidden="true" focusable="false"><use href="#sg-i-{m.group(1)}"/></svg>', src)
out = out.replace("{{SPRITE}}", sprite).replace("{{GRAPH}}", graph())
assert "{{" not in out
(HERE / "score-graph.html").write_text(out)
print("score-graph.html", len(out), "· день =", DAY, "px · іконок:", len(used))
