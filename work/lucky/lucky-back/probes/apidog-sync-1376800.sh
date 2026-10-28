#!/usr/bin/env bash
# Пересобирает Apidog-проект 1376800 («Lucky public API») из
# others/docs/openapi/game-provider.openapi.yaml.
#
# Отличие от синка 1341455: публичная дока идёт БЕЗ схем (LSR-101), поэтому
# спека сначала раскрывается в плоскую копию — все $ref подставлены по месту,
# блок components выброшен целиком. Импорт не перезаписывает существующее,
# поэтому эндпоинты и схемы удаляются перед импортом; прескрипты подписи и
# плейсхолдеры заголовков импорт не переносит, их возвращает второй проход.

set -uo pipefail

REPO="$HOME/Documents/Work/Lucky/lucky-api"
SPEC="$REPO/others/docs/openapi/game-provider.openapi.yaml"
FLAT="${TMPDIR:-/tmp}/gp-inline.yaml"
PROBES="$HOME/.claude/skills/lucky-back/probes"
PROJ=1376800
CLI="npx -y apidog-cli@2.2.9"

ids() {  # ids endpoint|schema  -> id'шники, по одному в строке
  $CLI "$1" list --project $PROJ 2>&1 | python3 -c "
import json,sys
raw=sys.stdin.read(); d=json.loads(raw[raw.find('{'):])['data']
if isinstance(d,dict): d=d.get('list') or d.get('items') or []
print(' '.join(str(x['id']) for x in d))
"
}

echo "=== 1/6 раскрываем спеку в плоскую копию"
python3 - "$SPEC" "$FLAT" <<'PY' || exit 1
import copy, sys, yaml
doc = yaml.safe_load(open(sys.argv[1]))

def resolve(ref):
    node = doc
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node

def deref(node, seen=()):
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/"):
            if ref in seen:
                return {"type": "object"}
            out = deref(copy.deepcopy(resolve(ref)), seen + (ref,))
            if isinstance(out, dict):
                out.update({k: v for k, v in node.items() if k != "$ref"})
            return out
        return {k: deref(v, seen) for k, v in node.items()}
    if isinstance(node, list):
        return [deref(v, seen) for v in node]
    return node

doc["paths"] = deref(doc["paths"])
doc.pop("components", None)
open(sys.argv[2], "w").write(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=10000))
text = open(sys.argv[2]).read()
assert "$ref" not in text and "components:" not in text, "плоская копия неполная"
print(f"  путей: {len(doc['paths'])}, схем не осталось")
PY

echo "=== 2/6 сносим эндпоинты"
for id in $(ids endpoint); do printf '  %s ' "$id"; $CLI endpoint delete "$id" --project $PROJ >/dev/null 2>&1 && echo ok || echo FAILED; done

echo "=== 3/6 сносим схемы"
for id in $(ids schema); do printf '  %s ' "$id"; $CLI schema delete "$id" --project $PROJ >/dev/null 2>&1 && echo ok || echo FAILED; done

echo "=== 4/6 импорт"
$CLI import --project $PROJ --format openapi --file "$FLAT" 2>&1 | python3 -c "
import json,sys
raw=sys.stdin.read(); d=json.loads(raw[raw.find('{'):])
c=d['data']['apiCollection']['item']
print('  создано:', c['createCount'], '| пропущено:', c['ignoreCount'], '| ошибок:', c['errorCount'])
"

echo "=== 5/6 возвращаем прескрипты подписи и плейсхолдеры заголовков"
# shellcheck disable=SC2046
bash "$PROBES/reapply.sh" $PROJ $(ids endpoint)

echo "=== 6/6 примеры ответов"
python3 "$HOME/.claude/skills/lucky-back/probes/response-examples.py" $PROJ "$FLAT" 2>/dev/null \
  || python3 "$(dirname "$0")/response-examples.py" $PROJ "$FLAT"

echo
echo "=== сверка"
python3 "$PROBES/verify.py" $PROJ "$FLAT"
