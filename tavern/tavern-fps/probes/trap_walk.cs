var pl = UnityEngine.GameObject.FindWithTag("Player").transform;
var cc = pl.GetComponent<UnityEngine.CharacterController>();
Cozy.Grid.GridCursor.I.TeleportPlayerTo(new UnityEngine.Vector3(-70.45f, 0.98f, -40f));
float t0 = UnityEngine.Time.realtimeSinceStartup, last = t0; float dur = 40f;
var outs = new System.Collections.Generic.List<float>(); var ins = new System.Collections.Generic.List<float>();
var slow = new System.Collections.Generic.List<string>();
int lastTiles = 0, lastRev = Cozy.Grid.InteractiveObject.AllRevision; float trapAt = -1;
UnityEngine.Events.UnityAction act = null;
act = () => {
  float now = UnityEngine.Time.realtimeSinceStartup; float dt = (now - last) * 1000f; last = now; float t = now - t0;
  if (pl == null) { UnityEngine.Application.onBeforeRender -= act; return; }
  bool tr = Cozy.Effects.FogTrap.Trapped; if (tr && trapAt < 0) trapAt = t;
  int tiles = 0; int dTiles = tiles - lastTiles; lastTiles = tiles;
  int rev = Cozy.Grid.InteractiveObject.AllRevision; int dRev = rev - lastRev; lastRev = rev;
  if (t > 1f) { (tr ? ins : outs).Add(dt); if (dt > 25f) slow.Add(string.Format("{0:0.0}s {1:0}ms tr={2} tiles+{3} rev+{4} y={5:0.0}", t, dt, tr ? 1 : 0, dTiles, dRev, pl.position.y)); }
  if (t > dur) {
    UnityEngine.Application.onBeforeRender -= act;
    System.Func<System.Collections.Generic.List<float>, string> st = l => { if (l.Count == 0) return "нет"; var c = new System.Collections.Generic.List<float>(l); c.Sort(); float s = 0; foreach (var x in c) s += x; return string.Format("кадров={0} сред={1:0.0} мед={2:0.0} p95={3:0.0} макс={4:0} >25мс={5}", c.Count, s / c.Count, c[c.Count / 2], c[(int)(c.Count * 0.95f)], c[c.Count - 1], c.FindAll(x => x > 25f).Count); };
    
    string res = "trapAt=" + trapAt.ToString("0.0") + "s y=" + pl.position.y.ToString("0.0") + "\nдо ловушки: " + st(outs) + "\nв ловушке: " + st(ins) + "\n";
    System.IO.File.WriteAllText("__OUT__", res + string.Join("\n", slow.GetRange(System.Math.Max(0, slow.Count-40), System.Math.Min(40, slow.Count)).ToArray()));
    return;
  }
  var step = new UnityEngine.Vector3(0f, -0.5f * UnityEngine.Time.deltaTime, -4.5f * UnityEngine.Time.deltaTime);
  if (cc != null && cc.enabled) cc.Move(step);
};
UnityEngine.Application.onBeforeRender += act;
return "walking from " + pl.position.ToString("F1");
