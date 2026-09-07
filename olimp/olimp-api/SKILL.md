---
name: olimp-api
description: >
  Бэкенд-монолит «Olimp-api» — CMS и API для мобильных приложений букмекера
  OlimpBet (Laravel 8 + Octane/RoadRunner). Активируй, когда Илья работает с
  репозиторием ~/Documents/Work/Olimp/Olimp-api, доменами api.dev.ragnaros.net
  и api3.ragnaros.net, главным экраном мобилки (viewscreen, секции, топ-матчи),
  сегментами и таргетингом контента, сторис/баннерами/промо/промокодами,
  пушами, интеграциями Kafka (Sportradar SR_SOCCER_TIMELINE), NATS (Hydra),
  Prisma, Segmentator, сервисом goevent, а также деплоем этого проекта через
  GitLab CI. Также по запросам «что с олимп апи», «задеплой олимп»,
  «почему мобилка не видит секцию», «разберись с сегментами».
---

# Olimp-api — CMS и API мобильных приложений OlimpBet

**Репозиторий:** `~/Documents/Work/Olimp/Olimp-api`, основная ветка `master`.

## Про что проект

Монолитный бэкенд, который отдаёт мобильным приложениям OlimpBet весь
управляемый контент — главный экран, сторис, баннеры, промо, топ-матчи,
промокоды, пуши, сплешскрины — и одновременно даёт админский API, через который
контент-менеджеры всё это настраивают. Ключевая идея: **контент таргетируется на
сегменты пользователей**, и мобилка получает свою версию экрана.

## Стек

PHP 8.1 · Laravel 8 · Octane + RoadRunner · MariaDB 10.5 · Redis 6 ·
Kafka (php-rdkafka) · NATS JetStream · Elasticsearch · Docker Compose · GitLab CI.
Плюс отдельный Go-сервис `services/goevent`.

## Ключевые домены

| Домен | Что это |
|---|---|
| **Viewscreen** | Главный экран мобилки. Собирается из секций (`shortcut_small/medium/large`, `promo`, `topmatches`, `informer`, `popup_banner`, `favourite_matches`, `ident_status`). Отдаётся через `GET /api/mobile/main`; `/main/hash` — по нему мобилка инвалидирует свой кеш |
| **Segment** | Таргетинг: `all`, `new only`, `authorized/unauthorized only`, `vip gold/silver/platinum/diamond`, `unknown accounts`, с приоритетами |
| **TopSection / TopMatch** | Топ-матчи; данные из Kafka `SR_SOCCER_TIMELINE` (Sportradar) + веса из goevent |
| **goevent** (Go) | Приём `POST /api/send_event` от мобилки, инкремент весов `olimp:top:match:<id>` / `olimp:top:story:<id>` в Redis DB 1. Заменил легаси v0.41 |
| **Hydra** | Консьюмер NATS (`login`, `cash`, `change_level`) — раскладывает аккаунты по сегментам |
| **Segmentator** | Внешний сервис сегментов, проекты `Olimp COM` и `Olymp CSN/CSW` |
| **Prisma** | Отдельная интеграция: вебвью + Kafka-фрибеты |

## Раскладка кода

```
app/Models/ (152)   домен: Viewscreen, Segment, Story, Banner, TopSection…
app/Http/Controllers/Api/{Mobile,Admin,User,External,Firebase}  (121)
app/Services/ (85)  бизнес-логика по доменам
app/Actions/ (95)   lorisleiva/laravel-actions
app/Cache/, app/Repository/   свои модули (HasCacheModule / HasRepositoryModule)
app/Features/ (18)  фиче-флаги, config/features.php + ENV
app/Modules/        Hydra, Segmentator, PushSender, Localization, RedisLog,
                    RequestAnalyze, Encrypter, UniqLog
routes/api/…        ~100 файлов, версии v2/v3
```

Роуты **не** автоподключаются: всё вручную в `app/Providers/RouteServiceProvider.php`
с префиксами, неймспейсами и middleware (`mobile_token`, `guest`,
`mobile_settings`, `prisma.project.auth`, `analyzable`).

## Деплой

GitLab CI, buildah-сборка → деплой по SSH:

- ветка `dev` → авто → **https://api.dev.ragnaros.net** (`compose.dev.yml`)
- ветка `master` → **вручную** → **https://api3.ragnaros.net** (`compose.prod.yml`)

Сервисы компоуза: `app` (Octane/RR), `goevent`, `queue`, `scheduler`, `mysql`,
`redis`, `mailpit`, `traefik`. Дев-стек локально — `compose.local.yml`.

## Серверы и доступы

> ## ⛔ Правило по серверам
>
> **Любое действие на сервере — только по явной команде Ильи в текущем разговоре.**
>
> Это касается и изменений (установка, правка файлов, рестарт, деплой, чистка),
> и просто захода на сервер с чтением — `ssh`, `docker ps`, `dcps`, чтение логов.
> Разрешение разовое: дали на одно действие — оно не распространяется на
> следующее и не переносится на другой сервер.
>
> Общая формулировка вроде «разберись», «почини», «поддерживай в порядке»
> разрешением НЕ является. Если для задачи нужен сервер — сначала спросить,
> назвав конкретный сервер и конкретную команду.
>
> Установлено 2026-09-07.

