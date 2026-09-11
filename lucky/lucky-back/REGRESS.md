# Регресс seamless-wallet коллбэков на дев-стенде

Проверяет живой `dev2.api.luckyserver.pro` по всем пяти денежным роутам
`/v1/external/game-provider/*` (player/info, bet, win, cancel, rollback), по
каталогу на `/games` (GET/POST/DELETE/PATCH) и по запуску игры. Скрипт —
`~/.claude/skills/lucky-back/probes/game-provider-regress.mjs`, 38 проверок плюс 2
необязательные, с PASS/FAIL и итоговой строкой; код выхода 1 при любом провале.
Ключи не печатает.
Последний зелёный прогон целиком: 2026-09-10 на деве, `b2ff72a`, **40/40** — вся
цепочка от регистрации игрока до отката, вместе с каталогом (включая `GET /games`)
и веткой `in_use`.

## Что покрыто

| № | Проверка | Ожидание |
|---|---|---|
| 0, 22 | `player/info` до и после | 200, баланс в минорных единицах сходится с расчётом |
| 1–4 | ставка, повтор, повтор с другой суммой, выигрыш | 201 / тот же ответ / 409 `idempotency_conflict` / 201 |
| 5–6 | ставка и отмена | деньги вернулись |
| 7–9 | ставка, откат, повтор отката | `reversed:true`, повтор отдаёт тот же ответ |
| 10–11 | откат неизвестной операции, опоздавшая ставка | 201 `reversed:false`, затем 409 `already_rolled_back` |
| 12 | откат **отмены** | списывает 100 обратно (раньше зачислял второй раз) |
| 13 | откат **выигрыша** | списывает выигрыш |
| 14–15 | лишнее поле в теле | подписано целиком → 400 `invalid_request`; подписаны только известные поля → 401 `invalid_signature` (подпись считается по сырому телу) |
| 16 | сумма из 31 цифры | 400 `invalid_request`, не 500 |
| 17 | битый JSON | 400 `invalid_request` в конверте `{error:{code,message}}` |
| 18–20 | неверная подпись, без заголовков, чужой токен | 401 `invalid_signature`, 401 `missing_signature`, 404 `unknown_session` |
| 21 | пять одинаковых ставок параллельно | один `processedTxId`, списание одно |
| 22a, 29a, 30a | `GET /games`: список до загрузки, после неё и после удаления | `total` растёт на 1 и возвращается назад; новая игра видна с нужными полями |
| 23-24 | `POST /games`: новая игра, затем повтор | `created:1`, затем `updated:1` — сверка идёт по `id` провайдера |
| 25 | `POST /games` с `type: "crash-games"` | 400 `invalid_request`: `type` — категория Lucky (`crash`), а не провайдера |
| 26 | `POST /games` без `cover_url` | 400 `invalid_request`, поле обязательное |
| 27-28 | `PATCH /games` выкл, затем вкл | `is_active` переключается, игра остаётся |
| 29 | `PATCH /games` неизвестного id | 404 `unknown_game` |
| 30 | `DELETE /games` своей игры и несуществующей | `deleted:[своя]`, `not_found:[чужая]`, `in_use:[]` |
| 31 | `PATCH` удалённой игры | 404 `unknown_game` — доказательство, что строка ушла |
| 32-33 | `DELETE` настоящей сыгранной игры (только с `PLAYED_GAME_ID`) | `in_use:[id]`, `deleted:[]`, игра на месте — БД держит её через `ON DELETE RESTRICT` |

## Порядок запуска

1. **Тестовый игрок.** Не гонять на живых игроках: у `test999@agg.one` уже размазана история.
   Зарегистрировать своего через публичный API (нужен `X-Public-Key` проекта BroBro —
   `project_api_keys.key_id` с `key_type='public_client'`, лежит на сервере в `/tmp/probe-pk`):
   `POST /v1/auth/register` `{locale:"en", email, currency:"USD", password, password_confirmation}` →
   `access_token`; id клиента — `GET /v1/core/auth/me` → `client.id`.
2. **Пополнить** через API проект-админа `brobro-admin@luckyserver.pro` (пароль — `lucky-infra/storefront/CONTEXT.md`,
   строкой ниже email): `POST /v1/project/finance/users/<clientId>/transactions`
   `{"direction":"credit","amount":"1000","currency":"USD","balance_code":"cash","comment":"…","is_private":false}`.
   Impersonate рутом не подходит — 403.
3. **Запустить игру** штатно, это проверяет выбор кошелька при launch:
   `POST /v1/core/providers/1/games/7/launch` (Balloon Fly у BroBro) с `X-Public-Key` и Bearer игрока → 201 `{link}`.
   Сессия появится в `game_sessions` с `currency_code`/`balance_code` активного баланса.
