"""Збирає concept/directions.html з _host.html і фрагментів напрямів.

Запуск з кореня репозиторію: python3 concept/directions/_build.py
Версію 4 спершу збирає _build_v4.py. Заголовки фрагментів підганяються під сторінку: h1 сторінки → h2 розділу → h3 і нижче у фрагментах.
"""
import re
from pathlib import Path

HERE = Path(__file__).parent
FONTS = (
    "https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;500;600"
    "&family=Dela+Gothic+One&family=Geologica:wght@300..700"
    "&family=Arsenal:ital,wght@0,400;0,700;1,400&family=Caveat:wght@500..700"
    "&family=Sofia+Sans+Extra+Condensed:wght@500..800"
    "&family=Literata:opsz,wght@7..72,400;7..72,600&display=swap"
)
META = {
    "riso": ("Різограф",
             "Дорога друкується двома фарбами. Зроблене — у збігу, і фарби дають фіолетовий; крок у роботі ще не зійшовся.",
             ["світлий", "багато кольору", "Dela Gothic One + Geologica", "гострі кути", "Solar Bold"],
             "<b>Чи вгадати з теми?</b> Ні. Тема дороги підказує зелене, асфальт і дорожній жовтий, а тут флуоресцентний рожевий і синій ризографа. Зв'язок із дорогою тримається на суміщенні фарб, а не на кольорах."),
    "zoshyt": ("Зошит у клітинку",
               "Дорога пишеться фіолетовою ручкою в шкільному зошиті. Крок дня — аркуш, вирваний із блокнота, як у ритуалі замовника.",
               ["світлий", "мало кольору", "Arsenal + Caveat", "тонкі лінії, скруглення 4px", "Solar Linear"],
               "<b>Чи вгадати з теми?</b> З теми дороги — ні. Але «паперовий планер» — знайома для категорії колія, тож чесно: найближчий до очікуваного з трьох. Відрізняє його фіолетове чорнило, біла клітинка замість кремового паперу й аркуш із ритуалу."),
    "score": ("Партитура",
              "Дорога записана як танцювальна партитура: читається знизу вгору, висота блока — скільки днів зайняв крок, заливка — його стан.",
              ["темний", "нуль кольору", "Sofia Sans Extra Condensed + Literata", "прямокутні блоки", "Solar Bold Duotone"],
              "<b>Чи вгадати з теми?</b> Переважно ні. Графітовий фон близький до асфальту, але акценту немає зовсім, навіть на кнопці. Стан передає заливка, а не колір — це треба перевірити на дрібному розмірі."),
}


def demote(frag, top=3):
    """Підганяє заголовки фрагмента під сторінку: найвищий стає h{top}."""
    levels = [int(n) for n in re.findall(r"<h([1-6])\b", frag)]
    if not levels:
        return frag
    shift = top - min(levels)
    return re.sub(r"(?<=[<\s/,>])h([1-6])(?=[\s>{,.:\[])",
                  lambda m: "h%d" % min(6, int(m.group(1)) + shift), frag)


def column(slug):
    name, thesis, tags, check = META[slug]
    frag = demote((HERE / f"{slug}.html").read_text(), top=4)
    tag_items = "".join(f"<li>{t}</li>" for t in tags)
    return f"""<article class="h-col" aria-labelledby="h-{slug}">
  <div class="h-meta">
    <h3 id="h-{slug}">{name}</h3>
    <p class="h-thesis">{thesis}</p>
    <ul class="h-tags">{tag_items}</ul>
    <p class="h-check">{check}</p>
  </div>
  <div class="h-frame">
{frag}
  </div>
</article>"""


host = (HERE / "_host.html").read_text()
out = (host.replace("{{FONTS}}", FONTS.replace("&", "&amp;"))
           .replace("{{V4}}", demote((HERE / "score-graph.html").read_text(), top=3))
           .replace("{{COLUMNS}}", "\n".join(column(s) for s in ("riso", "zoshyt", "score"))))
(HERE.parent / "directions.html").write_text(out)
print("concept/directions.html", len(out))
