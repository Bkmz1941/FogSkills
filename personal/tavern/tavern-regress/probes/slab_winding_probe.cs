// Проба P926 / инвариант 510 (05.10): у строительных мешей (GridCursorMouse, Roofs) треугольники
// обходятся вдоль своей нормали, как у PrimitiveType.Cube. Вывернутый низ плиты не даёт тени лампам
// этажом ниже — свет идёт сквозь перекрытие. Ожидание: строки PendingBlock в выводе нет.
// RoofField — дуги со сглаженными нормалями, единичные BAD там допустимы.
var seen = new System.Collections.Generic.Dictionary<Mesh, string>();
var byName = new System.Collections.Generic.Dictionary<string, int[]>();
foreach (var mf in UnityEngine.Object.FindObjectsByType<MeshFilter>(FindObjectsSortMode.None))
{
    var root = mf.transform.root.name;
    if (root != "GridCursorMouse" && root != "Roofs") continue;
    var m = mf.sharedMesh; if (m == null || !m.isReadable) continue;
    var key = mf.name + "/" + (mf.transform.parent ? mf.transform.parent.name : "");
    if (!byName.TryGetValue(key, out var acc)) { acc = new int[3]; byName[key] = acc; }
    acc[2]++;
    if (seen.ContainsKey(m)) continue; seen[m] = key;
    var v = m.vertices; var n = m.normals; if (n == null || n.Length == 0) continue;
    for (int s = 0; s < m.subMeshCount; s++) { var t = m.GetTriangles(s);
      for (int i = 0; i < t.Length; i += 3) { var cr = Vector3.Cross(v[t[i+1]] - v[t[i]], v[t[i+2]] - v[t[i]]); if (cr.sqrMagnitude < 1e-12f) continue;
        var nn = n[t[i]] + n[t[i+1]] + n[t[i+2]]; if (Vector3.Dot(cr, nn) < 0) acc[1]++; else acc[0]++; } }
}
var sb = new System.Text.StringBuilder();
foreach (var kv in byName) if (kv.Value[1] > 0) sb.Append(kv.Key + " ok=" + kv.Value[0] + " BAD=" + kv.Value[1] + " renderers=" + kv.Value[2] + "\n");
return sb.Length == 0 ? "all ok, meshes=" + seen.Count : sb.ToString();
