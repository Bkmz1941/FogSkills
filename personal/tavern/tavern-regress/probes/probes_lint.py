"""Живы ли пробы: всё, на что пробы ссылаются в коде игры, в коде игры ещё есть. Без Unity, секунда.

python3 probes_lint.py            список проб с мёртвыми ссылками, код 1 если такие есть

Зачем (16.09): `encounter_probe.py` звал `Cozy.Combat.BraceEffect` и ползунки крыльев, снятые
ночью 15→16.09, и сутки молча не работал — стычка осталась без живой защиты, а узнали случайно.
Та же семья, что правило 24 в 13.09 (P381): защита умирает тихо, когда код под ней переименовали.
Проба компилируется только в момент прогона, поэтому ловим раньше — по тексту:

- полные имена `Cozy.*` / `Tavern.*` в пробах (.py с кодом для execute_code и .cs-зонды):
  каждое имя после пространства имён обязано встречаться в коде `Assets` (без комментариев и строк);
- рефлексия `GetField("x")` / `GetMethod` / `GetProperty` — имя `x` обязано быть в коде.

Проверка грубая (есть ли такое слово в коде вообще), зато без ложных тревог на переносах
между файлами и классами. Пропажу слова целиком она ловит всегда.
"""
import pathlib, re, sys

PROJECT = pathlib.Path('/media/ilya/T714/Unity/Tavern-fresh')
PROBES = pathlib.Path(__file__).resolve().parent
NAMESPACES = {'Cozy', 'Tavern', 'Grid', 'Combat', 'Character', 'UI', 'Core', 'View', 'Effects', 'Weather',
              'Cooking', 'Monsters', 'Loc', 'Net', 'Data', 'Tests'}
QUALIFIED = re.compile(r'\b(?:Cozy|Tavern)(?:\.[A-Za-z_]\w*)+')
REFLECTED = re.compile(r'Get(?:Field|Method|Property)\(\s*\\?"(\w+)\\?"')


def strip(src):
    src = re.sub(r'/\*.*?\*/', ' ', src, flags=re.S)
    src = re.sub(r'//[^\n]*', ' ', src)
    return re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', src)


def code_words():
    words = set()
    for f in (PROJECT / 'Assets').rglob('*.cs'):
        words.update(re.findall(r'[A-Za-z_]\w*', strip(f.read_text(encoding='utf-8', errors='replace'))))
    return words


def main():
    words = code_words()
    dead = {}
    checked = 0
    for probe in sorted(PROBES.iterdir()):
        if probe.suffix not in ('.py', '.cs') or probe.name == pathlib.Path(__file__).name:
            continue
        text = probe.read_text(encoding='utf-8', errors='replace')
        missing = set()
        for ref in QUALIFIED.findall(text):
            if ref.endswith('.dll'):
                continue
            parts = ref.split('.')
            while parts and parts[0] in NAMESPACES:
                parts.pop(0)
            for part in parts:
                checked += 1
                if part not in words:
                    missing.add(ref)
                    break
        for name in REFLECTED.findall(text):
            checked += 1
            if name not in words:
                missing.add('рефлексия «%s»' % name)
        if missing:
            dead[probe.name] = sorted(missing)
    for name, refs in dead.items():
        print('МЁРТВЫЕ ССЫЛКИ %s: %s' % (name, ', '.join(refs[:8]) + (' …' if len(refs) > 8 else '')))
    print('пробы: ссылок проверено %d, проб с мёртвыми ссылками %d' % (checked, len(dead)))
    return 1 if dead else 0


if __name__ == '__main__':
    sys.exit(main())
