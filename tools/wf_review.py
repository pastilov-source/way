#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Критика каркасів за п'ятьма дефектами (wireframes/_critique.md).

Запуск із кореня репозиторію:  python3 tools/wf_review.py

Дефекти:
1. Заглушки — lorem ipsum, «Заголовок 1», «Текст кнопки», TODO; латиниця в тексті продукту.
2. Немає станів — стан із таблиці _screens.md без сторінки; вузол flow, позначений у службовій смузі «— ще немає».
3. Глухий кут — у самому продукті (без службової смуги, дерева, перемикача й шапки) жодного переходу.
4. Зона без головної дії — мітка «немає…» без посилання далі; заявлена дія, якої в зоні немає;
   головна дія-кнопка, що нікуди не веде. Редагування на місці («Змінити», «Додати ресурс»…) — прийнято, лише в довідці.
5. Екран не з карти — html у wireframes/, якого немає в переліку tools/wf_tree.py.
Код виходу 1, якщо є дефекти, крім прийнятих.
"""
import collections
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wf_tree import ALL_FILES, FILE2SCREEN, SCREENS, WF  # noqa: E402

VOID = {"br", "img", "input", "meta", "link", "hr", "source", "area", "col", "wbr"}
SERVICE_PAGES = {"ia.html"}   # зведена сторінка структури, не каркас
ENG_OK = {"way", "behance", "after", "effects", "iphone", "safari", "chrome", "edge", "opera", "firefox", "android",
          "ios", "picture", "in", "estimate", "md", "sitemap", "flows", "flow", "jtbd", "html", "ai", "pip", "telegram"}
IN_PLACE = {"Змінити", "Додати ресурс", "Поправити позицію", "Поправити етапи", "Уточнити фініш", "Намітити етапи",
            "Описати точку старту", "Замінити"}
PLACEHOLDERS = [r"lorem", r"ipsum", r"Заголовок \d", r"Текст кнопки", r"Placeholder", r"\bTODO\b", r"\bTBD\b",
                r"\bxxx\b", r"Назва \d", r"Підзаголовок"]
ACCEPTED = {"редагування на місці (прийнято)", "службова сторінка (прийнято)"}


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.kids, self.text = tag, dict(attrs), parent, [], []

    def all(self):
        for k in self.kids:
            yield k
            yield from k.all()

    def txt(self):
        return " ".join(self.text + [k.txt() for k in self.kids]).strip()

    def cls(self):
        return self.attrs.get("class") or ""

    def inert(self):
        n = self
        while n:
            if "inert" in n.attrs:
                return True
            n = n.parent
        return False

    def inside(self, pred):
        n = self.parent
        while n:
            if pred(n):
                return True
            n = n.parent
        return False


class DOM(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root", {}, None)
        self.cur = self.root

    def handle_starttag(self, t, a):
        n = Node(t, a, self.cur)
        self.cur.kids.append(n)
        if t not in VOID:
            self.cur = n

    def handle_endtag(self, t):
        n = self.cur
        while n and n.tag != t:
            n = n.parent
        if n and n.parent:
            self.cur = n.parent

    def handle_data(self, d):
        if d.strip():
            self.cur.text.append(d.strip())


def service(n):
    return (n.tag == "footer" and "wf" in n.cls()) or (n.tag == "nav" and ("wf-tree" in n.cls() or "wf-states" in n.cls()))


def target(n):
    if n.tag == "a" and n.attrs.get("href"):
        return n.attrs["href"]
    if n.tag == "form" and n.attrs.get("action"):
        return n.attrs["action"]
    if n.tag == "button" and n.attrs.get("formaction"):
        return n.attrs["formaction"]
    return None


def live(n):
    return [k for k in n.all() if (k.tag == "a" and k.attrs.get("href"))
            or (k.tag in ("button", "input", "summary") and "disabled" not in k.attrs)]


def norm(s):
    return re.sub(r"[«»\"'“”.,:!?…()]", "", s.lower()).strip()


def screens_table():
    """Стани з таблиці «Зведення» в _screens.md: [(slug, суфікс, '✓' або '—')]."""
    text = (WF / "_screens.md").read_text(encoding="utf-8")
    slug = {name: s for s, (name, _) in SCREENS.items()}
    out = []
    for m in re.finditer(r"^\| \*\*(.+?)\*\* \|(.+)\|$", text, re.M):
        if m.group(1) not in slug:
            continue
        marks = [c.strip() for c in m.group(2).split("|")]
        if len(marks) == 4 and all(x in ("✓", "—") for x in marks):
            for suf, mark in zip(["-empty", "-error", "-loading", ""], marks):
                out.append((slug[m.group(1)], suf, mark))
    return out


def review_page(f):
    rows = []
    d = DOM()
    d.feed((WF / f).read_text(encoding="utf-8"))
    nodes = list(d.root.all())
    stub = any(n.cls() == "stub" for n in nodes)

    # 1. заглушки
    prod = " ".join(n.txt() for n in nodes if n.tag in ("main", "aside", "dialog", "header") and not n.inside(service))
    for pat in PLACEHOLDERS:
        if re.search(pat, prod, re.I):
            rows.append((f, "заглушка в тексті", pat))
    for w in sorted(set(re.findall(r"\b[A-Za-z]{3,}\b", prod))):
        if w.lower() not in ENG_OK:
            rows.append((f, "латиниця в тексті", w))

    # 2. вузли flow, яких ще немає
    for n in nodes:
        if n.tag == "footer" and "wf" in n.cls():
            for m in re.findall(r"([^.;→]{0,60}— ще немає)", n.txt()):
                rows.append((f, "немає стану: вузол flow «ще немає»", re.sub(r"\s+", " ", m).strip()))

    # 3. глухий кут
    exits = set()
    for n in nodes:
        t = target(n)
        if not t or n.inert() or n.inside(service) or service(n) or n.inside(lambda x: x.tag == "header"):
            continue
        base = t.split("#")[0].split("?")[0]
        if base and base != f:
            exits.add(base)
        elif t.startswith("#"):
            exits.add(t)
    if not exits:
        rows.append((f, "глухий кут", "у самому продукті жодного переходу" + (" (заглушка)" if stub else "")))
    for n in nodes:
        t = target(n)
        if t and not t.startswith(("#", "http")):
            b = t.split("#")[0].split("?")[0]
            if b and not (WF / b).exists():
                rows.append((f, "глухий кут: посилання в нікуди", t))

    # 4. зона без головної дії
    for n in nodes:
        if "data-section" not in n.attrs or n.inert():
            continue
        name = n.attrs["data-section"].split(" · ")[0]
        act = n.attrs.get("data-action", "")
        skel = any("skel" in k.cls() for k in n.all())
        if not act:
            rows.append((f, "зона без головної дії", name + ": немає мітки data-action"))
            continue
        if act.startswith("немає"):
            if not live(n) and not skel:
                rows.append((f, "зона без головної дії", name + ": «" + act + "» — і жодного посилання далі"))
            continue
        if skel and not live(n):
            rows.append((f, "зона без головної дії", name + ": у зоні лише скелет, а мітка обіцяє «" + act + "»"))
            continue
        if act[:1].islower():
            if not live(n) and not act.startswith(("побачити", "бачити")):
                rows.append((f, "зона без головної дії", name + ": заявлено «" + act + "», активного елемента немає"))
        else:
            key = norm(re.split(r" — |;|\(", act)[0])
            ctrls = [k for k in n.all() if k.tag in ("button", "a", "summary")
                     or (k.tag == "input" and k.attrs.get("type") in ("submit", "radio", "text", "search", "checkbox"))]
            texts = [norm(k.txt() or k.attrs.get("aria-label", "") or k.attrs.get("value", "")) for k in ctrls]
            ok = n.tag == "header" or any(key and (key in t or (t and t in key)) for t in texts)
            if not ok and any(k.tag == "input" for k in ctrls) and any(w in key for w in ("обрати", "відповісти", "описати", "записати")):
                ok = True
            if not ok:
                rows.append((f, "зона без головної дії", name + ": заявлено «" + act + "», такого елемента в зоні немає"))
        for k in n.all():
            if k.tag == "button" and "main-action" in k.cls() and "disabled" not in k.attrs:
                if not k.inside(lambda x: x.tag == "form") and not k.attrs.get("formaction") and not k.attrs.get("form"):
                    cat = "редагування на місці (прийнято)" if k.txt() in IN_PLACE else "головна дія без переходу"
                    rows.append((f, cat, name + ": «" + k.txt() + "»"))
    return rows


def main():
    rows = []
    for f in ALL_FILES:
        if (WF / f).exists():
            rows += review_page(f)
    # 2. стани з _screens.md
    for slug, suf, mark in screens_table():
        f = slug + suf + ".html"
        p = WF / f
        if mark == "✓" and not p.exists():
            rows.append((f, "немає стану: за _screens.md", "стан позначено ✓, сторінки немає"))
        if mark == "—" and p.exists() and 'class="stub"' not in p.read_text(encoding="utf-8"):
            rows.append((f, "немає стану: за _screens.md", "стан позначено «—», а сторінка не заглушка"))
    # 5. екран не з карти
    for x in sorted(p.name for p in WF.glob("*.html")):
        if x in SERVICE_PAGES:
            rows.append((x, "службова сторінка (прийнято)", "не каркас"))
        elif x not in FILE2SCREEN:
            rows.append((x, "екран не з карти", "файлу немає в переліку tools/wf_tree.py"))

    by = collections.OrderedDict()
    for f, cat, msg in rows:
        by.setdefault(cat, []).append((f, msg))
    blocking = sum(len(v) for k, v in by.items() if k not in ACCEPTED)
    print("сторінок: " + str(len(ALL_FILES)) + "; дефектів: " + str(blocking)
          + "; прийнятих: " + str(sum(len(v) for k, v in by.items() if k in ACCEPTED)))
    for cat, items in by.items():
        print("\n[" + cat + "] " + str(len(items)))
        for f, msg in items:
            print("  " + f + " — " + msg)
    sys.exit(1 if blocking else 0)


if __name__ == "__main__":
    main()
