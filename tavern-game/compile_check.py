#!/usr/bin/env python3
"""Автономная компиляция всех asmdef-сборок проекта Roslyn'ом из поставки Unity.

Запуск из корня проекта: python3 compile_check.py
Успех = каждая сборка выдала .dll и ни одной строки с "error CS".
"""
import glob, json, os, re, shutil, subprocess, sys

PROJ = os.getcwd()
DATA = os.path.expanduser("~/Unity/Hub/Editor/6000.3.10f1/Editor/Data")
DOTNET = os.path.join(DATA, "NetCoreRuntime", "dotnet")
CSC = os.path.join(DATA, "DotNetSdkRoslyn", "csc.dll")
OUT = os.path.join(PROJ, "Temp", "compile_check")


def read(p):
    with open(p, encoding="utf-8-sig") as f:
        return f.read()


def csproj_refs(text):
    refs = []
    for m in re.finditer(r"<HintPath>(.*?)</HintPath>", text, re.S):
        p = m.group(1).strip()
        if not os.path.isabs(p):
            p = os.path.join(PROJ, p)
        if os.path.exists(p):
            refs.append(os.path.realpath(p))
    return refs


# Ссылки и дефайны берём из СВОЕГО csproj каждой сборки: смешивать наборы
# нельзя — netstandard-шимы и unity-4.8-api дают одинаковые фасады, и csc
# падает на CS1703 ещё до разбора исходников.
proj_refs, defines = {}, None
union = []
for cp in sorted(glob.glob(os.path.join(PROJ, "*.csproj"))):
    text = read(cp)
    name = os.path.splitext(os.path.basename(cp))[0]
    proj_refs[name] = csproj_refs(text)
    union += proj_refs[name]
    if defines is None:
        m = re.search(r"<DefineConstants>(.*?)</DefineConstants>", text, re.S)
        if m:
            defines = [d for d in m.group(1).split(";") if d]

# Запасной набор для сборок без своего csproj: по одному файлу на имя.
fallback, seen_names = [], set()
for r in union:
    n = os.path.basename(r)
    if n in seen_names:
        continue
    seen_names.add(n)
    fallback.append(r)

asm = {}
for ad in glob.glob(os.path.join(PROJ, "Assets", "**", "*.asmdef"), recursive=True):
    j = json.loads(read(ad))
    asm[j["name"]] = {
        "root": os.path.dirname(ad),
        "refs": [r.split(":")[-1] for r in j.get("references", [])],
        "editor": j.get("includePlatforms") == ["Editor"],
        "srcs": [],
    }

roots = sorted(((v["root"], k) for k, v in asm.items()), key=lambda x: -len(x[0]))
loose, loose_editor = [], []
for cs in glob.glob(os.path.join(PROJ, "Assets", "**", "*.cs"), recursive=True):
    owner = next((n for root, n in roots if cs.startswith(root + os.sep)), None)
    if owner:
        asm[owner]["srcs"].append(cs)
    else:
        (loose_editor if os.sep + "Editor" + os.sep in cs else loose).append(cs)

asm["Assembly-CSharp"] = {"refs": [k for k in list(asm) if not asm[k]["editor"]],
                          "editor": False, "srcs": loose}
asm["Assembly-CSharp-Editor"] = {"refs": list(asm), "editor": True, "srcs": loose_editor}

order, seen = [], set()


def visit(n, stack=()):
    if n in seen or n not in asm or n in stack:
        return
    for r in asm[n]["refs"]:
        visit(r, stack + (n,))
    seen.add(n)
    order.append(n)


for n in list(asm):
    visit(n)

shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT, exist_ok=True)

fail = 0
for name in order:
    a = asm[name]
    if not a["srcs"]:
        continue
    refs = list(proj_refs.get(name, fallback))
    refs = [r for r in refs if os.path.splitext(os.path.basename(r))[0] not in asm]
    for r in a["refs"]:
        built = os.path.join(OUT, r + ".dll")
        stale = os.path.join(PROJ, "Library", "ScriptAssemblies", r + ".dll")
        if os.path.exists(built):
            refs.append(built)
        elif os.path.exists(stale):
            refs.append(stale)

    dll = os.path.join(OUT, name + ".dll")
    rsp = os.path.join(OUT, name + ".rsp")
    with open(rsp, "w") as f:
        f.write("-nostdlib+\n-target:library\n-langversion:9.0\n"
                "-nowarn:0169,0414,0649,USG0001\n-unsafe-\n")
        f.write("-out:%s\n" % dll)
        for d in defines:
            f.write("-define:%s\n" % d)
        for r in sorted(set(refs)):
            f.write('-r:"%s"\n' % r)
        for s in sorted(a["srcs"]):
            f.write('"%s"\n' % s)

    res = subprocess.run([DOTNET, CSC, "-noconfig", "@" + rsp],
                         capture_output=True, text=True, cwd=PROJ)
    out = res.stdout + res.stderr
    errs = [l for l in out.splitlines() if "error CS" in l]
    if errs or not os.path.exists(dll):
        fail += 1
        print("FAIL %s (%d ошибок%s)" % (name, len(errs), "" if os.path.exists(dll) else ", dll не собрана"))
        for l in errs[:25]:
            print("   ", l.replace(PROJ + "/", ""))
    else:
        print("ok   %s (%d файлов)" % (name, len(a["srcs"])))

print("=== %s ===" % ("КОМПИЛЯЦИЯ ЧИСТАЯ" if fail == 0 else "СБОРОК УПАЛО: %d" % fail))
sys.exit(1 if fail else 0)
