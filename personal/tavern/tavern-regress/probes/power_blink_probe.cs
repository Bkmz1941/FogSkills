// Моргание щитков (P1291): пробежка героя квадратом 3×3 м вокруг текущего места, хук PowerFeature.Toggled 3 с.
// Любой поставщик питания, переключившийся больше одного раза, — красное. Мостом: execute_code в play.
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I; var player = Cozy.Grid.PlayerRef.GameObject;
var startPos = player.transform.position; var startRot = player.transform.rotation;
var corners = new UnityEngine.Vector3[] { startPos + new UnityEngine.Vector3(-1.5f, 0f, -1.5f), startPos + new UnityEngine.Vector3(1.5f, 0f, -1.5f), startPos + new UnityEngine.Vector3(1.5f, 0f, 1.5f), startPos + new UnityEngine.Vector3(-1.5f, 0f, 1.5f) };
var counts = new System.Collections.Generic.Dictionary<string, int>();
float until = UnityEngine.Time.time + 3f; int seg = 0; float segT = 0f;
System.Action<Cozy.Grid.PowerFeature, Cozy.Grid.IFeatureHost> h = null;
h = (f, host) => { string k = (host != null ? host.DisplayName : "?") + "@" + (host is Cozy.Grid.InteractiveObject io ? io.transform.position.ToString("F1") : ""); int c; counts.TryGetValue(k, out c); counts[k] = c + 1; };
Cozy.Grid.PowerFeature.Toggled += h;
string outPath = "/tmp/power_blink.txt";
UnityEditor.EditorApplication.CallbackFunction mover = null;
mover = () =>
{
    if (!UnityEngine.Application.isPlaying || UnityEngine.Time.time > until)
    {
        UnityEditor.EditorApplication.update -= mover; Cozy.Grid.PowerFeature.Toggled -= h;
        gc.TeleportPlayerTo(startPos); player.transform.rotation = startRot;
        var sb = new System.Text.StringBuilder();
        bool bad = false;
        foreach (var kv in counts) { sb.AppendLine(kv.Key + " переключений " + kv.Value); if (kv.Value > 1) bad = true; }
        sb.AppendLine(bad ? "POWER_BLINK FAIL" : "POWER_BLINK ok (щитков с переключениями: " + counts.Count + ")");
        System.IO.File.WriteAllText(outPath, sb.ToString());
        return;
    }
    float dt = UnityEngine.Time.deltaTime > 0f ? UnityEngine.Time.deltaTime : 1f / 60f;
    var a = corners[seg]; var b = corners[(seg + 1) % 4];
    segT += 6.5f * dt / 3f; if (segT >= 1f) { segT -= 1f; seg = (seg + 1) % 4; a = corners[seg]; b = corners[(seg + 1) % 4]; }
    var p = UnityEngine.Vector3.Lerp(a, b, segT); p.y = startPos.y; player.transform.position = p; UnityEngine.Physics.SyncTransforms();
};
UnityEditor.EditorApplication.update += mover;
return "запущено на 3 с, итог в " + outPath;
