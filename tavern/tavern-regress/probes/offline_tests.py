#!/usr/bin/env python3
"""EditMode-тесты чистой логики БЕЗ редактора — пока Илья в play (P992, P993).

python3 offline_tests.py [--build] [КлассТеста ...]
    по умолчанию: LifeRulesParseTests AiMonsterBriefTests

Берёт сборки из офлайн-сборки (`offline_build.py`, /tmp/tavern_offline; `--build`
или их отсутствие — собрать заново), кладёт рядом UnityEngine-модули редактора и
nunit, компилирует крошечный раннер (рефлексия по [Test]/[SetUp]/[TearDown]) и
гоняет его рантаймом .NET из редактора. Годится только тестам, которые не зовут
натив Unity (Resources, PlayerPrefs, сцена): такие падают не AssertionException,
раннер печатает стек. Код выхода 1 — есть красные.
"""
import glob
import os
import pathlib
import shutil
import subprocess
import sys

PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
EDITOR = os.path.expanduser('~/Unity/Hub/Editor/6000.3.10f1/Editor/Data')
DOTNET = EDITOR + '/NetCoreRuntime/dotnet'
CSC = EDITOR + '/DotNetSdkRoslyn/csc.dll'
OFFLINE = '/tmp/tavern_offline'
HARNESS = OFFLINE + '/tests'
DEFAULT = ['LifeRulesParseTests', 'AiMonsterBriefTests']

RUNNER = r'''
using System;
using System.Linq;
using System.Reflection;

static class Program
{
    static int Main(string[] args)
    {
        var asm = Assembly.LoadFrom(System.IO.Path.Combine(AppContext.BaseDirectory, "Tavern.Tests.EditMode.dll"));
        int red = 0, green = 0;
        foreach (var type in asm.GetTypes().Where(t => args.Length == 0 || args.Contains(t.Name)))
        {
            var tests = type.GetMethods().Where(m => m.GetCustomAttributes().Any(a => a.GetType().Name == "TestAttribute")).ToList();
            if (tests.Count == 0) continue;
            var setUp = type.GetMethods().FirstOrDefault(m => m.GetCustomAttributes().Any(a => a.GetType().Name == "SetUpAttribute"));
            var tearDown = type.GetMethods().FirstOrDefault(m => m.GetCustomAttributes().Any(a => a.GetType().Name == "TearDownAttribute"));
            foreach (var test in tests)
            {
                var inst = Activator.CreateInstance(type);
                try
                {
                    setUp?.Invoke(inst, null);
                    test.Invoke(inst, null);
                    green++;
                    Console.WriteLine("✓ " + type.Name + "." + test.Name);
                }
                catch (TargetInvocationException e)
                {
                    red++;
                    var inner = e.InnerException;
                    Console.WriteLine("✗ " + type.Name + "." + test.Name + ": " + inner.GetType().Name + " " + inner.Message.Replace("\n", " ⏎ "));
                    if (inner.GetType().Name != "AssertionException") Console.WriteLine(inner.StackTrace);
                }
                finally { try { tearDown?.Invoke(inst, null); } catch { } }
            }
        }
        Console.WriteLine("итог: зелёных " + green + ", красных " + red);
        return red == 0 ? 0 : 1;
    }
}
'''


def runtime_dir():
    shared = glob.glob(EDITOR + '/NetCoreRuntime/shared/Microsoft.NETCore.App/*')
    if not shared:
        raise SystemExit('нет рантайма .NET в редакторе: ' + EDITOR)
    return sorted(shared)[-1]


def build_game(force):
    if force or not os.path.exists(OFFLINE + '/Tavern.Tests.EditMode.dll'):
        res = subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name('offline_build.py'))], text=True)
        if res.returncode != 0:
            raise SystemExit('офлайн-сборка красная — тесты не гоняем')


def stage():
    bin_dir = pathlib.Path(HARNESS) / 'bin'
    bin_dir.mkdir(parents=True, exist_ok=True)
    for f in glob.glob(OFFLINE + '/*.dll') + glob.glob(EDITOR + '/Managed/UnityEngine/*.dll'):
        shutil.copy(f, bin_dir)
    nunit = glob.glob(PROJECT + '/Library/PackageCache/com.unity.ext.nunit*/net40/unity-custom/nunit.framework.dll')
    if not nunit:
        raise SystemExit('nunit.framework.dll не найден в Library/PackageCache')
    shutil.copy(nunit[0], bin_dir)
    return bin_dir


def build_runner(bin_dir):
    src = pathlib.Path(HARNESS) / 'Program.cs'
    out = bin_dir / 'rulecheck.dll'
    if out.exists() and src.exists() and src.read_text() == RUNNER:
        return out
    src.write_text(RUNNER)
    rt = runtime_dir()
    version = os.path.basename(rt)
    (bin_dir / 'rulecheck.runtimeconfig.json').write_text(
        '{"runtimeOptions":{"tfm":"net6.0","framework":{"name":"Microsoft.NETCore.App","version":"%s"}}}' % version)
    refs = ['System.Runtime', 'System.Collections', 'System.Console', 'System.Linq', 'System.Private.CoreLib', 'netstandard']
    rsp = pathlib.Path(HARNESS) / 'runner.rsp'
    rsp.write_text('\n'.join(['-target:exe', '-nologo', '-nostdlib', '-out:' + str(out)]
                             + ['-r:"%s/%s.dll"' % (rt, r) for r in refs] + [str(src)]))
    res = subprocess.run([DOTNET, CSC, '@' + str(rsp)], capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit('раннер не собрался:\n' + res.stdout + res.stderr)
    return out


def main():
    args = sys.argv[1:]
    force = '--build' in args
    classes = [a for a in args if not a.startswith('--')] or DEFAULT
    build_game(force)
    bin_dir = stage()
    runner = build_runner(bin_dir)
    res = subprocess.run([DOTNET, str(runner)] + classes, text=True)
    return res.returncode


if __name__ == '__main__':
    sys.exit(main())