4. **Собрать вход на сервере**, не выводя значений: файл `/tmp/probe-input`, три строки —
   `game_providers.public_key`, `game_providers.private_key` (провайдер «Crash Heroes»),
   `game_sessions.launch_token` последней сессии клиента (`closed_at is null`). Удобно SQL-файлом:
   `scp q.sql lucky-dev:/tmp/ && ssh lucky-dev 'docker exec -i luckyserver-dev-postgres-1 sh -c "psql -U \$POSTGRES_USER -d \$POSTGRES_DB -X -q -t -A" < /tmp/q.sql | head -3 > /tmp/probe-input'`.
   Кавычки в SQL через ssh не экранируются — только файлом.
5. **Прогнать**: `scp probes/game-provider-regress.mjs lucky-dev:/tmp/ && ssh lucky-dev 'node /tmp/game-provider-regress.mjs /tmp/probe-input'`.
   Ожидание — `26/26 PASS`. Скрипт можно гонять и локально: `LUCKY_API=http://localhost:18080 node … <input>`.

## Ключи провайдера: откуда их брать (с 2026-09-10)

Раньше вход пробника собирался целиком из БД: `public_key` и `private_key` лежали
в `game_providers` открытым текстом. **Больше нет.** Ключи теперь выпускает Lucky
(кнопка «Generate» на вкладке Integration у провайдера), приватный показывается
**один раз** в момент выпуска, а в базу кладётся зашифрованным
(`v1.<iv>.<tag>.<данные>`, шифр тот же, что у секретов проектов).

Отсюда правило: **после ротации приватный ключ из БД брать нельзя** — там лежит
шифротекст, и подпись по нему не сойдётся. Во входной файл идёт то значение,
которое показала админка при генерации. Публичный ключ по-прежнему читается из БД.

```sql
-- годится всегда
select public_key from game_providers where slug = 'crash-heroes' and is_active limit 1;
-- вернёт секрет ТОЛЬКО у провайдера, которого ещё не ротировали
select private_key from game_providers where slug = 'crash-heroes' and is_active limit 1;
```

Как понять, что провайдер уже ротирован: значение начинается с `v1.`. У такого
провайдера секрет есть только у того, кто нажимал «Generate»; если он потерян —
выпустить заново и вставить новую пару на стороне провайдера.

## Каталог: как гонять и что он трогает

Каталогу сессия не нужна, поэтому его можно гонять отдельно и без запуска игры —
хватает двух строк входа (public_key и private_key провайдера):

```bash
scp probes/game-provider-regress.mjs keys.sql lucky-dev:/tmp/
ssh lucky-dev 'docker exec -i luckyserver-dev-postgres-1 sh -c "psql -U \$POSTGRES_USER -d \$POSTGRES_DB -X -q -t -A" < /tmp/keys.sql > /tmp/probe-input
  ONLY=catalog node /tmp/game-provider-regress.mjs /tmp/probe-input
  rm -f /tmp/probe-input /tmp/keys.sql /tmp/game-provider-regress.mjs'
```

где `keys.sql` — два `select` из `game_providers where slug = 'crash-heroes'`
(`public_key`, затем `private_key`). Без `ONLY=catalog` идёт весь набор, и тогда
нужна третья строка с живым `launch_token`.

Проверки 23-31 мутируют каталог стенда, поэтому работают только со своей
одноразовой игрой `regress-<время>-<число>`: она не привязана ни к одному
проекту, в витрине не видна, и шаг 30 её удаляет. Чужие игры они не трогают —
«удалить игру» на живом стенде необратимо и каскадом снимает её со всех проектов
и из контента. Если прогон упал между 23 и 30, останется игра `regress-*`;
убрать повторным `DELETE /games` с её id либо из рутовой админки, вреда от неё
нет.

Ветку `in_use` (игру уже запускали → не удаляем) честно проверяют шаги 32-33, но
только когда явно задан `PLAYED_GAME_ID`. **Задавать его можно исключительно для
игры, у которой точно есть сессии** — если сессий нет, игра будет удалена
по-настоящему. Проверять заранее, read-only:

```sql
select g.external_id, g.title, count(s.id) as sessions
from game_provider_games g
join game_providers gp on gp.id = g.game_provider_id and gp.slug = 'crash-heroes'
left join game_sessions s on s.game_id = g.id
group by g.external_id, g.title order by sessions desc;
```

На деве 2026-09-10 подходили `1` Balloon Fly (42 сессии), `7` Beer Fest (38),
`6` Booble Jump (37); у восьми игр из пятнадцати сессий не было вовсе.
Шаг 33 оставляет игру включённой, так что для намеренно выключенной игры его
результат надо потом откатить.