| Сервер | Роль | Доступ |
|---|---|---|
| **95.179.244.240** (`vultr`, Debian 11 bullseye) | **дев** — api.dev.ragnaros.net | `ssh -i ~/.ssh/id_ed25519 admin@95.179.244.240`. Проверено 2026-09-07: заходит, `docker` доступен без sudo |
| прод — api3.ragnaros.net | боевой | IP и доступ ещё не записаны |

Алиаса в `~/.ssh/config` пока нет — ходить по IP с явным ключом.

### Дев-сервер: что где

Стек монолита живёт в **`/srv/dev-monolith`**, compose-файл
`/srv/dev-monolith/compose.dev.yml`, образ тянется из
`registry.agg.one/old-cms/monolith`. Проект в docker compose называется
`old-cms-dev`, контейнеры: `app`, `queue`, `scheduler`, `goevent`, `mysql`,
`redis`, `mailpit`; наружу 80/443 держит общий `traefik`.

**На этой же машине стоят другие проекты** — `proxy-server-dev` (app-1/app-2),
`admin-v1-dev`, стек наблюдаемости `proxy-server-observability-development`
(grafana, loki, alloy). Не задевать при работе с монолитом.

### `dcps` — короткий docker ps

На сервере лежит **`/usr/local/bin/dcps`** (root:root, 755): `docker ps` с
колонками «id, имя, статус, внутренний IP, порты, образ». Рядом `dci` — `docker images`. Аргументы пробрасываются,
работает и в неинтерактивном ssh.

```bash
ssh -i ~/.ssh/id_ed25519 admin@95.179.244.240 dcps
ssh -i ~/.ssh/id_ed25519 admin@95.179.244.240 'dcps --filter name=old-cms'   # только монолит
ssh -i ~/.ssh/id_ed25519 admin@95.179.244.240 'dcps -a'                      # со стоппнутыми
```

Исходник и инструкции по установке — в скиле **`scripts`**
(`~/.claude/skills/scripts/bin/dcps`). Правки вносить там, потом раскатывать
копию сюда, иначе версии разъедутся.

### Сети дев-сервера

| Подсеть | Что это |
|---|---|
| `172.19.x` | внутренняя сеть стека `old-cms-dev` |
| `172.18.x` | общая проксируемая сеть traefik |
| `172.20.x` | стек наблюдаемости (grafana, loki, alloy) |

Контейнеры, которые торчат наружу через traefik, **сидят в двух сетях сразу** и
имеют два IP — например `old-cms-dev-app-1` = `172.19.0.8` + `172.18.0.6`.
Поэтому в `dcps` адреса перечислены через запятую.

Скрипт общий для всей машины — им пользуются и соседние проекты на этом
сервере, не только Olimp. На проде его нет.

## `kafka-reader` — сервис чтения топиков win/cash

Начат 2026-09-07. Отдельный контейнер со **своим образом**
(`docker/kafka-reader/Dockerfile`), по образцу `goevent`. Общий образ
`app`/`queue`/`scheduler` не трогает: RoadRunner и медиа-утилиты
(ffmpeg, imagemagick, оптимизаторы) выкинуты, добавлен supervisor.

Внутри контейнера supervisor держит **два процесса — по одному на топик**,
чтобы вал по `BET_COM` (расчёт ставок, выигрыши) не создавал отставания
для редкого `CASH_COM` (пополнения). Это важно: в хендлерах есть фильтр
«сообщение не старше 15 минут», поэтому отставание не задерживает пуш,
а молча его выбрасывает.

| Что | Где |
|---|---|
| конфиг кластера | `config/kafka.php` (`kafka.reader`) |
| читатель | `app/Services/Kafka/KafkaReader.php` |
| команды | `app/Console/Commands/kafka/reader/` → `kafka:read-bet-com`, `kafka:read-cash-com` |
| supervisor | `docker/kafka-reader/supervisord.conf` |
| логи | каналы `kafka_reader_bet_com` / `kafka_reader_cash_com` → `storage/logs/kafka/reader/` |
| CI | job `build-kafka-reader`, переменная `KAFKA_READER_IMAGE` |

**Этап на сейчас:** читатель только пишет в лог всё, что пришло. Фильтров,
дедупа и диспатча в очереди пока нет — они появятся, когда станет понятен
реальный формат сообщений.

Решения, которые легко случайно сломать:

- `group.id` **не задаётся переменной**, а собирается в `KafkaReader` как
  `KAFKA_READER_GROUP_PREFIX` + имя топика (`…​.bet-com`, `…​.cash-com`).
  Поэтому оба процесса читают одну переменную, а группы разные — и это
  переживает `config:cache`. Не переносить сборку группы в конфиг.
- `auto.offset.reset=latest`. У легаси-сервиса `smallest` — при новой группе
  он перематывает топик с начала ретеншена.
- На деве нельзя ставить прод-группу `api.ragnaros.net.group2` — дев отберёт
  у прода партиции.
