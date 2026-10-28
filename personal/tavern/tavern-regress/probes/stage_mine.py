"""Собрать индекс только из СВОИХ ханок, когда файл правят несколько сессий.

Зачем: `git add <файл>` стейджит файл ЦЕЛИКОМ. В партиалах `GridCursor.*`,
`HudUI.*`, `ObjectDef.cs`, `FurnitureCatalog.*` сегодня одновременно работают
до пяти сессий, и обычный `git add` уносит в коммит чужую незаконченную
правку (случилось 11.09, коммит 341bdfb6 — разбор в SESSIONS.md, «Коммиты»).

Как работает: сравнивает рабочее дерево с HEAD, делит расхождения на блоки и
оставляет только те, где встречаются ТВОИ слова. Блок, где нашлись и твои, и
чужие слова, разбирается построчно: выбрасываются ТОЛЬКО строки с чужими
словами, нейтральные (скобки, `return`, `get`) остаются — иначе от блока
оставалась одна начинка без объявлений и код не собирался (поймал ilya-97
11.09 на `FireplaceFire.cs`: 6 строк вместо 21). Изменённое содержимое кладётся
прямо в индекс через `git hash-object` + `git update-index` — РАБОЧЕЕ ДЕРЕВО НЕ
ТРОГАЕТСЯ, чужие правки остаются на диске как были.

Сторож: если у файла в рабочем дереве скобки сходятся, а у собранной версии
нет — файл НЕ стейджится вовсе, и скрипт говорит почему. Разрез по словам
может попасть в середину объявления, и такую версию лучше не коммитить совсем,
чем коммитить молча.

    python3 stage_mine.py --repo /media/ilya/T714/Unity/Tavern-fresh \\
        --mine ворон,perch,CrowPerch --foreign камин,Fire,fireplace \\
        Assets/Modules/Grid/Cursor/GridCursor.cs Assets/Game/UI/Hud/HudUI.cs

Дальше обычный `git commit` (без -a!) и ОБЯЗАТЕЛЬНО `git diff --cached` —
глазами найти в нём чужие слова. Скрипт помогает, но не отменяет проверку.
"""
import argparse, difflib, os, subprocess, sys


def head_lines(repo, path):
    out = subprocess.run(['git', 'show', 'HEAD:' + path], cwd=repo, capture_output=True, text=True)
    return out.stdout.splitlines(keepends=True) if out.returncode == 0 else []


def hit(line, words):
    return any(w and w in line for w in words)


PAIRS = (('{', '}'), ('(', ')'), ('[', ']'))


def unbalanced(text):
    return [o + c for o, c in PAIRS if text.count(o) != text.count(c)]


def stage(repo, path, mine, foreign):
    head = head_lines(repo, path)
    work = open(os.path.join(repo, path), encoding='utf-8').readlines()
    blocks = difflib.SequenceMatcher(None, head, work, autojunk=False).get_opcodes()
    out, kept, skipped, split = [], 0, 0, 0
    for tag, i1, i2, j1, j2 in blocks:
        was, now = head[i1:i2], work[j1:j2]
        is_mine = any(hit(l, mine) for l in was + now)
        is_foreign = any(hit(l, foreign) for l in was + now)
        if tag == 'equal':
            out.extend(was)
        elif is_mine and not is_foreign:
            out.extend(now); kept += 1
        elif is_mine and is_foreign and tag == 'insert':
            # Нейтральная строка (ни своих слов, ни чужих) — СВОЯ: скобки,
            # `return`, `get` держат объявление, и выбрасывать их нельзя.
            out.extend(l for l in now if not hit(l, foreign))
            kept += 1; split += 1
        else:
            out.extend(was); skipped += 1
    content = ''.join(out)
    torn = unbalanced(content)
    if torn and not unbalanced(''.join(work)):
        print('%s: ⛔ НЕ застейджено — в собранной версии не сходятся %s, '
              'а в рабочем дереве сходятся. Разрез попал в середину объявления: '
              'уточни слова или закоммить файл целиком.' % (path, ', '.join(torn)))
        return
    blob = subprocess.run(['git', 'hash-object', '-w', '--path', path, '--stdin'], cwd=repo,
                          input=content, capture_output=True, text=True).stdout.strip()
    subprocess.run(['git', 'update-index', '--add', '--cacheinfo', '100644,%s,%s' % (blob, path)],
                   cwd=repo, check=True)
    note = ', смешанных блоков разобрано построчно %d' % split if split else ''
    print('%s: своих блоков %d, чужих пропущено %d%s | строк HEAD %d, в индексе %d, в дереве %d'
          % (path, kept, skipped, note, len(head), content.count(chr(10)), len(work)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--mine', required=True, help='слова твоей правки через запятую')
    ap.add_argument('--foreign', default='', help='слова чужой правки через запятую')
    ap.add_argument('files', nargs='+')
    a = ap.parse_args()
    mine = [w.strip() for w in a.mine.split(',') if w.strip()]
    foreign = [w.strip() for w in a.foreign.split(',') if w.strip()]
    for f in a.files:
        stage(a.repo, f, mine, foreign)
    print('дальше: git diff --cached — глазами поискать чужие слова, потом git commit (без -a)')


if __name__ == '__main__':
    main()
