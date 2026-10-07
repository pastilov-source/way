#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Єдине джерело переліку каркасів, дерева каркасів і перемикача станів.

Запуск із кореня репозиторію:
  python3 tools/wf_tree.py            — вставити дерево й перемикач станів у кожну сторінку wireframes/
  python3 tools/wf_tree.py --list     — перелік файлів
  python3 tools/wf_tree.py --table    — таблиця «екран · файл · стан · flow» для _conventions.md, розділ 4

Дерево каркасів (ліва панель) — лише розділи й екрани. Стани екрана — зверху макета, до трьох рівнів:
основні стани й «особливі стани» → варіанти вибраного основного або перелік особливих → варіанти вибраного особливого.
Кожен рівень показує лише дітей вибраного вище.
Сторінка отримує дерево на місці <!-- WF-TREE --> або наявного <nav class="wf-tree">…</nav>,
перемикач станів — на місці <!-- WF-STATES --> або наявного <nav class="wf-states">…</nav>.
Нова сторінка чи стан додаються в SECTIONS нижче — і тоді з'являються на всіх сторінках свого екрана.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WF = ROOT / "wireframes"

PIP = "J4 «Узяти крок із собою»"
FRAME = PIP + " · за рамкою ESTIMATE §1"
GOAL = "J0 «Дійти до цілі»"

# розділ → екрани → стани: (файл, назва стану, мітка, рівень: 0 — стан, 1 — варіант стану, flow)
SECTIONS = [
    ("Сьогодні · що я роблю сьогодні", [
        ("today", "Сьогодні", [
            ("today-empty.html", "порожній", "-empty", 0, "J0"),
            ("today-error.html", "помилка", "-error", 0, "J0"),
            ("today-error-offline.html", "немає зв'язку", "-offline", 1, "J0"),
            ("today-error-save.html", "збережемо, щойно зможемо", "-save", 1, "J0"),
            ("today-loading.html", "завантаження", "-loading", 0, "J0"),
            ("today-loading-save.html", "зберігаємо", "-save", 1, "J0"),
            ("today.html", "успіх", "базова", 0, "J0"),
            ("today-nostep.html", "кроку ще немає", "-nostep", 0, "J4"),
            ("today-skip.html", "сьогодні без кроку", "-skip", 0, "J4"),
            ("today-alldone.html", "усі кроки зроблено", "-alldone", 0, "J4"),
            ("today-carry.html", "крок переходить на завтра", "-carry", 0, "J4"),
            ("today-afterpause.html", "після паузи", "-afterpause", 0, "J5"),
            ("today-weekstart.html", "тиждень почався", "-weekstart", 0, "J1"),
        ]),
        ("step", "Крок із собою", [
            ("step-empty.html", "порожній", "заглушка", 0, "— заглушка: жоден flow не дає"),
            ("step-error.html", "помилка", "-error", 0, "J0"),
            ("step-loading.html", "завантаження", "-loading", 0, "J0"),
            ("step.html", "успіх", "базова", 0, "J0"),
            ("step-stuck.html", "крок висить кілька днів", "-stuck", 0, "J4"),
            ("step-pip.html", "вікно поверх програм", "-pip", 0, PIP),
            ("step-pip-unsupported.html", "браузер не підтримує", "-unsupported", 1, PIP),
            ("step-phone.html", "на телефоні", "-phone", 0, PIP),
            ("step-phone-install.html", "застосунок не встановлено", "-install", 1, FRAME),
            ("step-push.html", "сповіщення увімкнено", "-push", 0, FRAME),
            ("step-push-asking.html", "системний запит", "-asking", 1, FRAME),
            ("step-push-denied.html", "у дозволі відмовлено", "-denied", 1, FRAME),
            ("step-push-sending.html", "надсилаємо пробне", "-sending", 1, FRAME),
            ("step-push-failed.html", "пробне не надійшло", "-failed", 1, FRAME),
        ]),
    ]),
    ("Дорога · де я і що далі", [
        ("road", "Дорога", [
            ("road-empty.html", "порожній: без кроків", "-empty", 0, "J2"),
            ("road-error.html", "помилка", "-error", 0, "J0"),
            ("road-error-save.html", "збережемо, щойно зможемо", "-save", 1, GOAL),
            ("road-loading.html", "завантаження", "-loading", 0, "J0"),
            ("road-loading-save.html", "зберігаємо", "-save", 1, GOAL),
            ("road.html", "успіх", "базова", 0, "J0"),
            ("road-noposition.html", "позицію не визначено", "-noposition", 0, "J2"),
            ("road-paused.html", "на паузі", "-paused", 0, "J0, J5"),
            ("road-nearfinish.html", "поруч із фінішем", "-nearfinish", 0, GOAL),
            ("road-done.html", "пройдена", "-done", 0, GOAL),
            ("road-cancelled.html", "скасована", "-cancelled", 0, "J5"),
            ("road-draft.html", "чернетка", "-draft", 0, "J3"),
            ("road-planned.html", "запланована", "-planned", 0, "J3, J5"),
        ]),
        ("new-road", "Нова дорога", [
            ("new-road-empty.html", "порожній", "-empty", 0, "J3"),
            ("new-road-error.html", "помилка", "-error", 0, "J3"),
            ("new-road-error-save.html", "збережемо, щойно зможемо", "-save", 1, "J3"),
            ("new-road-loading.html", "завантаження", "-loading", 0, "J3"),
            ("new-road-loading-save.html", "зберігаємо", "-save", 1, "J3"),
            ("new-road.html", "успіх", "базова", 0, "J3"),
            ("new-road-proposal.html", "пропозиція є", "-proposal", 0, "J3"),
            ("new-road-questions.html", "запитання замість пропозиції", "-questions", 0, "J3"),
            ("new-road-draft.html", "чернетка збережена", "-draft", 0, "J3"),
        ]),
    ]),
    ("Тиждень · чому я віддаю увагу", [
        ("week", "Тиждень", [
            ("week-empty.html", "порожній", "-empty", 0, "J1"),
            ("week-error.html", "помилка", "-error", 0, "J1"),
            ("week-error-save.html", "збережемо, щойно зможемо", "-save", 1, "J1"),
            ("week-loading.html", "завантаження", "-loading", 0, "J1"),
            ("week-loading-save.html", "зберігаємо", "-save", 1, "J1"),
            ("week.html", "успіх", "базова", 0, "J1"),
            ("week-first.html", "перший тиждень", "-first", 0, "J1"),
            ("week-lastweek.html", "діє вибір минулого тижня", "-lastweek", 0, "J1"),
            ("week-toomany.html", "більше трьох: продукт питає", "-toomany", 0, "J1"),
            ("week-quiet.html", "тиждень без руху", "-quiet", 0, "J1"),
        ]),
    ]),
]