## Вариации (проверено на деве 2026-09-10)

Полный прогон 37/37 сделан по такой цепочке, всё через публичный API, без правок в БД:

1. `POST /v1/auth/register` с `X-Public-Key` дев-проекта BroBro
   (`pk_d81-…`, `projects.name = 'BroBro Casino'`, id `39506f3d`), игрок
   `dev-regress-<ts>@luckyserver.pro`, валюта USD.
2. Пополнение **через проект-админа** (`POST /v1/project/auth/login` →
   `POST /v1/project/finance/users/<clientId>/transactions`, credit 1000 USD).
   Мок-депозит игроком (`POST /v1/core/balances/deposit`) на деве **не работает**:
   `TestPay payment provider is disabled` — у дев-проекта провайдер выключен.
3. Два запуска подряд: Balloon Fly (`providers/1/games/7`) и Shark Cage
   (`providers/1/games/11`), оба 201 с живой ссылкой на `dev.games.crash-heroes.com`.
4. Полный пробник на свежей сессии + `PLAYED_GAME_ID=1`.

Отдельный скрипт `probes/game-provider-variations.mjs` проверяет **две живые сессии
одного игрока**. Результат:

- обе сессии видят одного игрока и **один кошелёк**: ставка в сессии B сразу
  меняет баланс, который отдаёт `player/info` сессии A;
- повтор того же `txId` **из другой сессии** возвращает сохранённый ответ (201,
  тот же `processedTxId`), деньги не двигаются второй раз.

Почему так — важно для понимания идемпотентности:

| Что | Значение |
| --- | --- |
| Ключ операции | `game-round:<providerId>:<txId>` — провайдер плюс его `txId` |
| Хеш сверки (`request_hash`) | `projectId`, `clientId`, `currencyCode`, `amount`, `operation` |
| В хеш **не** входят | `session`, `betId`, `roundId`, `betNumber` |

Отсюда два следствия. Повтор из другой сессии того же игрока — это реплей, а не
конфликт. И тот же `txId` с другим `betId`/`roundId`, но той же суммой, тоже
пройдёт как реплей, а не как ошибка: **уникальность `txId` на операцию — забота
провайдера**, мы её не навязываем. Конфликт (`idempotency_conflict`) поднимается
только когда меняется сумма, валюта, игрок, проект или тип операции.

Что на деве проверить не вышло: другая валюта (у проекта BroBro включён только
USD, `project_currencies`) и слот-игра (к проекту подключены 10 игр, все `crash`).
Для этих вариаций надо сначала подключить валюту/игру к проекту — это правка
конфига дева, отдельным решением.

## Ловушки

- Сессия годна TTL (30 мин) плюс ещё один TTL на дорасчёт; дальше все коллбэки отвечают
  `session_expired`. Старый `launch_token` из чужого прогона почти всегда уже мёртв — делай новый launch.
- Каждая ставка продлевает сессию, поэтому прогон подряд не упирается в TTL.
- Повтор операции отдаёт **сохранённый** ответ: сравнивать надо по полям, а не по байтам
  (скрипт сравнивает канонически, порядок ключей неважен).
- `player/info` читает тот же кошелёк, что и расчёты (валюта и код баланса из сессии).
- Скрипт соседней сессии с 11 сценариями лежит на сервере в `/tmp/probe.mjs`; он входит в этот
  скрипт как проверки 1–11, отдельно гонять не нужно.
- Со стороны крашей (`crash-heroes-backend-api-core`, ветка `develop`) после каждой выкатки нужен
  ручной `ssh crash-dev 'cd /home/admin/crashgames/minigames-admin-back && php artisan octane:reload'`,
  иначе воркеры держат старый код. Отката (`/rollback`) у них пока нет вовсе.

## Сквозная проверка «краши → Lucky»

После шага 3 (launch) в ссылке есть `authToken=sess_…` — это сессия крашей. Запрос
`GET https://dev.api.crash-heroes.com/api/app/profile?token_id=<sess>` с `Authorization: Bearer <sess>`
заставляет их бэкенд позвать наш `player/info`; ожидание — 200 с `external_id` = наш client id,
`balance` = зеркало (997 при 99700 минорных) и заполненные `player_id`/`currency` в их
`game_sessions` (`crash-dev`, MySQL, креды в `.env` бэкенда). Адреса коллбэков у крашей лежат в
`projects.api_player_info/api_bet/api_win/api_cancel` (строки 2 и 5 — оба проекта Lucky); при смене
путей у нас их надо обновить там, бэкап строк — в `~/deploy-backups/`.
