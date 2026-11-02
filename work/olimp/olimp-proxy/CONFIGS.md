# Конфиги приложений Olimp: где лежит адрес API и как его поменять

Выяснено и проверено 2026-10-31 (инцидент — `INCIDENT-2026-10-31.md`). Скрипты — `scripts/`.
Сменился прокси API → адрес надо поменять ВО ВСЕХ ТРЁХ местах ниже, иначе часть сборок останется на старом.

## Как приложение получает конфиг

```
Firebase (консоль, коллекции документов)
   │  правка документа  ──auto──►  МОНОЛИТ  POST https://api3.ragnaros.net/api/firebase/settings
   │                                 → БД application_settings + JSON-файл + сброс кеша Redis
   │                                 → приложение берёт: POST /api/mobile/v2/settings (через CMS-прокси velmorathion.com)
   │
   └─ ручной синк (инструмент Вовы) ─►  CONFIG PUBLISHER  https://proxyconfig.aggone.dev
                                     → своя копия коллекций (sqlite) → шифрует → S3 Timeweb
                                     → приложение берёт: https://s3.twcstorage.ru/proxyconfig-storage/publisher/...
```

- **Правка в консоли Firebase сама в publisher НЕ приходит.** 31.10 ночная правка дошла только до монолита,
  в S3 сутки висел старый адрес → «у одних работает, у других вечная загрузка».
- Какая сборка куда смотрит, решает код приложения (S3 publisher, монолит, встроенный адрес в сборке;
  по словам Глеба, старые iOS-билды «сначала смотрели в ФБ»). Поэтому чинить все источники.
- Firebase-проект ≠ project_id в монолите: iOS `olimp-premium-93c72` в Firebase/publisher = `olimp-premium` в монолите.

### Поле адреса API

| Приложение | Firebase проект / коллекция | Поле | Где отдаётся |
|---|---|---|---|
| iOS `com.olimpRF1` | `olimp-premium-93c72` / `olimpkz` | `APISettings.direct_api_url` | монолит + publisher (`base`) |
| Android `com.olimp.app` <246 | `olimp-com` / `OlimpCom` | `APISettings.default_api_url` | монолит |
| Android `com.olimp.app` ≥246 | `olimpcom-android-v2` / `OlimpCom` | `default_api_url` | монолит (правило версии) + publisher (`from-246.0.0`) |
| Android `com.olmp.premium.client` ≥246 | `olimpcom-android-v2` / `OlimpPremium2` | `default_api_url` | монолит + publisher; <246 конфига нет (файла `olimp-com/OlimpPremium2` нет) |
| Android `com.osportquiztop.app` | `olimpcom-android-v2` / `SportQuiz` | `default_api_url` | publisher |
| Android `com.olimpRF1.app` | `olimp-com` / `LifeTracker` | `default_api_url` | только монолит |
| QA-сборки | `OlimpComQA`, `OlimpPremium2Qa`, `SportQuizQa`, `LifeTrackerQA` | `default_api_url`, `PaymentsSettings…payment_url` | монолит/publisher |

Прочие поля `APISettings`: `cms_api_urls`/`admin_api_url` — CMS (`velmorathion.com` = прокси на
api.ragnaros.net, сервер `ragnaros-prx165` 83.222.13.165), `proxy_mode: 3`, `proxy_url`,
`trusted_proxy_urls` (XOR+base64, в iOS было `olimpapi.cc/` и `dlyamastera.com`; ключ из 23 байт
восстановлен — см. `olimp-api` SKILL). Иконка Spribe `…/img/spribegames/8.png` ссылается на домен прокси.

## 1. Firebase (источник правды)

Правит человек в консоли Firebase (у Ильи доступ есть: 31.10 сам поменял `default_api_url` android-v2).
Без этого следующий синк Вовы откатит publisher (так и было 31.10 12:10:56 UTC — откатило `com.olimp.app`).

## 2. Монолит (prod 209.250.237.82, `/srv/prod-monolith`)