SCREENS = {slug: (name, states) for _, scr in SECTIONS for slug, name, states in scr}
FILE2SCREEN = {st[0]: slug for slug, (_, states) in SCREENS.items() for st in states}
ALL_FILES = list(FILE2SCREEN)


def plural(n):
    """1 стан, 2 стани, 5 станів"""
    if n % 10 == 1 and n % 100 != 11:
        return str(n) + " стан"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return str(n) + " стани"
    return str(n) + " станів"


def tree(cur):
    """Дерево каркасів для сторінки cur: розділи й екрани; екран поточної сторінки — aria-current і t-open."""
    out = ['  <!-- Дерево каркасів: однакове на кожній сторінці, переїжджає лише aria-current і t-open -->',
           '  <nav class="wf-tree" aria-label="Каркаси: розділи й екрани">',
           '    <div class="wf-brand">',
           '      <p class="wf-brand-mark">WAY</p>',
           '      <p class="wf-brand-sub">каркаси · усі flows</p>',
           '    </div>',
           '    <ul>']
    for sec, screens in SECTIONS:
        out += ['      <li>', '        <span class="t-section">' + sec + '</span>', '        <ul>']
        for slug, name, states in screens:
            here = FILE2SCREEN.get(cur) == slug
            opn = ' class="t-open"' if here else ""
            mark = ' aria-current="true"' if here else ""
            out.append('          <li' + opn + '><a class="t-node t-screen" href="' + slug + '.html"' + mark + '>'
                       + name + ' <span class="t-lbl">' + plural(len(states)) + '</span></a></li>')
        out += ['        </ul>', '      </li>']
    out += ['    </ul>',
            '    <p class="wf-tree-foot">Розділи й екрани — з дерева sitemap.md. Стани екрана — зверху макета: основні й особливі вкладками.</p>',
            '  </nav>']
    return "\n".join(out)


MAIN4 = [("-empty", "порожній"), ("-error", "помилка"), ("-loading", "завантаження"), ("", "успіх")]


SPECIAL = "особливі стани"


def groups(slug):
    """Стани екрана деревом: основні чотири й особливі; у кожного — його варіанти.
    Повертає (main, special): main — [(файл, назва, [варіанти])], special — [(файл, назва, [варіанти])];
    варіант — (файл, назва)."""
    main_label = dict((slug + suf + ".html", lbl) for suf, lbl in MAIN4)
    main, special, last = [], [], None
    for f, label, _lbl, lvl, _flow in SCREENS[slug][1]:
        if lvl == 0:
            last = (f, main_label.get(f, label), [])
            (main if f in main_label else special).append(last)
        elif last:
            last[2].append((f, label))
    main.sort(key=lambda g: list(main_label).index(g[0]))
    return main, special


