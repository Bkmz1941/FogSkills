"""Характеризующий отпечаток каталога дефов (ночь 01→02.11, ilya-e9): каждый `ObjectDef` из
`FurnitureCatalog.All()` и каждый `ItemDef` из `Items.All()` → `JsonUtility.ToJson` → SHA1.
Рефакторинг каталога (хелперы, свёртка повторов) обязан дать байт-в-байт тот же список.

python3 defs_fp.py <out.txt>          снять отпечаток мостом (редактор, play не обязателен) → строки «вид:id<TAB>sha1<TAB>длина»
python3 defs_fp.py --show obj:<id>    показать JSON одного дефа (или item:<id>) — чтобы понять, чем разошлись
python3 defs_fp.py --diff a.txt b.txt   разница двух отпечатков по id

Ссылки на UnityEngine.Object внутри дефа сериализуются как instanceID и гуляют между запусками —
перед хешем они обнуляются (`"instanceID":N` → `"instanceID":0`).
⚠️ Шесть светящихся дефов (home_tv, lamp_ceiling_modern, lamp_fairy_curtain, lamp_lantern_string, lamp_pendant_lantern,
lamp_wall_garland) дают разный хеш в play и вне play — оба снимка снимать в одном режиме (02.11).
"""
import json, pathlib, subprocess, sys

MCP = str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
BATCH = 120

CODE = r'''
var sb = new System.Text.StringBuilder();
var sha = System.Security.Cryptography.SHA1.Create();
var rx = new System.Text.RegularExpressions.Regex("\"instanceID\":-?\\d+");
System.Func<UnityEngine.Object, string> fp = o => {
  string js = rx.Replace(UnityEngine.JsonUtility.ToJson(o), "\"instanceID\":0");
  var h = sha.ComputeHash(System.Text.Encoding.UTF8.GetBytes(js));
  return System.BitConverter.ToString(h).Replace("-", "").ToLowerInvariant() + "\t" + js.Length;
};
var objs = Cozy.Grid.FurnitureCatalog.All();
var items = Cozy.Grid.Items.All();
int n = objs.Length + items.Length;
int from = __FROM__, to = System.Math.Min(__TO__, n);
sb.Append("TOTAL\t").Append(n).Append('\n');
for (int i = from; i < to; i++) {
  if (i < objs.Length) { var d = objs[i]; if (d == null) continue; sb.Append("obj:").Append(d.id).Append('\t').Append(fp(d)).Append('\n'); }
  else { var d = items[i - objs.Length]; if (d == null) continue; sb.Append("item:").Append(d.id).Append('\t').Append(fp(d)).Append('\n'); }
}
return sb.ToString();
'''

SHOW = r'''
string want = "__ID__";
UnityEngine.Object found = null;
if (want.StartsWith("obj:")) { foreach (var d in Cozy.Grid.FurnitureCatalog.All()) if (d != null && d.id == want.Substring(4)) { found = d; break; } }
else { foreach (var d in Cozy.Grid.Items.All()) if (d != null && d.id == want.Substring(5)) { found = d; break; } }
return found == null ? "нет такого дефа" : UnityEngine.JsonUtility.ToJson(found, true);
'''


def run(code):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})],
                         capture_output=True, text=True, timeout=600, cwd=PROJECT)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    try:
        d = json.loads(line)
    except Exception:
        sys.exit('мост не ответил: ' + out.stdout[-400:] + out.stderr[-400:])
    if not d.get('success'):
        sys.exit('мост: ' + json.dumps(d, ensure_ascii=False)[:1200])
    return (d.get('data') or {}).get('result') or ''


def snapshot():
    rows = {}
    total = None
    start = 0
    while True:
        text = run(CODE.replace('__FROM__', str(start)).replace('__TO__', str(start + BATCH)))
        for line in text.splitlines():
            if line.startswith('TOTAL\t'):
                total = int(line.split('\t')[1])
                continue
            key, rest = line.split('\t', 1)
            rows[key] = rest
        start += BATCH
        if total is None or start >= total:
            break
    return rows, total


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == '--show':
        print(run(SHOW.replace('__ID__', sys.argv[2])))
        return
    if len(sys.argv) >= 4 and sys.argv[1] == '--diff':
        a = dict(l.split('\t', 1) for l in pathlib.Path(sys.argv[2]).read_text().splitlines() if '\t' in l)
        b = dict(l.split('\t', 1) for l in pathlib.Path(sys.argv[3]).read_text().splitlines() if '\t' in l)
        bad = 0
        for k in sorted(set(a) | set(b)):
            if a.get(k) != b.get(k):
                bad += 1
                print('%s: %s -> %s' % (k, a.get(k, '—'), b.get(k, '—')))
        print('разошлось: %d из %d' % (bad, len(set(a) | set(b))))
        sys.exit(1 if bad else 0)
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    rows, total = snapshot()
    out = pathlib.Path(sys.argv[1])
    out.write_text('\n'.join('%s\t%s' % (k, rows[k]) for k in sorted(rows)) + '\n')
    print('дефов %d (объектов и предметов в каталогах %s) → %s' % (len(rows), total, out))


if __name__ == '__main__':
    main()
