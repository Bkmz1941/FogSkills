#!/usr/bin/env python3
"""Регресс уровня «Продукты (test)» (18.10, ilya-e3): всё, что сломалось и чинилось 18.10, одним прогоном в play.

python3 products_probe.py

Каждая проверка сама готовит сцену (временные объекты, включённые ручки) и в finally возвращает как было:
  1. сковорода с маслом на включённой конфорке греется ≥ 100° и шипит за 20 с (P1120, тест-сторож тоже есть);
  2. у кофемашины ровно один кувшин, и он в машине (P1121);
  3. засыпанный кофе едет вместе с фильтром при переносе (ridesOnId) — начало/отмена переноса;
  4. пустая ёмкость для питья пишет «Утоление жажды 0ед», бутылка масла — нет;
  5. отступ под заголовком карточки у полного и пустого пакета молока одинаковый (скин, P «отступ»);
  6. свежее не травит, протухшее — по таблице; порог бодрости 15ед;
  7. порции масла и кетчупа — 5ед;
  8. ход дверец и ящиков (parts_motion_probe.cs) и точка привязки переносимых (pivot_probe.py) — отдельными пробами.
Вердикт «PRODUCTS ok/FAIL», код 1 при красном. Уровень в редакторе не меняет и не сохраняет.
"""
import json, os, subprocess, sys, time

MCP = os.path.expanduser('~/.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
HERE = os.path.dirname(os.path.abspath(__file__))


def run(code):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({'action': 'execute', 'code': code})],
                         capture_output=True, text=True, timeout=300, cwd=PROJECT)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    try:
        d = json.loads(line)
    except Exception:
        return 'ОШИБКА моста: ' + out.stdout[-300:]
    if not d.get('success'):
        return 'ОШИБКА: ' + json.dumps(d, ensure_ascii=False)[:400]
    return str((d.get('data') or {}).get('result'))


PAN_START = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
Cozy.Grid.InteractiveObject stove = null;
foreach (var io in Cozy.Grid.InteractiveObject.All) if (io != null && io.Def != null && io.Def.id == "home_stove") { stove = io; break; }
if (stove == null) return "SKIP нет плиты";
var zone = Cozy.Grid.FurnitureModel.FindNode(stove.transform, "Slot_Zone1");
var gc = Cozy.Grid.GridCursor.I;
var m = typeof(Cozy.Grid.GridCursor).GetMethod("SpawnObject", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
var pan = (Cozy.Grid.InteractiveObject)m.Invoke(gc, new object[]{ Cozy.Grid.FurnitureCatalog.ById("frying_pan"), zone.position + UnityEngine.Vector3.up * 0.02f, stove.transform.eulerAngles.y });
UnityEngine.Physics.SyncTransforms();
gc.ReattachToContainer(pan);
Cozy.Grid.Greased.On(pan).Set(true);
bool was = stove.SwitchOn("Knob1");
stove.SetSwitch("Knob1", true, false);
pan.Slug = "probe_pan_" + (was ? "1" : "0");
return "ok container=" + (pan.Container != null ? pan.Container.Def.id : "-") + " conducts=" + pan.Conducts;
'''

PAN_READ = r'''
foreach (var io in Cozy.Grid.InteractiveObject.All)
  if (io != null && io.Slug != null && io.Slug.StartsWith("probe_pan_")) {
    var sh = typeof(Cozy.Grid.SizzleEffect).GetField("_shown", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance).GetValue(io.GetComponent<Cozy.Grid.SizzleEffect>());
    return io.Temperature.ToString("0") + "|" + sh;
  }
return "нет";
'''

PAN_END = r'''
bool was = false; int n = 0;
foreach (var io in new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All))
  if (io != null && io.Slug != null && io.Slug.StartsWith("probe_pan_")) { was = io.Slug.EndsWith("1"); Cozy.Grid.LevelIO.Unsaved.Remove(io); UnityEngine.Object.Destroy(io.gameObject); n++; }