def states_bar(cur):
    """Стани екрана зверху макета, трьома рівнями; кожен показує лише дітей вибраного вище.
    1 — порожній · помилка · завантаження · успіх · особливі стани;
    2 — варіанти вибраного основного стану або перелік особливих станів;
    3 — варіанти вибраного особливого стану."""
    slug = FILE2SCREEN[cur]
    name = SCREENS[slug][0]
    main, special = groups(slug)

    def find(groups_):
        for g in groups_:
            if g[0] == cur or cur in [v[0] for v in g[2]]:
                return g
        return None

    sel_main, sel_special = find(main), find(special)

    def link(f, text, count=0, selected=False, cls=""):
        if f == cur:
            a = ' aria-current="page"'
        elif selected:
            a = ' aria-current="true"'
        else:
            a = ""
        c = ' class="' + cls + '"' if cls else ""
        n = ' <span class="wf-count">' + str(count) + '</span>' if count else ""
        return '<a href="' + f + '"' + a + c + '>' + text + n + '</a>'

    lvl1 = [link(f, lbl, len(vs), g is sel_main) for g in main for f, lbl, vs in [g]]
    if special:
        total = sum(1 + len(vs) for _, _, vs in special)
        lvl1.append(link(special[0][0], SPECIAL, total, bool(sel_special), "wf-special"))

    rows = ['      <div class="wf-states-main">',
            '        <p>Стани екрана «' + name + '»:</p>',
            '        <ul>'] + ['          <li>' + x + '</li>' for x in lvl1] + ['        </ul>', '      </div>']

    def row(cls, label, items):
        return (['      <ul class="' + cls + '" aria-label="' + label + '">']
                + ['        <li>' + x + '</li>' for x in items] + ['      </ul>'])

    if sel_main and sel_main[2]:
        rows += row("wf-tabs", "Варіанти стану «" + sel_main[1] + "»", [link(f, lbl) for f, lbl in sel_main[2]])
    if sel_special:
        rows += row("wf-tabs", "Особливі стани", [link(f, lbl, len(vs), g is sel_special) for g in special for f, lbl, vs in [g]])
        if sel_special[2]:
            rows += row("wf-subtabs", "Варіанти стану «" + sel_special[1] + "»", [link(f, lbl) for f, lbl in sel_special[2]])
    return ('    <nav class="wf-states" aria-label="Стани екрана «' + name + '»">\n'
            + "\n".join(rows) + '\n    </nav>')


def table():
    """Таблиця переліку сторінок для _conventions.md, розділ 4."""
    rows = ["| Екран | Файл | Стан | Flow |", "|---|---|---|---|"]
    for _, screens in SECTIONS:
        for slug, name, states in screens:
            first = True
            for f, label, _lbl, lvl, flow in states:
                rows.append("| " + ("**" + name + "**" if first else "") + " | `" + f + "` | "
                            + ("варіант: " if lvl else "") + label + " | " + flow + " |")
                first = False
    return "\n".join(rows)


TREE_RE = re.compile(r'[ \t]*(?:<!-- Дерево каркасів[^\n]*-->\s*)?<nav class="wf-tree".*?</nav>', re.S)
STATES_RE = re.compile(r'[ \t]*<nav class="wf-states".*?</nav>', re.S)


def inject(path):
    s = path.read_text(encoding="utf-8")
    cur = path.name
    if "<!-- WF-TREE -->" in s:
        s = s.replace("<!-- WF-TREE -->", tree(cur).lstrip(), 1)
    else:
        s, n = TREE_RE.subn(lambda m: tree(cur), s, count=1)
        if n != 1:
            raise SystemExit("немає дерева каркасів у " + cur)
    if "<!-- WF-STATES -->" in s:
        s = s.replace("<!-- WF-STATES -->", states_bar(cur).lstrip(), 1)
    else:
        s, n = STATES_RE.subn(lambda m: states_bar(cur), s, count=1)
        if n != 1:
            raise SystemExit("немає перемикача станів у " + cur)
    path.write_text(s, encoding="utf-8")


def main():
    args = sys.argv[1:]
    if args == ["--list"]:
        print("\n".join(ALL_FILES))
        return
    if args == ["--table"]:
        print(table())
        return
    done, missing = [], []
    for f in ALL_FILES:
        p = WF / f
        if p.exists():
            inject(p)
            done.append(f)
        else:
            missing.append(f)
    print("дерево вставлено: " + str(len(done)) + "; файлів немає: " + str(len(missing))
          + ((" — " + ", ".join(missing)) if missing else ""))


if __name__ == "__main__":
    main()
