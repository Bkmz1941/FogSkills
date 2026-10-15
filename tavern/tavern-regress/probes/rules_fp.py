#!/usr/bin/env python3
"""Снимок разбора правил LifeRules БЕЗ редактора: корпус сниппетов → Check() + все поля каждого Rule/PlanStep.
python3 rules_fp.py <out.txt>
Корпус: aiRules всех уровней из persistentDataPath + каждое слово действия в 7 синтаксических позициях × 13
аргументов (словарь слов — из LifeRules.Parse.cs, читается прямо из исходника). Нужна свежая офлайн-сборка
(`offline_build.py`, /tmp/tavern_offline). Правка парсера: снять снимок ДО, после правки — ПОСЛЕ, сравнить
посимвольно (`cmp`); любая разница — либо найденная ошибка, либо смена поведения, которую решает Илья.
Зоны и объекты уровня офлайн не существуют, поэтому ветки «локация найдена» снимок не проходит — но и слова,
и ошибки, и порядок разбора сравниваются целиком (12.10: поймал, что run/walk были в switch, но не в наборе
действий)."""
import glob
import json
import os
import pathlib
import re
import subprocess
import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import offline_tests as ot

PARSE = ot.PROJECT + '/Assets/Modules/Life/LifeRules.Parse.cs'
LEVELS = os.path.expanduser('~/.config/unity3d/DefaultCompany/Tavern/levels')
EXTRA = ["run", "walk", "бегом", "шагом",
         "sectant_point_hand", "point at player", "point player", "указать на игрока", "указать на героя", "sectant_point_hand 4s", "point at player soon",
         "pray", "молится", "молиться", "молитва", "pray shake", "pray shake 8s", "молится трясёт 3s", "pray soon",
         "look around", "look around left 1s right 2s", "look around/wait left 1s back 2s loop", "осмотреться", "оглядеться back 1s",
         "look around back 1s", "look around sideways",
         "wait 5s", "стоять 3с", "ждать 2 сек", "wait soon", "WAIT", "Go", "Ёжик", "ничего", "sees player", "every 15 min"]
ARGS = ["", "[5s]", "[door_1]", "[player]", "[last seen]", "[unseen]", "[all]", "[crow]", "[sectant sectant_1][zone_x/marker_1]", "[run]", "[walk]", "[meter_outdoor_1]", "[zone_x]"]


def action_words():
    src = open(PARSE, encoding='utf-8').read()
    start = src.index('ActionByWord = Actions(')
    end = src.index(';', src.index('ParseDrop(then, ref i)', start))
    words = []
    for m in re.finditer(r'new\[\] \{([^}]*)\}', src[start:end]):
        words += re.findall(r'"([^"]+)"', m.group(1))
    if len(words) < 40:
        raise SystemExit('словарь действий не прочитан из LifeRules.Parse.cs')
    return words


def snippets():
    out = []
    for f in sorted(glob.glob(LEVELS + '/*.json')):
        try:
            rules = json.load(open(f, encoding='utf-8')).get('aiRules') or ''
        except Exception:
            continue
        if rules.strip():
            out.append(('level ' + os.path.basename(f), rules))
    for w in action_words() + EXTRA:
        for a in ARGS:
            out.append(('rule %s %s' % (w, a), '[sectant_1] → [%s]%s' % (w, a)))
        out.append(('crow %s' % w, '[crow_1] → [%s][5s]' % w))
        out.append(('noarrow %s' % w, '[sectant_1][%s][5s]' % w))
        out.append(('bare %s' % w, '[%s][5s]' % w))
        out.append(('group %s' % w, '[sectant_1][loop]:\n1. [%s][5s]\n2. [%s]\n\n- [sees player]:\n  [%s]\n  [continue]' % (w, w, w)))
        out.append(('headerlike %s' % w, '[%s]\n- [sees player]:\n  [wait]' % w))
        out.append(('after go %s' % w, '[sectant_1] → [go][player][%s]' % w))
    out.append(('emotion', '[sectant_1][sees player] → (alert 3s)[wait][2s](question)[continue]'))
    out.append(('emotion only', '[sectant_1][sees player] → (alert)'))
    out.append(('emotion cond', '[sectant_1](alert) → [wait]'))
    out.append(('mixed', '[sectant_1][21:00-06:00][loop][priority 2]:\n[go][player][run][look around left1s loop]\n[look around/wait left2s right2s back2s]\n[open][door_2]\n[lock]\n[unlock][door_3]\n[pick up][meter_outdoor_1]\n[drop][zone_x/marker_2]\n[toggle][lamp_1]\n[vanish][unseen]\n- [while hears player]:\n  (question 5s)\n  [sectant_point_hand]\n- [reached][zone_x/marker_1]:\n  [pray shake][12s]\n  [continue]'))
    out.append(('leash', '[sectant_1][leash 12]:\n[wait][5s]\n\n[sectant_1][leash zone_x 7m]:\n[roam][20s]\n\n[sectant_1][поводок 3 м]:\n[wait]'))
    out.append(('keys', '[sectant_1]:\n[wait]\n- [sees door][has key]:\n  [open]\n- [sees locked door door_3][no key 100]:\n  [knock]\n- [sees unlocked door]:\n  [close]'))
    return out