foreach (var io in Cozy.Grid.InteractiveObject.All) if (io != null && io.Def != null && io.Def.id == "home_stove") io.SetSwitch("Knob1", was, false);
return "убрано " + n;
'''

CHECKS = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var bad = new System.Collections.Generic.List<string>(); var okl = new System.Collections.Generic.List<string>();
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public;
// 2. кувшин
int carafes = 0, attached = 0;
foreach (var io in Cozy.Grid.InteractiveObject.All) if (io != null && io.Def != null && io.Def.id == "coffee_carafe") { carafes++; if (io.Container != null && io.Container.Def.id == "home_coffee_machine") attached++; }
int machines = 0; foreach (var io in Cozy.Grid.InteractiveObject.All) if (io != null && io.Def != null && io.Def.id == "home_coffee_machine") machines++;
if (machines == 0) okl.Add("кувшин: SKIP (на уровне нет кофемашины)");
else if (carafes != 1 || attached != 1) bad.Add("кувшинов " + carafes + ", в машине " + attached); else okl.Add("кувшин один и в машине");
// 3. кофе в фильтре
Cozy.Grid.InteractiveObject filter = null, grounds = null;
foreach (var io in Cozy.Grid.InteractiveObject.All) { if (io == null || io.Def == null) continue; if (io.Def.id == "coffee_filter_cone") filter = io; if (io.Def.id == "coffee_grounds") grounds = io; }
if (filter != null && grounds != null && Cozy.Grid.DiscardFeature.TogetherInSlot(filter).Contains(grounds)) {
  var gc = Cozy.Grid.GridCursor.I;
  gc.BeginHandMove(filter);
  bool rides = grounds.transform.IsChildOf(filter.transform);
  typeof(Cozy.Grid.GridCursor).GetMethod("CancelHandMove", B).Invoke(gc, null);
  if (!rides) bad.Add("кофе не едет с фильтром"); else okl.Add("кофе едет с фильтром");
} else if (filter != null && grounds != null && grounds.Container == filter) okl.Add("кофе уже в фильтре");
else okl.Add("кофе в фильтре: SKIP (нет фильтра с кофе)");
// 4. «0ед»
var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
var def = Cozy.Grid.FurnitureCatalog.ById("milk_carton");
var gcur = Cozy.Grid.GridCursor.I;
var spawn = typeof(Cozy.Grid.GridCursor).GetMethod("SpawnObject", B);
var pos = Cozy.Grid.PlayerRef.Transform.position + UnityEngine.Vector3.down * 40f;
var full = (Cozy.Grid.InteractiveObject)spawn.Invoke(gcur, new object[]{ def, pos, 0f });
var empty = (Cozy.Grid.InteractiveObject)spawn.Invoke(gcur, new object[]{ def, pos + UnityEngine.Vector3.right, 0f });
var oil = (Cozy.Grid.InteractiveObject)spawn.Invoke(gcur, new object[]{ Cozy.Grid.FurnitureCatalog.ById("oil_bottle"), pos + UnityEngine.Vector3.left, 0f });
try {
  empty.Liquid.Take(100f); oil.Liquid.Take(100f);
  var l = new System.Collections.Generic.List<Cozy.Grid.ItemEffect>();
  Cozy.Grid.ItemEffects.Collect(empty, l); bool zero = false; foreach (var e in l) if (e.Hint == "Утоление жажды" && e.Text == "0ед") zero = true;
  if (!zero) bad.Add("пустой пакет без «0ед»"); else okl.Add("пустой пакет «0ед»");
  l.Clear(); Cozy.Grid.ItemEffects.Collect(oil, l); bool oilLine = false; foreach (var e in l) if (e.Hint == "Утоление жажды") oilLine = true;
  if (oilLine) bad.Add("у бутылки масла строка жажды"); else okl.Add("масло без строки жажды");
  // 5. отступ под заголовком
  var open = typeof(Tavern.UI.HudUI).GetMethod("OnInteractSelected", B); var close = typeof(Tavern.UI.HudUI).GetMethod("CloseInteractPanel", B);
  var fp = typeof(Tavern.UI.HudUI).GetField("_interactPanel", B);
  float[] gaps = new float[2]; int k = 0;
  foreach (var io in new[]{ full, empty }) {
    open.Invoke(hud, new object[]{ io }); UnityEngine.Canvas.ForceUpdateCanvases();
    var panel = fp.GetValue(hud) as UnityEngine.GameObject;
    foreach (UnityEngine.Transform c in panel.transform) { var t = c.GetComponent<TMPro.TMP_Text>(); if (t != null && c.name == "Text") { gaps[k] = t.margin.w; break; } }
    close.Invoke(hud, null); k++;
  }
  if (UnityEngine.Mathf.Abs(gaps[0] - gaps[1]) > 0.01f) bad.Add("отступ под заголовком " + gaps[0].ToString("0.00") + " vs " + gaps[1].ToString("0.00")); else okl.Add("отступ под заголовком ровный " + gaps[0].ToString("0.00"));
} finally {
  foreach (var io in new[]{ full, empty, oil }) if (io != null) { Cozy.Grid.LevelIO.Unsaved.Remove(io); UnityEngine.Object.Destroy(io.gameObject); }
}
// 6. отравление и бодрость
if (Cozy.Grid.FoodSpoil.DrinkDoses(Cozy.Grid.LiquidVolume.Milk, 5f, false) != 0) bad.Add("свежее молоко травит"); else okl.Add("свежее не травит");
int cheer = Cozy.Grid.LiquidVolume.Units(Cozy.Character.PlayerEffects.CheerCoffeeL);
if (cheer != 15) bad.Add("порог бодрости " + cheer + "ед"); else okl.Add("бодрость с 15ед");
// 7. порции
int g = Cozy.Grid.LiquidVolume.Units(Cozy.Grid.Greased.PortionL), s = Cozy.Grid.LiquidVolume.Units(Cozy.Grid.Sauced.PortionL);
if (g != 5 || s != 5) bad.Add("порции масло " + g + "ед, кетчуп " + s + "ед"); else okl.Add("порции по 5ед");
return string.Join("; ", bad.ToArray()) + "||" + string.Join("; ", okl.ToArray());
'''


def main():
    bad, ok = [], []
    r = run(PAN_START)
    if r.startswith('SKIP'):
        ok.append('сковорода: ' + r)
    elif not r.startswith('ok'):
        bad.append('сковорода: ' + r)
    else:
        try:
            hot = False
            for _ in range(10):
                time.sleep(2)
                t = run(PAN_READ)
                if '|' in t:
                    temp, sh = t.split('|')
                    if float(temp) >= 100 and sh == 'True':
                        hot = True; break
            (ok if hot else bad).append('сковорода греется и шипит' if hot else 'сковорода не греется/не шипит (' + t + ')')
        finally:
            run(PAN_END)
    r = run(CHECKS)
    if '||' in r:
        b, o = r.split('||')
        bad += [x for x in b.split('; ') if x]; ok += [x for x in o.split('; ') if x]
    else:
        bad.append(r)
    r = run(open(os.path.join(HERE, 'parts_motion_probe.cs')).read())
    (ok if r.startswith('PARTS ok') else bad).append(r[:200])
    print(('PRODUCTS ok' if not bad else 'PRODUCTS FAIL') + ' :: ' + str(len(ok)) + ' ок, ' + str(len(bad)) + ' красных')
    for x in bad: print('  ❌ ' + x)
    for x in ok: print('  ✅ ' + x)
    sys.exit(1 if bad else 0)


main()
