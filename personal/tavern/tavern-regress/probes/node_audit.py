import json, subprocess, sys

CODE = r'''
var defs = Cozy.Grid.FurnitureCatalog.All();
var report = new System.Text.StringBuilder();
int withModel = 0, noModel = 0, bad = 0;
foreach (var d in defs)
{
    if (string.IsNullOrEmpty(d.modelName)) continue;
    var path = (string.IsNullOrEmpty(d.resourceFolder) ? "Furniture" : d.resourceFolder) + "/" + d.modelName;
    var go = UnityEngine.Resources.Load<UnityEngine.GameObject>(path);
    if (go == null) { noModel++; continue; }
    withModel++;
    var names = new System.Collections.Generic.HashSet<string>();
    foreach (var t in go.GetComponentsInChildren<UnityEngine.Transform>(true)) names.Add(t.name);
    foreach (var slot in d.slots) if (!string.IsNullOrEmpty(slot.node)) names.Add("Slot_" + slot.node);
    var pairs = new System.Collections.Generic.List<string>();
    var stack = new System.Collections.Generic.Stack<object>();
    var seen = new System.Collections.Generic.HashSet<object>();
    stack.Push(d);
    int guard = 0;
    while (stack.Count > 0 && guard++ < 400)
    {
        var o = stack.Pop();
        if (o == null || !seen.Add(o)) continue;
        var tp = o.GetType();
        foreach (var f in tp.GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance))
        {
            var v = f.GetValue(o);
            if (v == null) continue;
            var lower = f.Name.ToLower();
            if (f.FieldType == typeof(string))
            {
                if (!lower.EndsWith("node") && !lower.EndsWith("nodes")) continue;
                var s = ((string)v).Trim();
                if (s.Length == 0) continue;
                if (f.Name == "liquidNode" && d.capacityL <= 0f) continue;
                if (f.Name == "snapToNode") continue;
                foreach (var part in s.Split(',', ' ', ';', ':'))
                {
                    var p = part.Trim();
                    if (p.Length == 0) continue;
                    if (names.Contains(p)) continue;
                    if (f.Name == "countNodes")
                    {
                        var prefixed = false;
                        foreach (var n in names) if (n.StartsWith(p)) { prefixed = true; break; }
                        if (prefixed) continue;
                    }
                    pairs.Add(f.Name + "=" + p);
                }
                continue;
            }
            if (f.FieldType.IsPrimitive || f.FieldType.IsEnum) continue;
            var ie = v as System.Collections.IEnumerable;
            if (ie != null) { foreach (var item in ie) if (item != null && item.GetType().FullName.StartsWith("Cozy")) stack.Push(item); continue; }
            if (f.FieldType.FullName.StartsWith("Cozy")) stack.Push(v);
        }
    }
    if (!string.IsNullOrEmpty(d.snapToNode) && !string.IsNullOrEmpty(d.snapToId))
    {
        foreach (var hostId in d.snapToId.Split(','))
        {
        var host = Cozy.Grid.FurnitureCatalog.ById(hostId.Trim());
        if (host == null) { pairs.Add("snapToId=" + hostId + " (хозяина нет в каталоге)"); continue; }
        {
            var hostGo = UnityEngine.Resources.Load<UnityEngine.GameObject>((string.IsNullOrEmpty(host.resourceFolder) ? "Furniture" : host.resourceFolder) + "/" + host.modelName);
            if (hostGo != null)
            {
                var found = false;
                foreach (var t in hostGo.GetComponentsInChildren<UnityEngine.Transform>(true)) if (t.name == d.snapToNode) { found = true; break; }
                if (!found) pairs.Add("snapToNode=" + d.snapToNode + " (нет у хозяина " + hostId + ")");
            }
        }
        }
    }
    if (pairs.Count > 0)
    {
        bad++;
        report.Append(d.id + ": " + string.Join(", ", pairs.ToArray()) + " | ");
    }
}
return "дефов с моделью=" + withModel + " без загруженной модели=" + noModel + " с отсутствующими нодами=" + bad + " :: " + report.ToString();
'''

out = subprocess.run(['python3','/home/ilya/.claude/skills/tavern-game/mcp_call.py','execute_code',
                      json.dumps({"action":"execute","code":CODE})],capture_output=True,text=True,timeout=280)
line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else out.stderr[-400:]
try:
    d = json.loads(line)
    print(d.get("data",{}).get("result") or json.dumps(d, ensure_ascii=False)[:1500])
except Exception:
    print(line[:1500])
