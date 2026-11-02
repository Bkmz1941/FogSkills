#!/usr/bin/env python3
r"""Переслать в Config Publisher документ, который уже лежит в базе монолита
(application_settings.content), — когда правка в Firebase дошла до монолита, но не до publisher.
Так 2026-10-31 11:40 UTC отправили olimpkz/APISettings (doc 214) для iOS com.olimpRF1.

Содержимое идёт трубой с прода на дев, в чат/терминал не печатается:
  echo "SELECT content FROM application_settings WHERE id=214;" | \
   ssh admin@209.250.237.82 'cd /srv/prod-monolith && docker compose -f compose.prod.yml exec -T mysql \
     sh -c "exec mariadb -N --raw -u\"\$MARIADB_USER\" -p\"\$MARIADB_PASSWORD\" \"\$MARIADB_DATABASE\""' | \
   ssh admin@95.179.244.240 'python3 -I /tmp/pub_send_from_monolith.py APISettings olimp-premium-93c72 olimpkz'
ВНИМАНИЕ: project_id в монолите и в publisher разные (olimp-premium vs olimp-premium-93c72) — брать из config.yml publisher.
"""
import sys, json, hashlib, subprocess, urllib.request, urllib.error

name, project, collection = sys.argv[1:4]
content = sys.stdin.read()
if content.endswith("\n"):
    content = content[:-1]
json.loads(content)  # валидный JSON
secret = subprocess.run(["sudo", "-n", "cat", "/srv/firebase-config-publisher/.secrets/firebase-signing.key"],
                        capture_output=True, text=True, check=True).stdout.strip()
payload = {"name": name, "project_id": project, "app_name": collection, "content": content}
sig = hashlib.md5(";".join([payload[k] for k in sorted(payload)] + [secret]).encode()).hexdigest()
req = urllib.request.Request("https://proxyconfig.aggone.dev/api/firebase/settings", data=json.dumps(payload).encode(),
                             headers={"Content-Type": "application/json", "X-FB-Token": sig}, method="POST")
try:
    r = urllib.request.urlopen(req, timeout=30)
    print(r.status, r.read().decode())
except urllib.error.HTTPError as e:
    print("ОШИБКА", e.code, e.read().decode())
