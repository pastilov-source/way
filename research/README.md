# research/

Кабінетний ресерч. Інтерв'ю з користувачами не буде (рішення D19) — компенсуємо аналізом продуктів, патернів і літератури.

| Файл | Що це |
|---|---|
| `research.md` | Головний документ: питання, метод, знахідки, висновки. |
| `screens/` | Скриншоти інтерфейсів-референсів. Назва файлу: `продукт--патерн--нотатка.png` (напр. `things--today--один-крок.png`). |

Правило: кожна знахідка в `research.md` посилається на файл у `screens/`, або її немає.

---

## Публікація

Сторінка [`research.html`](research.html) опублікована на Vercel: **https://way-research-pastilov-sources-projects.vercel.app**

Деплой **ручний, за командою** — автодеплой на пуш свідомо не підключений.

```bash
cd research && npx vercel@latest deploy --prod
```

`vercel.json` віддає `research.html` на корені домену. Скріни підтягуються відносними шляхами з `screens/`.

**Перевірка, що сторінка справді публічна.** Власника Vercel пропускає по сесійній куці, тож «у мене відкривається» нічого не доводить. Перевіряти анонімно:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://way-research-pastilov-sources-projects.vercel.app/
```

`200` — публічна. `302` — увімкнено Deployment Protection, вимикається в Project Settings → Deployment Protection.
