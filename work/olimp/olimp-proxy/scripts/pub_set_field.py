#!/usr/bin/env python3
r"""Точечно поменять ОДНО поле одного документа в Config Publisher (proxyconfig.aggone.dev).

Берёт ТЕКУЩУЮ публикацию бандла из S3, расшифровывает, меняет одно поле документа,
проверяет (assert), что изменилось только оно, подписывает и шлёт ОДИН документ
в POST /api/firebase/settings (не снапшот! снапшот авторитетный и удаляет документы,
которых в нём нет). Publisher пересобирает публикацию и за ~5 с выкладывает в S3.

Запускать НА ДЕВ-СЕРВЕРЕ 95.179.244.240:
  scp pub_set_field.py admin@95.179.244.240:/tmp/
  ssh admin@95.179.244.240 'timeout 90 python3 -I /tmp/pub_set_field.py \
      --bundle com.olimp.app --profile-path configs/v1/com.olimp.app/from-246.0.0/config.json \
      --project olimpcom-android-v2 --collection OlimpCom \
      --doc APISettings --field default_api_url --value https://API2.RAGNAROS.TOP [--send]; rm -f /tmp/pub_set_field.py'
Без --send — сухой прогон (только показывает diff).

Соответствие бандл → (project, collection, profile) — в config.yml publisher и в index.json S3.
ПЕРЕД --send: записать текущую публикацию для отката
  docker compose exec -T app publisher status   (в /srv/firebase-config-publisher)
Откат: publisher rollback --application <bundle> --profile <profile> --publication <старый id>
"""
import argparse, json, base64, subprocess, hashlib, urllib.request, urllib.error

S3 = "https://s3.twcstorage.ru/proxyconfig-storage/publisher/"
SECRETS = "/srv/firebase-config-publisher/.secrets/"
URL = "https://proxyconfig.aggone.dev/api/firebase/settings"

ap = argparse.ArgumentParser()
ap.add_argument("--bundle", required=True)
ap.add_argument("--profile-path", required=True, help="configs/v1/<bundle>/<profile>/config.json")
ap.add_argument("--project", required=True, help="project_id как в config.yml publisher (olimp-premium-93c72, olimpcom-android-v2 …)")
ap.add_argument("--collection", required=True, help="app_name: olimpkz, OlimpCom, OlimpPremium2 …")
ap.add_argument("--doc", required=True)
ap.add_argument("--field", required=True)
ap.add_argument("--value", required=True)
ap.add_argument("--send", action="store_true")
a = ap.parse_args()

key = subprocess.run(["sudo", "-n", "cat", SECRETS + "keys/" + a.bundle + ".key"], capture_output=True, check=True).stdout.strip()
assert len(key) == 32
raw = urllib.request.urlopen(S3 + a.profile_path, timeout=20).read()
d = json.loads(base64.b64decode(json.loads(raw)["data"]))
cfg = json.loads(subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-K", key.hex(), "-iv", d["iv"].encode().hex(), "-base64", "-A"],
                                input=d["value"].encode(), capture_output=True, check=True).stdout)
old = cfg[a.doc]
new = dict(old)
new[a.field] = a.value
diff = [k for k in set(old) | set(new) if old.get(k) != new.get(k)]
assert diff in ([a.field], []), diff
print(f"{a.bundle} {a.project}/{a.collection}/{a.doc}.{a.field}: {old.get(a.field)} -> {a.value}  (изменённых полей: {len(diff)})")
if not diff:
    print("уже стоит, ничего не шлю"); raise SystemExit
if not a.send:
    print("сухой прогон, для отправки добавь --send"); raise SystemExit

content = json.dumps(new, ensure_ascii=False, separators=(",", ":"))
secret = subprocess.run(["sudo", "-n", "cat", SECRETS + "firebase-signing.key"], capture_output=True, text=True, check=True).stdout.strip()
payload = {"name": a.doc, "project_id": a.project, "app_name": a.collection, "content": content}
# X-FB-Token = md5(значения полей, отсортированных по имени поля, через ';' + ';' + секрет) — docs/contract.md
sig = hashlib.md5(";".join([payload[k] for k in sorted(payload)] + [secret]).encode()).hexdigest()
req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                             headers={"Content-Type": "application/json", "X-FB-Token": sig}, method="POST")
try:
    r = urllib.request.urlopen(req, timeout=30)
    print(r.status, r.read().decode())
except urllib.error.HTTPError as e:
    print("ОШИБКА", e.code, e.read().decode())
