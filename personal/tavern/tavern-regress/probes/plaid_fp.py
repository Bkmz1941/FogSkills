"""Характеризующий отпечаток ткани пледов и кружевных скатертей (ночь 01→02.11, ilya-e9).
Для каждого `PlaidCloth` на уровне заново укладывает ткань (`Drape()`, детерминированная верле-симуляция
по коллайдерам и мешам без коллайдера) и печатает хозяина, позицию и SHA1 вершин меша.
Рефакторинг `PlaidCloth` обязан дать те же строки.

python3 plaid_fp.py <out.txt>      снять (нужен play, ткань уже лежит)
python3 plaid_fp.py --diff a.txt b.txt
"""
import json, pathlib, subprocess, sys

MCP = str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'

CODE = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var sb = new System.Text.StringBuilder();
var sha = System.Security.Cryptography.SHA1.Create();
var list = new System.Collections.Generic.List<Cozy.Grid.PlaidCloth>(UnityEngine.Object.FindObjectsByType<Cozy.Grid.PlaidCloth>(UnityEngine.FindObjectsSortMode.None));
list.Sort((a, b) => string.CompareOrdinal(a.transform.position.ToString("F3") + a.name, b.transform.position.ToString("F3") + b.name));
foreach (var pc in list) {
  var mf = pc.GetComponent<UnityEngine.MeshFilter>();
  if (mf == null || mf.sharedMesh == null) continue;
  pc.Drape();
  var v = mf.sharedMesh.vertices;
  var bytes = new byte[v.Length * 12];
  for (int i = 0; i < v.Length; i++) {
    System.Buffer.BlockCopy(System.BitConverter.GetBytes(v[i].x), 0, bytes, i * 12, 4);
    System.Buffer.BlockCopy(System.BitConverter.GetBytes(v[i].y), 0, bytes, i * 12 + 4, 4);
    System.Buffer.BlockCopy(System.BitConverter.GetBytes(v[i].z), 0, bytes, i * 12 + 8, 4);
  }
  var h = System.BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
  var io = pc.GetComponentInParent<Cozy.Grid.InteractiveObject>();
  var b = mf.GetComponent<UnityEngine.Renderer>().bounds;
  sb.Append(io != null && io.Def != null ? io.Def.id : pc.name).Append('\t').Append(pc.transform.position.ToString("F3"))
    .Append('\t').Append(v.Length).Append('\t').Append(b.size.ToString("F3")).Append('\t').Append(h).Append('\n');
}
return sb.Length == 0 ? "пледов нет" : sb.ToString();
'''


def run(code):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})],
                         capture_output=True, text=True, timeout=600, cwd=PROJECT)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    d = json.loads(line)
    if not d.get('success'):
        sys.exit('мост: ' + json.dumps(d, ensure_ascii=False)[:1200])
    return (d.get('data') or {}).get('result') or ''


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == '--diff':
        a = pathlib.Path(sys.argv[2]).read_text().splitlines()
        b = pathlib.Path(sys.argv[3]).read_text().splitlines()
        bad = [(x, y) for x, y in zip(a, b) if x != y] + [(x, '—') for x in a[len(b):]] + [('—', y) for y in b[len(a):]]
        for x, y in bad:
            print('%s\n  -> %s' % (x, y))
        print('разошлось: %d из %d' % (len(bad), max(len(a), len(b))))
        sys.exit(1 if bad else 0)
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    text = run(CODE)
    pathlib.Path(sys.argv[1]).write_text(text if text.endswith('\n') else text + '\n')
    print(text.strip())


if __name__ == '__main__':
    main()
