#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Звірка набору каркасів: навігація, нейминг, зони, посилання, глухі кути.

Запуск із кореня репозиторію:  python3 tools/wf_audit.py

Перевіряє кожну сторінку з переліку tools/wf_tree.py:
- head: шрифти way-tau, Lucide, _wireframe.css; немає <script>, <style>, style="";
- дерево каркасів (розділи й екрани) і стани зверху — точно такі, як генерує wf_tree.py; у дереві позначено екран, у станах — поточну сторінку;
- <title> «WAY · <Екран> — <стан>», один h1, шапка продукту, службова смуга, «Куди далі за flow»;
- зони (data-section) — лише секції з дерева sitemap.md для свого екрана;
- кожне посилання й form action веде на наявний файл;
- у стану є вихід поза деревом каркасів і перемикачем;
- назва файлу за правилом _conventions.md §4.
Наприкінці — сторінки, на які не веде жоден перехід, і html поза переліком.
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wf_tree import ALL_FILES, FILE2SCREEN, SCREENS, WF, states_bar, tree  # noqa: E402

SLUG = {name: slug for slug, (name, _) in SCREENS.items()}
GLOBAL = ["глобальна навігація", "крок дня"]
EXTRA = {"road": ["перемикач доріг тижня"]}   # контекстне з sitemap.md «Навігація», а не з дерева
UNDER = {"step": "today"}                      # плаваючий екран показує під собою «Сьогодні» (inert)
HEAD_MUST = ["fonts.googleapis.com/css2?family=Unbounded", "lucide-static@1.49.0/font/lucide.css", 'href="_wireframe.css"']


def clean(name):
    return name.replace("[?]", "").strip()


def sitemap_sections():
    """Секції кожного екрана з дерева в sitemap.md (блок після «### Дерево»)."""
    text = (WF / "sitemap.md").read_text(encoding="utf-8")
    block = text.split("### Дерево", 1)[1].split("```", 2)[1]
    out, cur = {}, None
    for line in block.splitlines():
        m = re.match(r"^([│ ]*)[├└]─ (.+)$", line)
        if not m:
            continue
        depth = len(m.group(1)) // 3
        name = clean(re.split(r"\s{2,}|\(", m.group(2))[0])
        if depth == 1:
            cur = SLUG.get(name)
            if cur:
                out[cur] = []
        elif depth == 2 and cur:
            out[cur].append(name)
    return out


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.skip, self.inert = [], 0, 0
        self.out, self.all, self.sections, self.h1 = [], [], [], 0

    def handle_starttag(self, t, a):
        a = dict(a)
        cls = a.get("class") or ""
        skip = t == "nav" and ("wf-tree" in cls or "wf-states" in cls)
        inert = "inert" in a
        self.stack.append((t, skip, inert))
        self.skip += skip
        self.inert += inert
        if t == "h1":
            self.h1 += 1
        if "data-section" in a:
            self.sections.append((a["data-section"], bool(self.inert)))
        href = a.get("href") if t == "a" else a.get("action") if t == "form" else a.get("formaction") if t == "button" else None
        if href:
            self.all.append(href)
            if not self.skip and not self.inert:
                self.out.append(href)

    def handle_endtag(self, t):
        while self.stack:
            tag, skip, inert = self.stack.pop()
            self.skip -= skip
            self.inert -= inert
            if tag == t:
                break


def norm_tree(html):
    m = re.search(r'<nav class="wf-tree".*?</nav>', html, re.S)
    return m.group(0).replace(' aria-current="true"', "").replace(' class="t-open"', "") if m else None


def main():
    sections = sitemap_sections()
    problems = []
    ref = norm_tree(tree(ALL_FILES[0]))
    incoming = {f: set() for f in ALL_FILES}
    for f in ALL_FILES:
        p = WF / f
        if not p.exists():
            problems.append((f, "файлу немає"))
            continue
        html = p.read_text(encoding="utf-8")
        slug = FILE2SCREEN[f]
        for h in HEAD_MUST:
            if h not in html:
                problems.append((f, "head: немає " + h))
        if re.search(r"<script|<style|\sstyle=", html):
            problems.append((f, "є script чи style"))
        if "<!-- WF-" in html:
            problems.append((f, "лишився плейсхолдер — запустити tools/wf_tree.py"))
        if norm_tree(html) != ref:
            problems.append((f, "дерево каркасів відрізняється — запустити tools/wf_tree.py"))
        if '<a class="t-node t-screen" href="' + slug + '.html" aria-current="true">' not in html:
            problems.append((f, "у дереві не позначено екран поточної сторінки"))
        if '<a href="' + f + '" aria-current="page">' not in html:
            problems.append((f, "у станах зверху не позначено поточну сторінку"))
        if states_bar(f).strip() not in html:
            problems.append((f, "перемикач станів відрізняється"))
        m = re.search(r"<title>(.*?)</title>", html)
        if not (m and m.group(1).startswith("WAY · " + SCREENS[slug][0] + " — ")):
            problems.append((f, "title «" + (m.group(1) if m else "") + "»"))
        lp = Links()
        lp.feed(html)
        stub = 'class="stub"' in html
        if lp.h1 != 1:
            problems.append((f, "h1: " + str(lp.h1)))
        if not stub and 'data-section="глобальна навігація"' not in html:
            problems.append((f, "немає шапки продукту"))
        if '<footer class="wf">' not in html:
            problems.append((f, "немає службової смуги"))
        if not stub and 'class="wf-next"' not in html:
            problems.append((f, "немає «Куди далі за flow»"))
        allowed = sections.get(slug, []) + GLOBAL + EXTRA.get(slug, [])
        under = sections.get(UNDER.get(slug, ""), [])
        for name, inert in lp.sections:
            base = clean(name.split(" · ")[0])
            if not any(base.startswith(x) for x in allowed + (under if inert else [])):
                problems.append((f, "зона поза sitemap.md: «" + name + "»"))
        for h in lp.all:
            if h.startswith(("http", "#")):
                continue
            t = h.split("#")[0].split("?")[0]
            if t and not (WF / t).exists():
                problems.append((f, "посилання в нікуди: " + h))
        exits = {h.split("#")[0].split("?")[0] for h in lp.out} - {"", f}
        if not exits:
            problems.append((f, "глухий кут: жодного переходу поза деревом"))
        for t in exits:
            if t in incoming:
                incoming[t].add(f)
        if not re.fullmatch(r"(today|step|road|new-road|week)(-[a-z]+){0,2}\.html", f):
            problems.append((f, "назва файлу поза правилом"))

    print("сторінок у переліку: " + str(len(ALL_FILES)) + "; проблем: " + str(len(problems)))
    for f, msg in problems:
        print("  " + f + ": " + msg)
    orphans = [f for f, src in incoming.items() if not src]
    print("без вхідних переходів поза деревом: " + (", ".join(orphans) or "немає"))
    extra = sorted(x.name for x in WF.glob("*.html") if x.name not in ALL_FILES and x.name != "ia.html")
    print("html поза переліком: " + (", ".join(extra) or "немає"))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
