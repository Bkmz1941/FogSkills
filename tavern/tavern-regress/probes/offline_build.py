"""Офлайн-сборка всех сборок проекта Roslyn'ом редактора — пока редактор в play (P844).

python3 offline_build.py [папка_вывода]     по умолчанию /tmp/tavern_offline

Списки исходников в Library/Bee устаревают: новые файлы соседей туда не попадают,
и «офлайн чисто» врёт (P753, P760, P844, P856). Здесь:
- исходники — все .cs папки asmdef, кроме вложенных asmdef;
- ссылки на сборки проекта — по `references` asmdef: только что собранные или свежие
  из Library/ScriptAssemblies; лишних ссылок нет (иначе имена неоднозначны);
- флаги компилятора и ссылки Unity — из rsp редактора той же сборки (или основной сборки сетки);
- порядок — по зависимостям;
- `-refout` редактора НЕ копируется: иначе офлайн-сборка перезаписывает справочные сборки
  в Library/Bee, и редактор перестаёт видеть сборку (05.10, P847: справочная сборка сетки стала 4 КБ).
Код выхода 1, если хоть одна сборка с ошибкой.
"""
import glob
import json
import os
import re
import subprocess
import sys

PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
EDITOR = os.path.expanduser('~/Unity/Hub/Editor/6000.3.10f1/Editor/Data')
DOTNET = EDITOR + '/NetCoreRuntime/dotnet'
CSC = EDITOR + '/DotNetSdkRoslyn/csc.dll'
BEE = PROJECT + '/Library/Bee/artifacts/2400b0aE.dag'
LIB = PROJECT + '/Library/ScriptAssemblies'
FALLBACK_TEMPLATE = 'Cozy.Grid'


def asmdefs():
    found = {}
    guids = {}
    for path in glob.glob(PROJECT + '/Assets/**/*.asmdef', recursive=True):
        data = json.load(open(path, encoding='utf-8'))
        found[data['name']] = {'dir': os.path.dirname(path), 'refs': data.get('references', [])}
        meta = path + '.meta'
        if os.path.exists(meta):
            m = re.search(r'guid: ([0-9a-f]+)', open(meta).read())
            if m:
                guids['GUID:' + m.group(1)] = data['name']
    for info in found.values():
        info['refs'] = [guids.get(r, r) for r in info['refs']]
    return found


def sources(folder):
    out = []
    for root, dirs, files in os.walk(folder):
        if root != folder and any(f.endswith('.asmdef') for f in os.listdir(root)):
            dirs[:] = []
            continue
        out.extend(os.path.join(root, f) for f in files if f.endswith('.cs'))
    return sorted(out)


def order(found):
    done, seq = set(), []

    def visit(name, stack=()):
        if name in done or name not in found:
            return
        if name in stack:
            raise SystemExit('цикл зависимостей: ' + ' → '.join(stack + (name,)))
        for r in found[name]['refs']:
            visit(r, stack + (name,))
        done.add(name)
        seq.append(name)

    for name in sorted(found):
        visit(name)
    return seq


def ref_name(line):
    m = re.match(r'-r:"?(.*?)"?$', line)
    if not m:
        return None
    base = os.path.basename(m.group(1))
    for tail in ('.ref.dll', '.dll'):
        if base.endswith(tail):
            return base[:-len(tail)]
    return base


def rsp_for(name, info, found, out_dir):
    template = BEE + '/' + name + '.rsp'
    if not os.path.exists(template):
        template = BEE + '/' + FALLBACK_TEMPLATE + '.rsp'
    keep = []
    for line in open(template, encoding='utf-8').read().splitlines():
        if not line.startswith('-') or line.startswith('-out:') or line.startswith('-refout:') or line.startswith('/additionalfile'):
            continue
        if line.startswith('-r:'):
            n = ref_name(line)
            if n in found:
                continue
            if n and os.path.exists(LIB + '/' + n + '.dll'):
                line = '-r:"' + LIB + '/' + n + '.dll"'
        keep.append(line)
    for r in info['refs']:
        if r in found:
            keep.append('-r:"' + out_dir + '/' + r + '.dll"')
        elif os.path.exists(LIB + '/' + r + '.dll') and not any(ref_name(k) == r for k in keep):
            keep.append('-r:"' + LIB + '/' + r + '.dll"')
    keep.insert(0, '-out:' + out_dir + '/' + name + '.dll')
    keep += ['"' + s + '"' for s in sources(info['dir'])]
    path = out_dir + '/' + name + '.rsp'
    open(path, 'w', encoding='utf-8').write('\n'.join(keep) + '\n')
    return path


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else '/tmp/tavern_offline'
    os.makedirs(out_dir, exist_ok=True)
    found = asmdefs()
    bad = 0
    guard = {f: os.path.getmtime(f) for f in glob.glob(PROJECT + '/Library/Bee/artifacts/*/*.dll')}
    for name in order(found):
        rsp = rsp_for(name, found[name], found, out_dir)
        res = subprocess.run([DOTNET, CSC, '@' + rsp], capture_output=True, text=True, cwd=PROJECT)
        errors = [l for l in res.stdout.splitlines() if ': error ' in l]
        if errors:
            bad += 1
            print(name + ': ОШИБКИ ' + str(len(errors)))
            for e in errors[:6]:
                print('   ' + e.replace(PROJECT + '/', ''))
        else:
            print(name + ': ок')
    touched = [f for f, t in guard.items() if not os.path.exists(f) or os.path.getmtime(f) != t]
    if touched:
        bad += 1
        print('КРАСНОЕ: офлайн-сборка тронула файлы редактора (P847):', ', '.join(os.path.basename(f) for f in touched[:6]))
    print('итог:', 'чисто' if bad == 0 else 'КРАСНОЕ — сборок с ошибками ' + str(bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
