#!/usr/bin/env python3
"""Скільки часу пішло на проєкт — за логами сесій Claude Code і комітами git.

Запуск із кореня репозиторію:

    python3 tools/timecount.py

Як рахує і що не потрапляє в підрахунок — tools/README.md.
"""
import json
import os
import re
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path

GAP = 30          # хв тиші, після яких починається перерва
GAP_WIDE = 45     # верхня межа: паузи до 45 хв теж вважаємо роботою
TAIL = 5          # хв на читання останньої відповіді у відрізку
CLAUDE_WAIT = 10  # довша пауза всередині ходу Claude — це він чекає на людину

# Робота поза Claude, якої немає в логах: (дата, що робили, хвилини).
OFFLINE = [
    ('2026-09-03', 'дискавері-сесія із замовником', 60),
]

HERE = Path(os.path.abspath(__file__)).parent
REPO = HERE.parent
CACHE = HERE / '.timecount-cache.json'
PROJECTS = Path(os.environ.get('CLAUDE_CONFIG_DIR', '~/.claude')).expanduser() / 'projects'
ASKS = ('AskUserQuestion', 'ExitPlanMode')
NOT_PROMPTS = ('<task-notification', '<local-command', '[Request interrupted', '<system-reminder>')
WEEKDAYS = ('пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'нд')


def project_dirs():
    """Теки з логами Claude Code для цього репо та його worktree."""
    names = {re.sub(r'[^a-zA-Z0-9]', '-', p) for p in (str(REPO), os.path.realpath(REPO))}
    if not PROJECTS.is_dir():
        return []
    return [d for d in PROJECTS.iterdir() if d.is_dir() and any(
        d.name == n or d.name.startswith(n + '--claude-worktrees-') for n in names)]


def is_prompt(o):
    """Промпт, який написала людина, а не результат інструмента чи системна вставка."""
    if o.get('isMeta') or o.get('isSidechain'):
        return False
    c = o.get('message', {}).get('content')
    if isinstance(c, list):
        if any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in c):
            return False
        c = ' '.join(b.get('text', '') for b in c if isinstance(b, dict) and b.get('type') == 'text')
    return isinstance(c, str) and bool(c.strip()) and not c.strip().startswith(NOT_PROMPTS)


def kind_of(o):
    t = o.get('type')
    if t == 'assistant':
        content = o.get('message', {}).get('content')
        blocks = content if isinstance(content, list) else []
        asks = any(isinstance(b, dict) and b.get('name') in ASKS for b in blocks)
        return 'ask' if asks else 'assistant'
    if t == 'user':
        return 'prompt' if is_prompt(o) else 'tool'
    if t == 'queue-operation' and o.get('operation') == 'enqueue':
        return 'queued'
    return None


def load_live():
    """{сесія: {title, events: [[unix-час, вид], ...]}} з логів на диску."""
    sessions, seen = {}, set()
    for d in project_dirs():
        for f in sorted(d.rglob('*.jsonl')):
            sid = f.relative_to(d).parts[0].split('.')[0]  # логи субагентів — у теці своєї сесії
            s = sessions.setdefault(sid, {'title': None, 'ai_title': None, 'events': []})
            with open(f, encoding='utf-8') as fh:
                for line in fh:
                    try:
                        o = json.loads(line)
                    except ValueError:
                        continue
                    if o.get('type') == 'custom-title' and o.get('customTitle'):
                        s['title'] = o['customTitle']
                    elif o.get('type') == 'ai-title' and o.get('aiTitle'):
                        s['ai_title'] = o['aiTitle']
                    uid, ts, kind = o.get('uuid'), o.get('timestamp'), kind_of(o)
                    if not ts or not kind or uid in seen:
                        continue
                    if uid:
                        seen.add(uid)
                    t = datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp()
                    s['events'].append([t, kind])
    return {sid: {'title': s['title'] or s['ai_title'] or sid[:8], 'events': sorted(s['events'])}
            for sid, s in sessions.items() if s['events']}


