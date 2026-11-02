#!/usr/bin/env python3
r"""Заменить хост старого прокси на новый в указанных документах одной коллекции Config Publisher.
Каждый изменённый документ шлётся ОТДЕЛЬНО в POST /api/firebase/settings (не снапшот).
Меняются только строковые значения, где встречается старый хост; пути/параметры сохраняются.
Использовано 2026-10-31 для QA и SportQuiz (там старый адрес и в PaymentsSettings…payment_url).

На ДЕВ-СЕРВЕРЕ 95.179.244.240:
  ssh admin@95.179.244.240 'timeout 120 python3 -I /tmp/pub_replace_host.py \
     --bundle com.osportquiztop.app-qa --profile-path configs/v1/com.osportquiztop.app-qa/base/config.json \
     --project olimpcom-android-v2 --collection SportQuizQa --docs APISettings,PaymentsSettings [--send]'
Без --send — сухой прогон. Иконки (…/img/…) не трогаются, если не задан --include-images.
"""
import argparse, json, base64, subprocess, hashlib, urllib.request, urllib.error, re

S3 = "https://s3.twcstorage.ru/proxyconfig-storage/publisher/"
SECRETS = "/srv/firebase-config-publisher/.secrets/"
URL = "https://proxyconfig.aggone.dev/api/firebase/settings"

ap = argparse.ArgumentParser()
ap.add_argument("--bundle", required=True)
ap.add_argument("--profile-path", required=True)
ap.add_argument("--project", required=True)
ap.add_argument("--collection", required=True)
ap.add_argument("--docs", required=True, help="через запятую")
ap.add_argument("--old", default=r"https://dlyamasterapoblokirovkam1?\.top")
ap.add_argument("--new", default="https://api2.ragnaros.top")
ap.add_argument("--include-images", action="store_true")
ap.add_argument("--send", action="store_true")
a = ap.parse_args()
OLD = re.compile(a.old)


def fix(o):
    if isinstance(o, dict):
        return {k: fix(v) for k, v in o.items()}
    if isinstance(o, list):
        return [fix(v) for v in o]
    if isinstance(o, str) and OLD.search(o) and (a.include_images or "/img/" not in o):
        return OLD.sub(a.new, o)
    return o


def walk(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, p + "." + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{p}[{i}]")
    else:
        yield p, o


key = subprocess.run(["sudo", "-n", "cat", SECRETS + "keys/" + a.bundle + ".key"], capture_output=True, check=True).stdout.strip()
assert len(key) == 32
raw = urllib.request.urlopen(S3 + a.profile_path, timeout=20).read()
d = json.loads(base64.b64decode(json.loads(raw)["data"]))
cfg = json.loads(subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-K", key.hex(), "-iv", d["iv"].encode().hex(), "-base64", "-A"],
                                input=d["value"].encode(), capture_output=True, check=True).stdout)
secret = subprocess.run(["sudo", "-n", "cat", SECRETS + "firebase-signing.key"], capture_output=True, text=True, check=True).stdout.strip() if a.send else ""

for name in a.docs.split(","):
    old = cfg[name]
    new = fix(old)
    po, pn = dict(walk(old)), dict(walk(new))
    assert list(po) == list(pn), "структура изменилась"
    ch = [(p, po[p], pn[p]) for p in po if po[p] != pn[p]]
    assert all(isinstance(x, str) and a.new in y for _, x, y in ch)
    print(f"{a.bundle} {a.project}/{a.collection}/{name}: изменений {len(ch)}")
    for p, x, y in ch:
        print(f"   {p}: {x[:80]} -> {y[:80]}")
    if not ch or not a.send:
        continue
    payload = {"name": name, "project_id": a.project, "app_name": a.collection,
               "content": json.dumps(new, ensure_ascii=False, separators=(",", ":"))}
    sig = hashlib.md5(";".join([payload[k] for k in sorted(payload)] + [secret]).encode()).hexdigest()
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", "X-FB-Token": sig}, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=30)
        print("   ->", r.status, r.read().decode())
    except urllib.error.HTTPError as e:
        print("   -> ОШИБКА", e.code, e.read().decode())
