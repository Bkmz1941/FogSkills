"""Собрать индекс только из СВОИХ ханок, когда файл правят несколько сессий.

Зачем: `git add <файл>` стейджит файл ЦЕЛИКОМ. В партиалах `GridCursor.*`,
`HudUI.*`, `ObjectDef.cs`, `FurnitureCatalog.*` сегодня одновременно работают
до пяти сессий, и обычный `git add` уносит в коммит чужую незаконченную
правку (случилось 11.09, коммит 341bdfb6 — разбор в SESSIONS.md, «Коммиты»).

Как работает: сравнивает рабочее дерево с HEAD, делит расхождения на блоки и
оставляет только те, где встречаются ТВОИ слова. Блок, где нашлись и твои, и
чужие слова, разбирается построчно. Изменённое содержимое кладётся прямо в
индекс через `git hash-object` + `git update-index` — РАБОЧЕЕ ДЕРЕВО НЕ
ТРОГАЕТСЯ, чужие правки остаются на диске как были.

    python3 stage_mine.py --repo /media/ilya/T714/Unity/Tavern-fresh \\
        --mine ворон,perch,CrowPerch --foreign камин,Fire,fireplace \\
        Assets/Modules/Grid/GridCursor.cs Assets/Game/UI/HudUI.cs

Дальше обычный `git commit` (без -a!) и ОБЯЗАТЕЛЬНО `git diff --cached` —
глазами найти в нём чужие слова. Скрипт помогает, но не отменяет проверку.
"""
import argparse, difflib, os, subprocess, sys


def head_lines(repo, path):
    out = subprocess.run(['git', 'show', 'HEAD:' + path], cwd=repo, capture_output=True, text=True)
    return out.stdout.splitlines(keepends=True) if out.returncode == 0 else []


def hit(line, words):
    return any(w and w in line for w in words)


def stage(repo, path, mine, foreign):
    head = head_lines(repo, path)
    work = open(os.path.join(repo, path), encoding='utf-8').readlines()
    blocks = difflib.SequenceMatcher(None, head, work, autojunk=False).get_opcodes()
    out, kept, skipped = [], 0, 0
    for tag, i1, i2, j1, j2 in blocks:
        old, new = head[i1:i2], work[j1:j2]
        if tag == 'equal':
            out.extend(old)
            continue
        is_mine = any(hit(l, mine) for l in old + new)
        is_foreign = any(hit(l, foreign) for l in old + new)
        if is_mine and not is_foreign:
            out.extend(new); kept += 1
        elif is_mine and is_foreign and tag == 'insert':
            out.extend(l for l in new if hit(l, mine) and not hit(l, foreign))
            kept += 1; skipped += 1
        else:
            out.extend(old); skipped += 1
    blob = subprocess.run(['git', 'hash-object', '-w', '--path', path, '--stdin'], cwd=repo,
                          input=''.join(out), capture_output=True, text=True).stdout.strip()
    subprocess.run(['git', 'update-index', '--add', '--cacheinfo', '100644,%s,%s' % (blob, path)],
                   cwd=repo, check=True)
    print('%s: своих блоков %d, чужих пропущено %d' % (path, kept, skipped))


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