def load_sessions():
    """Живі логи + кеш. Claude Code стирає старі логи, кеш зберігає з них таймстемпи."""
    cached = {}
    if CACHE.exists():
        try:
            cached = json.loads(CACHE.read_text(encoding='utf-8'))
        except ValueError:
            pass
    live = load_live()
    sessions = {**cached, **live}
    CACHE.write_text(json.dumps(sessions, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return sessions, len(sessions) - len(live)


def split(events, gap):
    """Відрізки роботи: тиша довша за gap хвилин розриває відрізок."""
    blocks = []
    for t, sid in events:
        if blocks and t - blocks[-1]['end'] <= gap * 60:
            blocks[-1]['end'] = t
        else:
            blocks.append({'start': t, 'end': t, 'sids': {}})
        blocks[-1]['sids'].setdefault(sid)
    return blocks


def length(block):
    return (block['end'] - block['start']) / 60 + TAIL


def claude_minutes(sessions):
    """Час, коли працював Claude: від промпту чи результату інструмента до його наступної дії.

    Пауза перед новим промптом — час людини. Пауза після питання людині
    або довша за CLAUDE_WAIT — він чекав. Паралельні сесії не рахуються двічі."""
    spans = []
    for s in sessions.values():
        ev = [e for e in s['events'] if e[1] != 'queued']
        for (t0, k0), (t1, k1) in zip(ev, ev[1:]):
            if k1 != 'prompt' and k0 != 'ask' and t1 - t0 <= CLAUDE_WAIT * 60:
                spans.append((t0, t1))
    total, end = 0.0, float('-inf')
    for a, b in sorted(spans):
        total += max(0.0, b - max(a, end))
        end = max(end, b)
    return total / 60


def commits():
    try:
        out = subprocess.run(['git', '-C', str(REPO), 'log', '--format=%ct%x09%s'],
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    return sorted((int(ts), subj) for ts, subj in
                  (line.split('\t', 1) for line in out.splitlines() if '\t' in line))


def hm(minutes):
    m = int(round(minutes))
    return f'{m // 60} год {m % 60:02d} хв' if m >= 60 else f'{m} хв'


def row(label, minutes, note=''):
    print(f'{label:<14}{hm(minutes):>12}' + (f'   {note}' if note else ''))


def local(t):
    return datetime.fromtimestamp(t)


def main():
    sessions, only_cached = load_sessions()
    events = sorted((e[0], sid) for sid, s in sessions.items() for e in s['events'])
    if not events:
        print(f'Логів Claude Code для {REPO} не знайдено в {PROJECTS}.')
        return

    blocks = split(events, GAP)
    total = sum(length(b) for b in blocks)
    total_wide = sum(length(b) for b in split(events, GAP_WIDE))
    claude = claude_minutes(sessions)
    offline = sum(m for _, _, m in OFFLINE)
    prompts = sum(1 for s in sessions.values() for e in s['events'] if e[1] == 'prompt')
    log = commits()

    print(f'Час на проєкт {REPO.name}')
    print(f'Логи Claude Code: сесій {len(sessions)}, промптів {prompts}, '
          f'{local(events[0][0]):%d.%m.%Y} – {local(events[-1][0]):%d.%m.%Y}')
    if only_cached:
        print(f'  з них {only_cached} — тільки з кешу, логи вже стерто')

    print(f'\nВідрізки роботи (тиша понад {GAP} хв — перерва; +{TAIL} хв на читання відповіді)')
    per_day = defaultdict(float)
    for b in blocks:
        start, end = local(b['start']), local(b['end'])
        per_day[start.date()] += length(b)
        titles = ' · '.join(sessions[sid]['title'] for sid in b['sids'])
        print(f'  {WEEKDAYS[start.weekday()]} {start:%d.%m}  {start:%H:%M}–{end:%H:%M}  {hm(length(b)):>11}  {titles}')
        for _, subj in (c for c in log if b['start'] <= c[0] <= b['end'] + 60):
            print(f'{"":36}· {subj}')

    print('\nПо днях')
    for d in sorted(per_day):
        row(f'  {WEEKDAYS[d.weekday()]} {d:%d.%m}', per_day[d])

    wide = total_wide - total >= 1
    print()
    row('З Claude', total, f'до {hm(total_wide)}, якщо й паузи до {GAP_WIDE} хв були роботою' if wide else '')
    row('  Claude', claude, 'генерував і виконував команди')
    row('  людина', total - claude, 'читала, думала, відповідала, писала промпти')
    if OFFLINE:
        row('Поза Claude', offline)
        for date, what, m in OFFLINE:
            row(f'  {datetime.strptime(date, "%Y-%m-%d"):%d.%m}', m, what)
    row('Разом', total + offline, f'до {hm(total_wide + offline)}' if wide else '')


if __name__ == '__main__':
    main()
