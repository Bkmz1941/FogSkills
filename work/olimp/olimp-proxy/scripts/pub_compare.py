#!/usr/bin/env python3
"""Сравнить две публикации бандла в Config Publisher (расшифровать обе и показать,
какие документы/поля APISettings отличаются). Публикация — путь в S3 или локальный файл
(например бэкап из ../backups/).

На ДЕВ-СЕРВЕРЕ 95.179.244.240:
  ssh admin@95.179.244.240 'timeout 90 python3 -I /tmp/pub_compare.py com.olimpRF1 \
     /tmp/old.json configs/v1/com.olimpRF1/base/config.json'
Старые версии публикаций лежат в S3 по пути configs/v1/<bundle>/<profile>/<publication_id>.json,
пока профиль активен (список id — `publisher publications list`). Только чтение.
"""
import json, base64, subprocess, urllib.request, sys, os

S3 = "https://s3.twcstorage.ru/proxyconfig-storage/publisher/"
bundle, a_src, b_src = sys.argv[1:4]
key = subprocess.run(["sudo", "-n", "cat", f"/srv/firebase-config-publisher/.secrets/keys/{bundle}.key"],
                     capture_output=True, check=True).stdout.strip()


def load(src):
    raw = open(src).read() if os.path.exists(src) else urllib.request.urlopen(S3 + src, timeout=20).read()
    d = json.loads(base64.b64decode(json.loads(raw)["data"]))
    return json.loads(subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-K", key.hex(), "-iv", d["iv"].encode().hex(), "-base64", "-A"],
                                     input=d["value"].encode(), capture_output=True, check=True).stdout)


A, B = load(a_src), load(b_src)
print("документов:", len(A), "->", len(B))
print("изменились документы:", sorted(k for k in set(A) | set(B) if A.get(k) != B.get(k)))
x, y = A.get("APISettings", {}), B.get("APISettings", {})
for k in sorted(set(x) | set(y)):
    if x.get(k) != y.get(k):
        if any(s in k.lower() for s in ("key", "secret", "token", "pass")):
            print(f"  APISettings.{k}: (секрет изменён)")
        else:
            print(f"  APISettings.{k}: {x.get(k)} -> {y.get(k)}")
