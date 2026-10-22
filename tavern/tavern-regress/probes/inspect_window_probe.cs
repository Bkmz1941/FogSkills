// 20.10 P1158: целиком по всем предметам одним вызовом уронила редактор (SIGSEGV в драйвере NVIDIA) — не больше 100 стендов
// за вызов, гонять частями: check_all.py (probe_cs_parts) или parts-копией с `_k++ % K`.
if (!UnityEngine.Application.isPlaying) return "не в play";
var F = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance;
var T = typeof(Tavern.UI.ItemPreview3D);
System.Func<object, string, object> Get = (o, f) => T.GetField(f, F).GetValue(o);
System.Action<object, string, object> Set = (o, f, v) => T.GetField(f, F).SetValue(o, v);
System.Action<object, string, object[]> Call = (o, f, a) => T.GetMethod(f, F).Invoke(o, a);
var sb = new System.Text.StringBuilder();
int n = 0, bad = 0, checks = 0;
bool cut = false;
var badIds = new System.Collections.Generic.Dictionary<string, int>();
System.Action<bool, string, string> Ok = (ok, code, id) =>
{
    checks++;
    if (ok) return;
    badIds[code] = badIds.TryGetValue(code, out var k) ? k + 1 : 1;
    if (badIds[code] <= 3) sb.Append("FAIL " + code + " " + id + "\n");
};
System.Func<UnityEngine.RectTransform, float, UnityEngine.Vector2> Cap = (r, s) =>
    r.anchoredPosition + (UnityEngine.Vector2)(r.localRotation * UnityEngine.Vector3.up) * s * (r.sizeDelta.y - r.sizeDelta.x) * 0.5f;