- **Сертификаты в репозитории не хранятся.** Путь к папке на хосте —
  `KAFKA_READER_CERTS_PATH`, монтируется read-only в фиксированную точку
  `/home/kafka/certs`, куда и смотрят `KAFKA_READER_SSL_*_LOCATION`.
  Локально у Ильи — `~/.olimp/certs/kafka`, на сервере — `/srv/secrets/kafka`.
  Префикс `KAFKA_*` без `READER` занят легаси-читателем `SR_SOCCER_TIMELINE`
  (`ContextKafka`, порт 9093, сертификаты в `/home/kafka/cert`) — не путать.
  Внутри образа пользователь `app` = **uid 999**, файлы должны принадлежать ему.
  Клиентский сертификат `CN=push-new` годен до 20.02.2027.

## `Olimp-api-redis` — панель по очередям Redis

Отдельный проект: **`~/Documents/Work/Olimp/Olimp-api-redis`**. Дебаг-панель на Go
(один бинарь, UI вшит через `go:embed`, образ 14 МБ — как у `goevent`).
Только читает, ничего не пишет и задачи из очередей не снимает.

Показывает по каждой очереди `ожидают / отложены / в работе` (ключи Laravel
`queues:<name>`, `:delayed`, `:reserved`), скорость роста Δ/сек, спарклайн на 60
точек и сводку по Redis. Клик по очереди разворачивает ближайшие 10 задач с
разобранным `displayName`. Вкладки в шапке переключают Redis: `local` / `dev`.

### Запускать по просьбе Ильи — командами ниже

Дев-Redis наружу не опубликован, живёт только в docker-сети сервера, поэтому
нужен ssh-туннель. IP контейнера меняется при пересоздании — `tunnel.sh` узнаёт
его на месте сам.

```bash
cd ~/Documents/Work/Olimp/Olimp-api-redis
./tunnel.sh          # фоном: 127.0.0.1:6390 → old-cms-dev-redis-1:6379
./olimp-api-redis    # фоном: http://127.0.0.1:8091
```

Обе команды долгоживущие — запускать в фоне. Если правился `main.go` или
`web/index.html`, сперва `go build -o olimp-api-redis .`.

- **только локальный Redis** — достаточно второй команды, вкладка `dev` просто
  не ответит;
- **дев** — нужны обе;
- остановить: `pkill -f 'olimp-api-redis$'` и `pkill -f '\-N \-L 6390'`.

### Настройки

`targets.json` (в git не попадает, шаблон `targets.example.json`):

| таргет | адрес | префикс ключей |
|---|---|---|
| `local` | `127.0.0.1:6381` | `olimp_api_local_database_` |
| `dev` | `127.0.0.1:6390` (туннель) | `olimp_admin_com_database_` |

Порт панели — `8091`. На 8090 у Ильи сидит какой-то питон, туда не вставать.

### Ловушки

- Туннель привязан к текущему IP контейнера. Пересоздали дев-стек — перезапустить
  `tunnel.sh`.
- Redis 6.0 не принимает `INFO memory clients` двумя секциями сразу (это Redis 7+),
  в коде запросы разнесены. Не «упрощать» обратно.
- Панель показывает payload задач — публиковать наружу без `AUTH_USER`/`AUTH_PASS`
  нельзя.

## Ловушки

- **Слоёв больше, чем нужно**: `Services` + `Actions` + `UseCases` + `Repository`
  + `Cache`. Правила «что куда» неочевидны — смотри соседний код того же домена.
- **Фиче-флагов ~30** (`FEATURE_*` в `.env`). Прежде чем чинить поведение,
  проверь, не закрыто ли оно флагом.
- `Api/Mobile/Viewscreen/ViewscreenController` возвращает захардкоженный JSON
  «for postman» — это заглушка. Боевой путь — `MainController`.
- Тестов мало (~13 файлов: Hydra, Kafka, Mobile v2 auth/store, main eager load).
  Шпаргалка запуска — `Tests.md` в корне репо.

## TODO

- [ ] Записать прод: IP, доступ, раскладку стека (сейчас известен только домен
      api3.ragnaros.net).
- [ ] Завести ssh-алиасы `olimp-dev` / `olimp-prod` в блоке work-skills
      `~/.ssh/config`.
- [ ] `kafka-reader` локально: в `compose.local.yml` сервиса нет. Локальные
      пути к сертификатам в `.env` рассчитаны на запуск `php artisan
      kafka:read-bet-com` прямо на машине. Чтобы гонять в докере локально,
      нужен сервис в `compose.local.yml`, и там всплывает uid: локальный образ
      собирается под `LOCAL_UID=1000`, образ читателя — фиксированно под 999,
      поэтому `privkey.pem` с правами `0600` контейнер не прочитает. Решать
      либо прокидыванием `LOCAL_UID`/`LOCAL_GID` в
      `docker/kafka-reader/Dockerfile`, либо отдельным локальным сервисом на
      базе локального образа.
- [ ] Дополнять по мере работы: типовые runbook'и, разбор инцидентов.
