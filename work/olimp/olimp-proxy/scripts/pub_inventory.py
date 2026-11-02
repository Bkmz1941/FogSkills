#!/usr/bin/env python3
"""Инвентаризация конфигов Config Publisher: расшифровать текущие публикации из S3
и показать адреса API (default/direct_api_url, cms) и все вхождения искомой строки.

Запускать НА ДЕВ-СЕРВЕРЕ 95.179.244.240 (там ключи AES в .secrets, читаются через sudo):
  scp pub_inventory.py admin@95.179.244.240:/tmp/ && \
  ssh admin@95.179.244.240 'timeout 120 python3 -I /tmp/pub_inventory.py [строка] ; rm -f /tmp/pub_inventory.py'
По умолчанию ищет 'dlyamaster'. Только чтение.
"""
import json, base64, subprocess, urllib.request, sys

S3 = "https://s3.twcstorage.ru/proxyconfig-storage/publisher/"
KEYS = "/srv/firebase-config-publisher/.secrets/keys/"
NEEDLE = sys.argv[1] if len(sys.argv) > 1 else "dlyamaster"


def decrypt(bundle, path):
    key = subprocess.run(["sudo", "-n", "cat", KEYS + bundle + ".key"], capture_output=True, check=True).stdout.strip()
    assert len(key) == 32, f"{bundle}: key len {len(key)}"
    raw = urllib.request.urlopen(S3 + path, timeout=20).read()
    d = json.loads(base64.b64decode(json.loads(raw)["data"]))
    out = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-K", key.hex(), "-iv", d["iv"].encode().hex(), "-base64", "-A"],
                         input=d["value"].encode(), capture_output=True, check=True).stdout
    return json.loads(out)


def walk(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, p + "." + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{p}[{i}]")
    else:
        yield p, o


idx = json.loads(urllib.request.urlopen(S3 + "index.json", timeout=20).read())
for bundle, app in idx["applications"].items():
    rules = app.get("rules", []) + ([app["default"]] if isinstance(app.get("default"), dict) else [])
    for r in rules:
        if not r.get("available", True) or "path" not in r:
            continue
        c = decrypt(bundle, r["path"])
        a = c.get("APISettings", {})
        pub = r["path"].rsplit("/", 1)[-1][:12]
        print(f"{bundle} [{r.get('profile')}] {r.get('project_id')}/{r.get('app_name')} pub={pub} docs={len(c)}")
        print(f"    default={a.get('default_api_url')} direct={a.get('direct_api_url')} "
              f"cms={[x.get('url') for x in a.get('cms_api_urls', [])]} admin={a.get('admin_api_url')}")
        for p, v in walk(c):
            if isinstance(v, str) and NEEDLE in v:
                print(f"    {NEEDLE}: {p} = {v[:120]}")
