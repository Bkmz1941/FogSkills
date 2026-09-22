"""Характеризующий замер wall-run'ов: отпечаток run'ов среза стен, угловых столбиков и кусков плинтуса
на открытом уровне — защита `GridCursor.RebuildWallRuns` и `BuildCornerPosts` при рефакторинге.

python3 wallruns_probe.py [метка]   печатает счётчики и md5 отпечатка; с меткой пишет полный отпечаток
                                   рядом (wallruns_<метка>.txt) для построчного диффа ДО/ПОСЛЕ

Порядок: снять ДО правки (`before`), после stop → компиляция → play снять ПОСЛЕ (`after`),
`diff` файлов пуст и md5 совпал — поведение то же. Ночь 22→23.09: level1 даёт 17 run'ов и
95 кусков плинтуса, столбиков 0 — `BuildCornerPosts` этим уровнем НЕ защищён.
"""
import hashlib, json, os, subprocess, sys

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'
OUT = os.environ.get('WALLRUNS_OUT', '/tmp')

CODE = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var lines = new System.Collections.Generic.List<string>();
int runs = 0, corners = 0, plinths = 0, rends = 0;
foreach (var wc in Cozy.Grid.WallCutaway.All)
{
    if (wc == null) continue;
    runs++;
    var names = new System.Collections.Generic.List<string>();
    foreach (var r in wc.GetComponentsInChildren<UnityEngine.Renderer>(true)) { rends++; names.Add(r.name + "@" + r.bounds.center.ToString("F2") + "#" + r.bounds.size.ToString("F2")); }
    foreach (var r in wc.Fulls) if (r != null) names.Add("full:" + r.name + "@" + r.bounds.center.ToString("F2") + "#" + r.bounds.size.ToString("F2"));
    names.Sort(string.CompareOrdinal);
    lines.Add("WALLRUN " + wc.transform.position.ToString("F2") + " " + string.Join(";", names));
}
foreach (var c in Cozy.Grid.WallCorner.All)
{
    if (c == null) continue;
    corners++;
    var r = c.GetComponent<UnityEngine.Renderer>();
    lines.Add("CORNER " + c.transform.position.ToString("F2") + " " + (r != null ? r.bounds.size.ToString("F2") : "-"));
}
foreach (var p in Cozy.Grid.PlinthPiece.All)
{
    if (p == null || p.Rend == null) continue;
    plinths++;
    lines.Add("PLINTH " + p.face + " " + p.span + " " + p.Rend.bounds.min.ToString("F2") + " " + p.Rend.bounds.max.ToString("F2"));
}
lines.Sort(string.CompareOrdinal);
return "runs=" + runs + " renderers=" + rends + " corners=" + corners + " plinths=" + plinths + "\n" + string.Join("\n", lines);
'''


def main():
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": CODE})],
                         capture_output=True, text=True, timeout=300)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ''
    try:
        res = (json.loads(line).get('data') or {}).get('result')
    except Exception:
        res = None
    if not res:
        print('wallruns: мост не ответил —', (line or out.stderr)[:300]); sys.exit(1)
    head, _, body = res.partition('\n')
    digest = hashlib.md5(body.encode()).hexdigest()[:12]
    print(head + ' md5=' + digest)
    if len(sys.argv) > 1:
        path = os.path.join(OUT, 'wallruns_%s.txt' % sys.argv[1])
        open(path, 'w').write(body + '\n')
        print('отпечаток:', path, '(%d строк)' % (body.count('\n') + 1))


if __name__ == '__main__':
    main()
