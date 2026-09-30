"""Сверка двух отпечатков срезов стен (`cutaway_state.cs`) по СОСТОЯНИЮ, а не по md5:
после перезагрузки уровня `col.along` и центры плинтуса на сантиметр плавают на одном
и том же коде (26.09). Сравниваются: флаг «выше этажа», флаги колонок (fulls/cut/hidden)
и набор полных рендереров с enabled/тенями — без координат.

python3 cutaway_compare.py cutaway_a.txt cutaway_b.txt
"""
import re, sys
from collections import Counter


def norm(path):
    out = []
    for line in open(path):
        line = re.sub(r' along=-?\d+\.\d+', '', line)
        rends = tuple(sorted(re.findall(r'(\w+)@\([^)]*\):(on|off)/(\w+)', line)))
        flags = tuple(sorted(re.findall(r'fulls=(\w+) cut=(\w+) hidden=(\w+)', line)))
        above = re.search(r'above=(\w+)', line).group(1)
        out.append((above, flags, rends))
    return sorted(out)


a, b = norm(sys.argv[1]), norm(sys.argv[2])
print('run\'ов', len(a), len(b), 'совпало:', a == b)
if a != b:
    ca, cb = Counter(a), Counter(b)
    for k in (ca - cb).elements(): print(' только в первом:', k[:2], len(k[2]), 'рендереров')
    for k in (cb - ca).elements(): print(' только во втором:', k[:2], len(k[2]), 'рендереров')
sys.exit(0 if a == b else 1)