var holder = new UnityEngine.GameObject("InspectProbeHolder", typeof(UnityEngine.RectTransform));
((UnityEngine.RectTransform)holder.transform).sizeDelta = new UnityEngine.Vector2(640f, 480f);
var turns = new[] { new UnityEngine.Vector2(90f, 0f), new UnityEngine.Vector2(0f, 90f), new UnityEngine.Vector2(137f, -61f), new UnityEngine.Vector2(-45f, 180f), new UnityEngine.Vector2(33f, 271f) };
var pans = new[] { new UnityEngine.Vector3(0f, 9f, 0f), new UnityEngine.Vector3(0f, -9f, 0f), new UnityEngine.Vector3(9f, 0f, 0f), new UnityEngine.Vector3(-9f, 0f, 0f) };
try
{
    foreach (var def in Cozy.Grid.FurnitureCatalog.All())
    {
        if (def == null || string.IsNullOrEmpty(def.pickupItemId)) continue;
        if (n >= 100) { cut = true; break; }
        var p = Tavern.UI.ItemPreview3D.Attach((UnityEngine.RectTransform)holder.transform, def);
        if (p == null) continue;
        n++;
        try
        {
            var cam = (UnityEngine.Camera)Get(p, "_cam");
            var spin = (UnityEngine.Transform)Get(p, "_spin");
            var model = p.Model;
            var rends = model.GetComponentsInChildren<UnityEngine.Renderer>();
            Ok(holder.GetComponentInChildren<Tavern.UI.ItemPreview3D>() == p && cam.transform.parent.Find("ItemPreviewGrid") == null, "IN-S01", def.id);
            p.FitInside(UnityEngine.Mathf.Max(Tavern.UI.InventoryScreenUI.InspectLook.ArrowLeft, Tavern.UI.InventoryScreenUI.InspectLook.ArrowRight) + Tavern.UI.InventoryScreenUI.InspectLook.ArrowSize + Tavern.UI.InventoryScreenUI.InspectLook.ObjectGap,
                UnityEngine.Mathf.Max(Tavern.UI.InventoryScreenUI.InspectLook.ArrowTop, Tavern.UI.InventoryScreenUI.InspectLook.ArrowBottom) + Tavern.UI.InventoryScreenUI.InspectLook.ArrowSize + Tavern.UI.InventoryScreenUI.InspectLook.ObjectGap);
            p.SetGrid(0.35f, 1f, 1.6f);
            UnityEngine.Transform grid = null;
            foreach (var t in cam.transform.parent.GetComponentsInChildren<UnityEngine.Transform>()) if (t.name == "ItemPreviewGrid") grid = t;
            Ok(grid != null, "IN-G00", def.id);
            if (grid == null) continue;
            var camPos = cam.transform.position; var camRot = cam.transform.rotation;
            var gridPos = grid.position; var gridRot = grid.rotation;
            Ok(UnityEngine.Mathf.Abs(UnityEngine.Mathf.DeltaAngle(grid.eulerAngles.y, cam.transform.eulerAngles.y)) < 0.01f
               && UnityEngine.Mathf.Abs(UnityEngine.Mathf.DeltaAngle(grid.eulerAngles.x, 90f)) < 0.01f, "IN-G03", def.id);
            System.Action<string> Frame = stage =>
            {
                float near = cam.nearClipPlane, low = float.MaxValue;
                bool inFrame = true, front = true;
                foreach (var r in rends)
                {
                    if (r == null || !r.enabled || !r.gameObject.activeInHierarchy) continue;
                    var mf = r.GetComponent<UnityEngine.MeshFilter>();
                    var b = r is UnityEngine.SkinnedMeshRenderer sk ? sk.localBounds : mf != null && mf.sharedMesh != null ? mf.sharedMesh.bounds : r.localBounds;
                    for (int c = 0; c < 8; c++)
                    {
                        var w = r.transform.TransformPoint(new UnityEngine.Vector3((c & 1) == 0 ? b.min.x : b.max.x, (c & 2) == 0 ? b.min.y : b.max.y, (c & 4) == 0 ? b.min.z : b.max.z));
                        low = UnityEngine.Mathf.Min(low, w.y);
                        var v = cam.WorldToViewportPoint(w);
                        if (v.z <= near) front = false;
                        if (v.x < -0.001f || v.x > 1.001f || v.y < -0.001f || v.y > 1.001f) inFrame = false;
                    }
                }
                if (stage != "колесо вплотную") Ok(inFrame, "IN-F01 " + stage, def.id);
                Ok(front, "IN-F02 " + stage, def.id);
                Ok(low > grid.position.y + 1e-4f, "IN-G01 " + stage, def.id);
                Ok((cam.transform.position - camPos).sqrMagnitude < 1e-10f && UnityEngine.Quaternion.Angle(cam.transform.rotation, camRot) < 0.01f
                   && (grid.position - gridPos).sqrMagnitude < 1e-10f && UnityEngine.Quaternion.Angle(grid.rotation, gridRot) < 0.01f, "IN-G02 " + stage, def.id);
            };
            Frame("старт");
            if (spin != null)
            {
                float tilt0 = UnityEngine.Vector3.Angle(spin.up, UnityEngine.Vector3.up);
                Call(p, "Rotate", new object[] { new UnityEngine.Vector2(77f, 0f) });
                Ok(UnityEngine.Mathf.Abs(UnityEngine.Vector3.Angle(spin.up, UnityEngine.Vector3.up) - tilt0) < 0.05f, "IN-R02", def.id);
            }
            foreach (var t in turns) { Call(p, "Rotate", new object[] { t }); Frame("поворот"); }
            float fit = (float)Get(p, "_fitDist");
            Set(p, "_dist", fit * 0.01f);
            Set(p, "_dist", (float)T.GetMethod("ClampDist", F).Invoke(p, new object[] { fit * 0.01f }));
            Call(p, "PlaceCamera", new object[0]);
            Frame("колесо вплотную");
            foreach (var pan in pans)
            {
                Set(p, "_dist", (float)T.GetMethod("ClampDist", F).Invoke(p, new object[] { fit * 100f }));
                Set(p, "_pan", pan);
                Call(p, "ClampPan", new object[0]);
                Call(p, "PlaceCamera", new object[0]);
                Frame("отдалён и сдвинут");
                Set(p, "_dist", (float)Get(p, "_distRest"));
                Set(p, "_pan", pan);
                Call(p, "ClampPan", new object[0]);
                Call(p, "PlaceCamera", new object[0]);
                Frame("сдвинут");
            }
            p.ResetView();
            if (spin != null)
                Ok(UnityEngine.Quaternion.Angle(spin.rotation, (UnityEngine.Quaternion)Get(p, "_spinRest")) < 0.05f
                   && UnityEngine.Mathf.Abs(spin.localScale.x - (float)Get(p, "_fitDist") / (float)Get(p, "_distRest")) < 1e-4f && spin.localPosition.sqrMagnitude < 1e-10f, "IN-R01", def.id);
            Frame("вид по умолчанию");
        }
        finally { UnityEngine.Object.DestroyImmediate(p.gameObject); }
    }

    var canvasGo = new UnityEngine.GameObject("InspectProbeCanvas", typeof(UnityEngine.Canvas));
    try
    {
        var bars = new System.Collections.Generic.List<UnityEngine.RectTransform>();
        foreach (var left in new[] { true, false })
        {
            var btn = Tavern.UI.UiFactory.Chevron(canvasGo.transform, left, 34f, () => { });
            bars.Clear();
            foreach (UnityEngine.Transform c in btn.transform) bars.Add((UnityEngine.RectTransform)c);
            float join = float.MaxValue;
            foreach (var s1 in new[] { 1f, -1f }) foreach (var s2 in new[] { 1f, -1f })
                join = UnityEngine.Mathf.Min(join, (Cap(bars[0], s1) - Cap(bars[1], s2)).magnitude);
            Ok(bars.Count == 2 && join < 0.5f, "IN-U02", left ? "галка ‹" : "галка ›");
            float minX = float.MaxValue, maxX = float.MinValue, minY = float.MaxValue, maxY = float.MinValue;
            foreach (var r in bars) foreach (var s in new[] { 1f, -1f })
            {
                var c = Cap(r, s);
                float h = r.sizeDelta.x * 0.5f;
                minX = UnityEngine.Mathf.Min(minX, c.x - h); maxX = UnityEngine.Mathf.Max(maxX, c.x + h);
                minY = UnityEngine.Mathf.Min(minY, c.y - h); maxY = UnityEngine.Mathf.Max(maxY, c.y + h);
            }
            Ok(UnityEngine.Mathf.Abs(minX + maxX) < 0.5f && UnityEngine.Mathf.Abs(minY + maxY) < 0.5f, "IN-U03", left ? "галка ‹" : "галка ›");
        }
    }
    finally { UnityEngine.Object.DestroyImmediate(canvasGo); }
}
finally { UnityEngine.Object.DestroyImmediate(holder); }

foreach (var kv in badIds) bad += kv.Value;
var head = cut ? "НЕПОЛНОЕ: больше 100 стендов за вызов — гонять частями (check_all.py, P1158). " : "";
head += bad == 0 ? "ЗЕЛЁНОЕ из " + checks + " (предметов " + n + ")" : "КРАСНОЕ: " + bad + " из " + checks + " (предметов " + n + ")";
var sum = new System.Text.StringBuilder();
foreach (var kv in badIds) sum.Append(" " + kv.Key + "×" + kv.Value);
return head + sum + "\n" + sb;

