#!/usr/bin/env bash
set -uo pipefail
S="$(cd "$(dirname "$0")" && pwd)"
P="$1"; shift
for id in "$@"; do
  npx -y apidog-cli@2.2.9 endpoint get "$id" --project "$P" > "$S/raw-$id.json" 2>/dev/null
  python3 - "$S/raw-$id.json" "$S/body-$id.json" "$S/pre-on.json" <<'PY'
import json, sys
raw=open(sys.argv[1],encoding="utf-8").read()
data=json.loads(raw[raw.index("{"):])["data"]
params=data.get("parameters") or {}
names={"x-api-key","x-sign","x-public-key"}
for h in params.get("header") or []:
    n=(h.get("name") or "").lower()
    if n in names: h["example"]="{{"+("x-public-key" if n=="x-api-key" else n)+"}}"
pre=json.load(open(sys.argv[3]))["preProcessors"]
json.dump({"parameters":params,"preProcessors":pre},open(sys.argv[2],"w"),ensure_ascii=False)
print(f'{data.get("method","").upper():<7}{data.get("path")}', end=" ")
PY
  if npx -y apidog-cli@2.2.9 endpoint update "$id" --project "$P" --file "$S/body-$id.json" 2>&1 | grep -q '"success": true'; then echo "ok"; else echo "FAILED"; fi
  rm -f "$S/raw-$id.json" "$S/body-$id.json"
done