Только чтение (то, что разрешено без отдельной команды):
```bash
# все APISettings: адреса по приложениям
cat <<'EOF' | ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 admin@209.250.237.82 'cd /srv/prod-monolith && docker compose -f compose.prod.yml exec -T mysql sh -c "exec mariadb --table -u\"\$MARIADB_USER\" -p\"\$MARIADB_PASSWORD\" \"\$MARIADB_DATABASE\""'
SELECT s.id,a.bundle_name,s.project_id,s.app_name,s.updated_at,
 JSON_UNQUOTE(JSON_EXTRACT(s.content,'$.default_api_url')) def, JSON_UNQUOTE(JSON_EXTRACT(s.content,'$.direct_api_url')) dir
FROM application_settings s JOIN applications a ON a.id=s.application_id WHERE s.name='APISettings' ORDER BY s.updated_at DESC;
EOF
# история правок из Firebase (кто/когда прислал): лог storage/logs/app_settings/settings-<дата>.log, строки "incoming request" и "FB Settings store"
# публичный JSON (то же, что отдаёт API): https://api.ragnaros.net/storage/firebase/v2/<project>/<collection>.json
```
- Ответ `/api/mobile/v2/settings` требует подписи (`X-Token` = md5(значения тела по алфавиту ключей `;` + секрет
  `mobile-app.settings.<bundle_>.secret`)), шифруется AES-256-CBC ключом `mobile-app.settings.<bundle_>.encryption_key`.
  Проверка «что реально получает приложение» 31.10 — через `php artisan tinker` на проде (подписать, запросить, расшифровать).
- Кеш: Redis по бандлу+`X-AppVersion`, сбрасывается сам при записи из Firebase (`flushBundleSettings`).
- Запись: штатно — только приход из Firebase. Ручная отправка в `POST /api/firebase/settings` (подпись `X-FB-Token`
  = md5(значения по алфавиту полей `;` + `FB_SETTINGS_SECRET` из `.env`)) 31.10 была ЗАБЛОКИРОВАНА автоклассификатором
  («Remote Shell Writes») — на это нужно явное разрешение Ильи. Правка руками в БД не годится (не обновит JSON-файл).
- **Рецепт записи (31.10, по команде Ильи):** `scripts/mono_replace_host.php` — гонится в tinker контейнера `app`, секрет и подпись считаются внутри, наружу не уходят. Без `SEND=1` — сухой прогон (список вхождений), `IDS=1,2` — только эти строки. Бэкап каждой строки — `storage/app/backup-2026-10-31/application_settings-<id>.json` в контейнере.
  ```bash
  ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 admin@209.250.237.82 'cd /srv/prod-monolith && docker compose -f compose.prod.yml exec -T [-e SEND=1] [-e IDS=…] app php artisan tinker' < scripts/mono_replace_host.php
  ```
  Перед новым переездом прокси поменять в скрипте регулярку старого хоста и новый адрес. Монолит ключует документ по `type_id=1, name, project_id, app_name, application_id`; JSON-файл коллекции собирается из всех строк источника, входящий документ главнее.
- `olimpcom-android-v2` (Android ≥246) вебхуком в монолит НЕ шлёт: копии 16.10 залиты формой admin3 и сами не обновляются. Правка в Firebase этого проекта не доходит ни до монолита, ни до publisher.
- У `com.olmp.premium.client` в монолите документов `olimp-com` нет — только android-v2 по правилу ≥246.
- Флаги: `FEATURE_RELAY_FIREBASE_APPLICATION_SETTINGS_STORE` (пересылка вебхука во второй бэкенд) и `FEATURE_CDN` на проде выключены.

## 3. Config Publisher (Вова, dev 95.179.244.240)

