#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Єдине джерело переліку каркасів, дерева каркасів і перемикача станів.

Запуск із кореня репозиторію:
  python3 tools/wf_tree.py            — вставити дерево й перемикач станів у кожну сторінку wireframes/
  python3 tools/wf_tree.py --list     — перелік файлів
  python3 tools/wf_tree.py --table    — таблиця «екран · файл · стан · flow» для _conventions.md, розділ 4

Сторінка отримує дерево на місці <!-- WF-TREE --> або наявного <nav class="wf-tree">…</nav>,
перемикач — на місці <!-- WF-STATES --> або наявного <nav class="wf-states">…</nav>.
Нова сторінка чи стан додаються в SECTIONS нижче — і тоді вони з'являються в дереві всіх сторінок.
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


def tree(cur):
    """Дерево каркасів для сторінки cur: поточний стан — aria-current, його екран — t-open."""
    out = ['  <!-- Дерево каркасів: однакове на кожній сторінці, переїжджає лише aria-current і t-open -->',
           '  <nav class="wf-tree" aria-label="Каркаси: розділи, екрани й стани">',
           '    <div class="wf-brand">',
           '      <p class="wf-brand-mark">WAY</p>',
           '      <p class="wf-brand-sub">каркаси · усі flows</p>',
           '    </div>',
           '    <ul>']
    for sec, screens in SECTIONS:
        out += ['      <li>', '        <span class="t-section">' + sec + '</span>', '        <ul>']
        for slug, name, states in screens:
            opn = ' class="t-open"' if FILE2SCREEN.get(cur) == slug else ""
            out += ['          <li' + opn + '>',
                    '            <a class="t-node t-screen" href="' + slug + '.html">' + name + ' <span class="t-lbl">екран</span></a>',
                    '            <ul>']
            i = 0
            while i < len(states):
                f, label, lbl, _lvl, _flow = states[i]
                mark = ' aria-current="page"' if f == cur else ""
                link = '<a class="t-node" href="' + f + '"' + mark + '>' + label + ' <span class="t-lbl">' + lbl + '</span></a>'
                variants = []
                j = i + 1
                while j < len(states) and states[j][3] == 1:
                    vf, vlabel, vlbl = states[j][:3]
                    vm = ' aria-current="page"' if vf == cur else ""
                    variants.append('                  <li><a class="t-node" href="' + vf + '"' + vm + '>' + vlabel
                                    + ' <span class="t-lbl">' + vlbl + '</span></a></li>')
                    j += 1
                if variants:
                    out += ['              <li>', '                ' + link, '                <ul>', *variants,
                            '                </ul>', '              </li>']
                else:
                    out.append('              <li>' + link + '</li>')
                i = j
            out += ['            </ul>', '          </li>']
        out += ['        </ul>', '      </li>']
    out += ['    </ul>',
            '    <p class="wf-tree-foot">Розділи й екрани — з дерева sitemap.md, стани — з таблиці станів sitemap.md, _screens.md і flows.md.</p>',
            '  </nav>']
    return "\n".join(out)


MAIN4 = [("-empty", "порожній"), ("-error", "помилка"), ("-loading", "завантаження"), ("", "успіх")]


def states_bar(cur):
    """Перемикач чотирьох основних станів екрана зверху макета."""
    slug = FILE2SCREEN[cur]
    name = SCREENS[slug][0]
    items = []
    for suf, lbl in MAIN4:
        f = slug + suf + ".html"
        mark = ' aria-current="page"' if f == cur else ""
        items.append('        <li><a href="' + f + '"' + mark + '>' + lbl + '</a></li>')
    return ('    <nav class="wf-states" aria-label="Стани екрана «' + name + '»">\n'
            '      <p>Стани екрана «' + name + '»:</p>\n'
            '      <ul>\n' + "\n".join(items) + '\n      </ul>\n'
            '    </nav>')


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