DUMP = r'''
using System;
using System.Collections;
using System.Linq;
using System.Reflection;
using System.Text;
static class Program
{
    static string Val(object v, int depth)
    {
        if (v == null) return "null";
        if (v is string s) return "\"" + s + "\"";
        if (v is float f) return f.ToString("R", System.Globalization.CultureInfo.InvariantCulture);
        if (v is bool || v is int) return v.ToString();
        if (v is IEnumerable e && depth < 3)
        {
            var sb = new StringBuilder("[");
            foreach (var x in e) sb.Append(Dump(x, depth + 1)).Append(';');
            return sb.Append(']').ToString();
        }
        return v.GetType().Name;
    }
    static string Dump(object o, int depth)
    {
        if (o == null) return "null";
        var t = o.GetType();
        var sb = new StringBuilder("{");
        foreach (var f in t.GetFields(BindingFlags.Public | BindingFlags.Instance).OrderBy(x => x.Name))
            sb.Append(f.Name).Append('=').Append(Val(f.GetValue(o), depth)).Append(' ');
        foreach (var p in t.GetProperties(BindingFlags.Public | BindingFlags.Instance).OrderBy(x => x.Name))
            if (p.GetIndexParameters().Length == 0) sb.Append(p.Name).Append('=').Append(Val(p.GetValue(o), depth)).Append(' ');
        return sb.Append('}').ToString();
    }
    static int Main(string[] args)
    {
        var dir = AppContext.BaseDirectory;
        var grid = Assembly.LoadFrom(System.IO.Path.Combine(dir, "Cozy.Grid.dll"));
        var life = Assembly.LoadFrom(System.IO.Path.Combine(dir, "Cozy.Life.dll"));
        var levelIo = grid.GetType("Cozy.Grid.LevelIO");
        var rules = life.GetType("Cozy.Life.LifeRules");
        var aiProp = levelIo.GetProperty("AiRules", BindingFlags.Public | BindingFlags.Static);
        var aiField = levelIo.GetField("AiRules", BindingFlags.Public | BindingFlags.Static);
        Action<string> setRules = v => { if (aiProp != null) aiProp.SetValue(null, v); else aiField.SetValue(null, v); };
        var check = rules.GetMethod("Check", BindingFlags.Public | BindingFlags.Static);
        var list = rules.GetProperty("Rules", BindingFlags.Public | BindingFlags.Static);
        if ((aiProp == null && aiField == null) || check == null || list == null) { Console.WriteLine("нет члена: AiRules=" + (aiProp != null || aiField != null) + " Check=" + (check != null) + " Rules=" + (list != null)); return 2; }
        var text = System.IO.File.ReadAllText(args[0]);
        var parts = text.Split(new[] { "\n=====SNIPPET " }, StringSplitOptions.RemoveEmptyEntries);
        var outp = new StringBuilder();
        foreach (var part in parts)
        {
            int nl = part.IndexOf('\n');
            string name = part.Substring(0, nl).Trim();
            string body = part.Substring(nl + 1);
            setRules(body);
            string report;
            try { report = (string)check.Invoke(null, new object[] { "" }); }
            catch (TargetInvocationException e) { report = "EXC " + e.InnerException.GetType().Name + ": " + e.InnerException.Message; }
            outp.Append("##### ").Append(name).Append('\n').Append(report).Append('\n');
            try
            {
                foreach (var r in (IEnumerable)list.GetValue(null)) outp.Append("  ").Append(Dump(r, 0)).Append('\n');
            }
            catch (TargetInvocationException e) { outp.Append("  EXC ").Append(e.InnerException.Message).Append('\n'); }
        }
        Console.Write(outp.ToString());
        return 0;
    }
}
'''


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    out = pathlib.Path(sys.argv[1])
    work = pathlib.Path(ot.HARNESS) / 'rules_fp'
    work.mkdir(parents=True, exist_ok=True)
    corpus = work / 'corpus.txt'
    corpus.write_text(''.join('\n=====SNIPPET %s\n%s' % (n, b) for n, b in snippets()), encoding='utf-8')
    bin_dir = ot.stage()
    src = work / 'Dump.cs'
    src.write_text(DUMP)
    exe = bin_dir / 'rulesdump.dll'
    rt = ot.runtime_dir()
    (bin_dir / 'rulesdump.runtimeconfig.json').write_text(
        '{"runtimeOptions":{"tfm":"net6.0","framework":{"name":"Microsoft.NETCore.App","version":"%s"}}}' % os.path.basename(rt))
    refs = ['System.Runtime', 'System.Collections', 'System.Console', 'System.Linq', 'System.Private.CoreLib', 'netstandard']
    rsp = work / 'dump.rsp'
    rsp.write_text('\n'.join(['-target:exe', '-nologo', '-nostdlib', '-out:' + str(exe)] + ['-r:"%s/%s.dll"' % (rt, r) for r in refs] + [str(src)]))
    res = subprocess.run([ot.DOTNET, ot.CSC, '@' + str(rsp)], capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit('дамп не собрался:\n' + res.stdout + res.stderr)
    res = subprocess.run([ot.DOTNET, str(exe), str(corpus)], capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit('дамп упал:\n' + res.stdout[-2000:] + res.stderr[-2000:])
    out.write_text(res.stdout, encoding='utf-8')
    print('снимок: %s — сниппетов %d, строк %d' % (out, res.stdout.count('##### '), res.stdout.count('\n')))


if __name__ == '__main__':
    main()