| Что | Где |
|---|---|
| Репо | `git@gitlab.agg.one:firebase-proxy/firebase-config-publisher.git` (ключ Ильи читает), контракт — `docs/contract.md`, команды — `docs/deployment.md` |
| Сервис | `/srv/firebase-config-publisher` (`compose.yml`, `config.yml`, `.env` = `APP_IMAGE`), контейнер `firebase-config-publisher-app-1`, traefik `proxyconfig.aggone.dev` |
| Секреты | `.secrets/` (uid 65532, читать `sudo`): `firebase-signing.key` (подпись входа), `keys/<bundle>.key` (AES 32 байта), `s3-timeweb/` |
| Хранилище | S3 Timeweb `s3.twcstorage.ru`, бакет `proxyconfig-storage`, префикс `publisher`; `index.json` + `configs/v1/<bundle>/<profile>/<publication>.json` и алиас `config.json`, `max-age=300` |
| Админка | `https://proxyconfig.aggone.dev/admin/` — только CDN (вкл/выкл, изменить, проверить, «Синхронизировать») и журнал работ. Редактора конфигов НЕТ |
| Токен админки | `ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 admin@95.179.244.240 'docker cp firebase-config-publisher-app-1:/data/admin-token - \| tar -xO'` (без `IdentitiesOnly` 1Password-агент даёт «Too many authentication failures») |
| Вход данных | `POST /api/firebase/settings` — один документ `{name,project_id,app_name,content}`; `POST /api/firebase/collections` — снапшот `{project_id,app_name,content}` (АВТОРИТЕТНЫЙ: отсутствующие документы удаляются). Подпись `X-FB-Token` как у монолита, секрет — `firebase-signing.key` |
| Переезд | Вова 31.10: «proxyconfig.aggone.dev переедет на новый проект» — пути и сервер могут смениться |

«Синхронизировать» в админке = перезалить в S3 ТО, ЧТО УЖЕ ЕСТЬ у publisher. Из Firebase ничего не забирает.

Команды (всё на деве, `cd /srv/firebase-config-publisher`):
```bash
docker compose exec -T app publisher status               # generation, источники, текущая публикация каждого бандла, pinned
docker compose exec -T app publisher publications list    # история публикаций с датами
docker compose exec -T app publisher rollback --application <bundle> --profile <profile> --publication <id>   # откат (закрепляет)
docker compose exec -T app publisher resume  --application <bundle> --profile <profile>                       # снять закрепление
docker compose exec -T app publisher sync                 # = кнопка «Синхронизировать»
docker logs --since 30m firebase-config-publisher-app-1 | grep -v health   # firebase_request (кто что прислал) и mirror_sync
```

### Рецепт: поменять адрес API в publisher (так делали 31.10)

1. Инвентаризация: `scripts/pub_inventory.py` (на деве) — у кого какой адрес.
2. Бэкап S3-объекта локально: `curl -s https://s3.twcstorage.ru/proxyconfig-storage/publisher/configs/v1/<bundle>/<profile>/config.json -o backup-<bundle>.json`,
   и записать текущий id публикации из `publisher status`.
3. Сухой прогон `scripts/pub_set_field.py … ` без `--send` → должно измениться ровно одно поле.
4. С `--send` → ответ `200 {"status":"stored","remote_delivery":"queued"}`, в логе `firebase_request … result: success`, затем `mirror_sync … success`.
5. Проверка: `scripts/pub_compare.py <bundle> <бэкап> configs/v1/<bundle>/<profile>/config.json` → изменился только `APISettings`.
6. Обязательно поправить то же значение в Firebase, иначе следующий снапшот откатит.

Ловушки:
- Перед отправкой смотреть `docker logs` — если Вова только что прислал снапшот, базу брать из ТЕКУЩЕЙ публикации (скрипт так и делает, но S3 обновляется через ~5 с после приёма).
- Не слать снапшот, собранный из базы монолита: у publisher в `olimpkz` 18 документов, у монолита 17 — снапшот удалил бы лишний.
- `urllib` без `timeout` однажды повис на S3 на 7+ минут — во всех скриптах стоит `timeout`.

## Проверка, что приложения пошли на новый прокси

```bash
ssh olimp-proxy3 'sudo tail -f /var/log/haproxy.log'                       # живьём
ssh olimp-proxy3 'sudo grep -c "COM/24" /var/log/haproxy.log'              # UA приложений: "COM/245.0 (iOS; …)" / Android
curl -s https://api.ipify.org   # свой IP → grep его в логе прокси, чтобы найти свой телефон
```
На телефоне — сниффер (QA пользуются): домены `s3.twcstorage.ru` (конфиг publisher), `velmorathion.com` (CMS), API-домен.
