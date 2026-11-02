"""Снимок каталога объектов для генератора домов: id, имя, категория, крепление, класс размера, якорь,
флаги и ГАБАРИТЫ (bounds рендереров объекта, собранного без поворота на y = −80 и снесённого в том же вызове).

python3 catalog_dump.py            снять каталог мостом (нужен play) → catalog.json рядом
python3 catalog_dump.py --show id  показать запись

Оси объекта (как у постановки): ширина — X, глубина — Z, спина объекта смотрит в +Z (yaw 0 → +Z, 90 → +X).
cx/cz — смещение центра габарита от корня, y0 — низ габарита от корня.
"""
import json, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
MCP = str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
OUT = HERE / 'catalog.json'
BATCH = 100

CODE = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var all = Cozy.Grid.FurnitureCatalog.All();
var sb = new System.Text.StringBuilder();
int from = __FROM__, to = System.Math.Min(__TO__, all.Length);
sb.Append("TOTAL\t").Append(all.Length).Append('\n');
for (int i = from; i < to; i++) {
  var def = all[i]; if (def == null || string.IsNullOrEmpty(def.id)) continue;
  UnityEngine.GameObject body = null;
  try {
    body = new UnityEngine.GameObject("HouseCatalogProbe");
    body.transform.position = new UnityEngine.Vector3(0f, -80f, 0f);
    var io = body.AddComponent<Cozy.Grid.InteractiveObject>();
    io.Build(def);
    var rs = body.GetComponentsInChildren<UnityEngine.Renderer>(false);
    UnityEngine.Bounds b = default(UnityEngine.Bounds); bool any = false;
    foreach (var r in rs) { if (r is UnityEngine.ParticleSystemRenderer || !r.enabled) continue; if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds); }
    var root = body.transform.position;
    sb.Append(def.id).Append('\t').Append(def.displayName).Append('\t').Append(def.category ?? "").Append('\t').Append(def.mount).Append('\t').Append(def.size).Append('\t').Append(def.anchor)
      .Append('\t').Append(def.freePlace ? 1 : 0).Append('\t').Append(def.hostOnly ? 1 : 0).Append('\t').Append(def.snapToId ?? "").Append('\t').Append(def.kit ?? "").Append('\t').Append(def.outdoorOnly ? 1 : 0).Append('\t').Append(def.isProduct ? 1 : 0).Append('\t').Append(def.resourceFolder ?? "").Append('\t').Append(def.weightKg.ToString("0.##"))
      .Append('\t').Append(any ? b.size.x.ToString("0.000") : "").Append('\t').Append(any ? b.size.z.ToString("0.000") : "").Append('\t').Append(any ? b.size.y.ToString("0.000") : "")
      .Append('\t').Append(any ? (b.center.x - root.x).ToString("0.000") : "").Append('\t').Append(any ? (b.min.y - root.y).ToString("0.000") : "").Append('\t').Append(any ? (b.center.z - root.z).ToString("0.000") : "")
      .Append('\t').Append(def.cellFill.ToString("0.00")).Append('\t').Append(def.lightRange.ToString("0.##")).Append('\t').Append(def.openable ? 1 : 0).Append('\t').Append(def.ridesOnId ?? "").Append('\t').Append(def.spawnWith ?? "").Append('\t').Append(def.modelName ?? "").Append('\t').Append(def.cladCut).Append('\t').Append(def.plinthStop ? 1 : 0).Append('\t').Append(def.plinthBehind ? 1 : 0).Append('\t').Append(def.seatToWall ? 1 : 0).Append('\t').Append(def.resizable ? 1 : 0).Append('\t').Append(def.wallHeight.ToString("0.00")).Append('\t').Append(def.cornerModule ? 1 : 0).Append('\t').Append(def.seatSideToWall ? 1 : 0).Append('\t').Append(def.switchesRoom ? 1 : 0).Append('\t').Append(def.sizeDMin.ToString("0.00")).Append('\t').Append(def.sizeDMax.ToString("0.00")).Append('\t').Append(def.sizeMin.ToString("0.00")).Append('\t').Append(def.sizeMax.ToString("0.00"))
      .Append('\n');
  } catch (System.Exception e) { sb.Append(def.id).Append("\tERR ").Append(e.Message.Replace('\n', ' ')).Append('\n'); }
  finally { if (body != null) UnityEngine.Object.DestroyImmediate(body); }
}
return sb.ToString();
'''
COLS = ['id', 'name', 'category', 'mount', 'size', 'anchor', 'free', 'host_only', 'snap_to', 'kit', 'outdoor', 'product', 'folder', 'weight',
        'w', 'd', 'h', 'cx', 'y0', 'cz', 'cell_fill', 'light', 'openable', 'rides_on', 'spawn_with', 'model', 'clad_cut', 'plinth_stop', 'plinth_behind', 'seat_to_wall', 'resizable', 'wall_height', 'corner', 'side_to_wall', 'switches_room', 'd_min', 'd_max', 'w_min', 'w_max']
NUM = {'w', 'd', 'h', 'cx', 'y0', 'cz', 'cell_fill', 'light', 'weight', 'wall_height', 'd_min', 'd_max', 'w_min', 'w_max'}
INT = {'free', 'host_only', 'outdoor', 'product', 'openable', 'plinth_stop', 'plinth_behind', 'seat_to_wall', 'resizable', 'corner', 'side_to_wall', 'switches_room'}


def run(code):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})],
                         capture_output=True, text=True, timeout=600, cwd=PROJECT)
    text = out.stdout.strip()
    line = text.splitlines()[-1] if text else '{}'
    d = json.loads(line)
    return (d.get('data') or {}).get('result') or d.get('message') or ''


def dump():
    items, errors, total, start = {}, [], None, 0
    while True:
        res = run(CODE.replace("__FROM__", str(start)).replace("__TO__", str(start + BATCH)))
        if res.startswith('не в play'): raise SystemExit(res)
        for line in res.split('\n'):
            if not line.strip(): continue
            parts = line.split('\t')
            if parts[0] == 'TOTAL': total = int(parts[1]); continue
            if len(parts) > 1 and parts[1].startswith('ERR'): errors.append((parts[0], parts[1])); continue
            rec = {}
            for k, v in zip(COLS, parts):
                if k in NUM: rec[k] = float(v) if v != '' else None
                elif k in INT: rec[k] = v == '1'
                else: rec[k] = v
            items[rec['id']] = rec
        print('снято %d..%d, всего %s, записей %d, ошибок %d' % (start, start + BATCH, total, len(items), len(errors)), flush=True)
        start += BATCH
        if total is None or start >= total: break
    OUT.write_text(json.dumps({'items': items, 'errors': errors}, ensure_ascii=False, indent=1))
    print('записан', OUT, '—', len(items), 'объектов; ошибки:', errors[:10])


def main():
    if '--show' in sys.argv:
        cat = json.loads(OUT.read_text())['items']
        for oid in sys.argv[sys.argv.index('--show') + 1:]:
            print(json.dumps(cat.get(oid), ensure_ascii=False))
        return
    dump()


if __name__ == '__main__':
    main()
