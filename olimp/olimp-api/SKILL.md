---
name: olimp-api
description: Бэкенд «Olimp-api» — CMS и API мобилки OlimpBet (Laravel 8 + Octane), репо ~/Documents/Work/Olimp/Olimp-api, api.dev.ragnaros.net и api3.ragnaros.net: главный экран, сегменты, сторис, пуши, Kafka/NATS, деплой. По «что с олимп апи», «задеплой олимп».
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

Пуш в `dev` обновляет **все** сервисы: монолит (`app`+`goevent`), `push-service`,
`kafka-reader`. Сузить набор — переменной `ONLY` (список через запятую,
значения `app`, `push-service`, `kafka-reader`):

```bash
git push -o ci.variable="ONLY=kafka-reader"
git push -o ci.variable="ONLY=kafka-reader,push-service"
```

`app` означает пару монолит + goevent: они деплоятся одной job'ой
`deploy-development` и тегируются одним `$CI_COMMIT_SHA`, врозь не собираются.

**Ловушка тегов (решение Ильи от 2026-09-08 — оставить как есть).**
`push-service` и `kafka-reader` тегируются НЕ по SHA, а по своим
`docker/*/VERSION`. С появлением prod-job (ветка `master`) дев и мастер пишут в
один и тот же тег: сборка с любой ветки без бампа `VERSION` молча подменяет
содержимое `kafka-reader:1.1.0` сразу на обоих окружениях. Обсуждали переход на
`$CI_COMMIT_SHA` — Илья решил не менять, поэтому **правило: меняешь сервис —
бампай его `VERSION`**, иначе на деве и проде окажется разный код под одним тегом.
`deploy-kafka-reader` и `deploy-push-service` ждут `deploy-development`
(`needs … optional: true`), чтобы миграции успели проехать до рестарта сервисов.

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
| **209.250.237.82** (`ragnaros`, Debian 11 bullseye) | **прод** — api3.ragnaros.net, api.ragnaros.net | `ssh -i ~/.ssh/id_ed25519 admin@209.250.237.82`. Проверено 2026-09-08: заходит, `docker` без sudo. `dcps` там **нет** |

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
сервере, не только Olimp. С 2026-09-08 `dcps` и `dci` стоят и на проде
(`209.250.237.82`, те же `/usr/local/bin`, root:root 755).

### Прод-сервер: что где

Стек монолита — **`/srv/prod-monolith`** (`compose.prod.yml`, `.env`,
`.olimp-platforms.json`), проект docker compose `old-cms-prod`, образ
`registry.agg.one/old-cms/monolith`. Контейнеры: `app`, `goevent`, `queue`,
`scheduler`, `mysql` (mariadb 10.5.29), `redis` (6.0.16). Наружу 80/443 держит
общий `traefik`.

**`push-service` и `kafka-reader` на проде подняты** (с 2026-09-08, проверено
2026-09-10): `old-cms-prod-push-service-1` образ `push-service:1.0.1`,
`old-cms-prod-kafka-reader-1` образ `kafka-reader:1.1.5` (с 2026-09-10, фикс
потерь и дублей — см. раздел ридера). Прод-деплой этих сервисов — ручные job'ы
`deploy-kafka-reader-production` / `deploy-push-service-production` в пайплайне
ветки `master`; локально `glab` и токена GitLab нет, кнопку жмёт Илья.
Лимит памяти у обоих контейнеров 512 МБ, ридер ест ~300 МБ.

`queue` крутит одну общую очередь: `php artisan queue:work redis --sleep=1
--tries=3 --timeout=300` (без `--queue`). Префикс ключей Redis —
`olimp_admin_com_database_`, тот же, что на деве.

Как сейчас работают пуши на проде — легаси: в `.env` есть `KAFKA_WINCASH_*`
(brokers, group, сертификаты) и `PUSH_SENDER_*` (`ACTIVE_CHANNEL=rest`,
`REST_URL`, `WIN_REST_LOG`, `CASH_REST_LOG`). `KAFKA_WINCASH_*` в коде монолита
не используется — это конфигурация внешнего сервиса-пушера.

**На этой же машине живут другие проекты** — `prod-proxy-server-bff`
(app-1/app-2), `admin-v1-prod`, `proxy-server-observability-production`
(grafana, loki, alloy). Не задевать.

Ресурсы на 2026-09-08: диск 150G занято 34%, RAM 7.8G (3.3G занято), uptime 39 дней.

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
| тест пушей | `kafka:produce-win` / `kafka:produce-cash` пишут синтетические события
  в `BET_COM` / `CASH_COM` (`--topic` переопределяет, `--dry-run` только печатает,
  боевые топики спрашивают подтверждение). `kafka:test-win` гоняет выигрыш через
  правила ридера без Kafka. Продюсер — `app/Services/Kafka/KafkaProducer.php`,
  пейлоады — `app/Services/Kafka/Fixtures/`, конфиг `kafka.producer` (наследует
  брокеры и сертификаты ридера), лог-канал `kafka_producer` |

**Главная причина ребалансов — старая librdkafka (2026-09-08).** В образе
`kafka-reader` библиотека ставилась пакетом `librdkafka-dev` из bullseye, то есть
**1.6.0** (2021 год). На соединении к брокерам через порт 443 (за балансировщиком,
который молча рвёт простаивающие сессии) её брокерский поток уходил в busy-loop
реконнектов: `rdk:broker-1` съедал целое ядро, heartbeat не укладывался в
`session.timeout.ms`, партиции отбирались, чтение стояло. `CASH_COM` с его редким
потоком в ловушку не попадал, `BET_COM` — сразу.

Лечение — сборка **librdkafka 2.3.0** из исходников в `docker/kafka-reader/Dockerfile`
плюс `php-rdkafka 6.0.5`, версия образа поднята до `1.1.0`. Эффект на деве:
CPU ридера 95% → 1%, `rdk:broker-1` 23 694 тика → 2, отставание 76 минут → 18 секунд,
ребалансы прекратились. Диагностика, которая это показала: разложить CPU по потокам
процесса (`/proc/<pid>/task/*/stat` + `comm`) — видно, что жжёт не PHP, а librdkafka.

Заодно в консьюмер добавлены `socket.keepalive.enable=true` и
`socket.timeout.ms` (30 с, `KAFKA_READER_SOCKET_*`) — против тех же полумёртвых
соединений через 443.

**Партиционирование тестовых сообщений (2026-09-08).** librdkafka по умолчанию
считает партицию по CRC32 (`partitioner=consistent_random`), а боевой Java-продюсер
— по murmur2. Один и тот же ключ уводил синтетику в другую партицию: `CASH_COM`
боевой лежит в партиции 2 (все пополнения пишутся с фиксированным ключом `CASH`),
а наши тесты улетали в пустую 5-ю, где ридер их не находил до истечения
15-минутного фильтра свежести. Лечится строкой в `KafkaProducer`:
`$conf->set('partitioner', 'murmur2_random')`. У `BET_COM` ключ — `card_id`,
уникальный, поэтому win-события равномерно расходятся по всем шести партициям —
это нормально. На крайний случай у команд есть `--partition=N`.

**Залипание ридера и группа (разобрано 2026-09-10, решение Ильи: группу при
рестарте НЕ менять).** Координатор группы выбирается по хэшу `group.id`; если он
на проблемном брокере, консьюмер не получает ответ на `FindCoordinator`/
`Heartbeat` по 60–70 с при живом TCP: партиции назначены, чтения нет. В
`KafkaReader::restartOnStall` есть сторож: партиции есть, сообщений нет
`KAFKA_READER_STALL_TIMEOUT_SEC` (90 с) → `reader.stalled_restart` и `exit(1)`,
supervisor поднимает процесс заново. До 1.1.5 рестарт ещё и инкрементил
поколение группы в Redis (`kafka:reader:generation:<bet-com|cash-com>` с
Laravel-префиксом → `group.id` получал суффикс `.g34`), новая группа стартовала
с `latest`, и всё, что пришло за время залипания, терялось навсегда: на проде
10 слепых окон по 2–12 минут за 10 сентября (по 236–279 сообщений на партицию
за один рестарт), 21 окно за 9 сентября. Так пропал win-пуш тестировщика
(логин 39559350 — событие вообще не дошло до ридера). С 1.1.5 рестарт идёт с
той же группой и продолжает с закоммиченного офсета. Поколение осталось только
как ручной рычаг: `INCR olimp_admin_com_database_kafka:reader:generation:bet-com`
(на проде на 2026-09-10 bet-com = 36, cash-com = 12) или смена
`KAFKA_READER_GROUP_PREFIX` — оба означают старт с `latest` и потерю хвоста.
Ключ читается только при старте процесса; после `INCR` ридер уйдёт на новую
группу на ближайшем рестарте сторожа (≤2 мин, если стоит) или после
`supervisorctl restart`.

**Ловушка «той же группы» (2026-09-10, 13:13–13:32 UTC, прод стоял 19 минут).**
Сразу после выкатки 1.1.5 `BET_COM` встал: партиции назначаются, сообщений нет,
сторож перезапускает процесс с той же группой раз в ~95 с — и так 7 раз подряд
без единого сообщения, пока `CASH_COM` в соседнем процессе читал нормально.
В stderr контейнера — `Timed out FetchRequest in flight (after ~30000ms)` ко
всем брокерам. Объяснение: с той же группой ридер возобновляет чтение с
закоммиченного офсета, то есть с отставанием; fetch-ответы растут до
`fetch.message.max.bytes` (1 МБ) на партицию и на сетевом пути прод-хоста не
успевают за `socket.timeout.ms=30000`. Старый код «лечил» это переходом на
новую группу с `latest` — маленькие ответы с хвоста топика. Расклинили вручную
`INCR` поколения (35 → 36) через туннель панели. Лечение в 1.1.6:
`fetch.message.max.bytes` = 64 КБ (`KAFKA_READER_FETCH_MESSAGE_MAX_BYTES`),
чтобы хвост дочитывался мелкими порциями, плюс предохранитель в стороже:
счётчик `kafka:reader:stalls:<topic>` (TTL 1 ч, сбрасывается первым
прочитанным сообщением), на **третьем** подряд рестарте без прогресса
поколение поднимается автоматически — лучше потерять хвост, чем стоять.
`KAFKA_READER_DEBUG` (например `cgrp,broker,fetch`) включает отладку
librdkafka в stderr.

С машины Ильи оба пути к брокерам чистые: два локальных ридера через 443 и
через 9093 за 7 минут — 0 таймаутов, 0 ребалансов; локальный ридер через 443 с
fetch 1 МБ разгрёб 10-минутный хвост (4 238 сообщений) за 6 секунд. Значит
размер fetch сам по себе не беда, беда — сетевой путь прод-хоста. PMTU в
норме (1472 байта с DF проходят), ICMP без потерь, RTT 35–38 мс ровный.

**Диагноз по TCP-счётчикам (2026-09-10 13:46 UTC).** В сетевом пространстве
контейнера ридера `/proc/net/snmp`: `RetransSegs` 30% от `OutSegs`,
`/proc/net/netstat`: `TCPTimeouts` 5 319, `TCPLostRetransmit` 4 143,
`TCPFastRetrans` 0 — то есть только RTO-таймауты, ни одного fast retransmit:
ACK от брокеров периодически не приходят вовсе. Потери постоянные (~25 повторов
на ~50 сегментов каждые 10 с), не всплесками. В `/proc/net/tcp` десятки
соединений к 185.232.107.209/.210/.211:9093 висят в FIN_WAIT1 с `retrnsmt`
7–8, живых 6. Соседи на хосте здоровы (`app` 0.1%, `push-service` 0%,
`queue` 0%), но **никто кроме ридера с брокерами не общается**: у `app`,
`queue`, `scheduler` нет соединений на 9093 (легаси `ContextKafka` там не
крутится), `app` держит только 138.226.234.x:443. Conntrack 1 940/262 144,
MTU 1500 везде, sysctl netns одинаковые. Так что «9093 с этого хоста
работает» ничем не подтверждено, а дев и локалка ходят через 443 и живут.
Диагностика без `ss` в образе: `cat /proc/net/tcp` (колонка
`retrnsmt`), `grep ^Tcp: /proc/net/snmp`, `grep ^TcpExt: /proc/net/netstat`.

**Порт ни при чём (проверено 2026-09-10 14:11).** Дев, как выяснилось, тоже
ходит на 9093 и болеет так же: 31% ретрансмитов, 23 залипания и 362
ребаланса за день. Прод перевели на `…:443` (пересоздан на 1.1.5, потому что
`docker compose pull` с хоста упал: логин в registry живёт только внутри
CI-джобы) — в новом контейнере те же 26% ретрансмитов и залипание через две
минуты. С машины Ильи оба порта разгребают 10-минутный хвост с fetch 1 МБ за
секунды (700+ сообщений на партицию в одном ответе). Итог: теряет путь
**Vultr → mgr.com.ru** как таковой, независимо от порта; похоже на
шейпинг/полисинг потока (мелкий трафик с хвоста топика проходит, устойчивый
поток с отставанием ложится). Лечить надо путём: другой хост/сеть для ридера
или разбор с владельцами Kafka, а не параметрами клиента.

**Как 1.1.6 живёт на этом пути (дев, 13:50–14:14).** Два рестарта с той же
группой хвост не разгребли даже порциями по 64 КБ, третий поднял поколение
(`restarts_without_progress: 3, next_generation: 34`), и дальше 16 минут
ровного чтения вровень с топиком. То есть на Vultr возобновление с отставания
не работает в принципе; предохранитель превращает вечный стояк в ~5 минут
простоя плюс потерю хвоста (который фильтр свежести 15 мин и так почти весь
выбросил бы). Без 1.1.6 (как на проде в 13:48–14:17) ридер стоит, пока не
сделать `INCR` поколения руками и `supervisorctl restart bet_com` в контейнере.

**Окно старта (1.1.8, идея Ильи).** При каждом назначении партиций ридер
сравнивает закоммиченный офсет с офсетом на момент `now − KAFKA_READER_MAX_LAG_MINUTES`
(`offsetsForTimes`, по умолчанию 5 мин) и стартует с более позднего; партиция
без сообщений внутри окна стартует с конца. Лог — `reader.start_offsets_capped`
(`from` → `to` по партициям), при ошибке запроса — `reader.offset_lookup_failed`
и обычный старт. Смысл: всё старше 15 минут фильтр свежести и так выбросит, а
длинный хвост на пути Vultr → брокеры не разгребается никогда; с окном рестарт
стоит максимум N минут перечитывания, а новая группа после предохранителя
начинает с последних N минут, а не с `latest`. `auto.offset.reset=latest`
остался только запасным вариантом. Проверено локально: отставание 1.5 ч →
старт с `now − 4:54`, 2 250 сообщений догнаны за 15 с.

**Дыра сторожа до 1.1.7:** `partitions_assigned` сбрасывал `lastProgressAt`,
а ребалансы на этом пути идут каждые 1–2 минуты, поэтому 90 секунд «без
прогресса» могли не набираться никогда, и застрявший ридер даже не
перезапускался (прод 14:13–14:17: два назначения подряд, ни одного
сообщения, ни одного рестарта). В 1.1.7 (`6a96d343`) таймер ставится на
первом назначении и двигается только прочитанными сообщениями.

**Ребалансы каждые 1–4 минуты — фон прода, не залипание.** 290 revoke за
сутки в `BET_COM`, 166 в `CASH_COM`, CPU ридера при этом ~2%, так что это не
busy-loop, а рвущиеся соединения к брокерам (сессия 45 с истекает, партиции
отбирают и тут же возвращают тому же единственному члену). Внутри группы
сообщения не теряются, но после каждого ребаланса перечитываются последние
18–44 на партицию — до 1.1.5 это давало дубли пушей: 973 из 4889 win-пушей
за 10 сентября ушли дважды. С 1.1.5 диспатч защищён
`AbstractTopicReadCommand::isReplay` — `SET NX` в Redis по ключу
`kafka:reader:dispatched:<topic>:<partition>:<offset>` с TTL 1 ч, повтор
логируется как `reader.replay_skipped`. Ключ пишется только для сообщений,
дошедших до диспатча (~16 тыс./сутки), поэтому Redis не пухнет. `kafka:test-win`
подставляет уникальный offset, чтобы не считаться повтором. Причина самих
обрывов не найдена — см. TODO.

**Ловушка ридера (разобрана 2026-09-08):** в холостых ветках `consume()`
не было паузы, поэтому при отсутствии партиций цикл крутился на 100% ядра.
На двухъядерном деве два ридера съедали 122% CPU, фоновым потокам librdkafka
не хватало времени, heartbeat не укладывался в `session.timeout.ms=45000` —
координатор отбирал партиции, и цикл повторялся: 233 ребаланса за сутки и
отставание в час, которое не сокращалось. Лечится двумя правками в
`KafkaReader`: `usleep(100ms)` в ветках EOF/таймаутов и трактовка `-166`
(`__TIMED_OUT_QUEUE`) как таймаута, а не фатальной ошибки. Сеть при этом была
исправна — проверено (ping 34 мс, коннект 86 мс, потерь нет), симптомы
`REQTMOUT`/`SESSTMOUT` в stderr контейнера были следствием CPU-голодания.

**Что делает ридер сейчас.** `BetComReadCommand`: пишет сырое сообщение в лог
(`KAFKA_READER_LOG_MESSAGES`), затем диспатчит `PrepareWinPushJob` в очередь
`push-win`, если это выигрыш (`pay_sum > 0` и `pay_sum > bet_sum`, без кэшаута,
`card_number` не `user-SPORTGAMES…`), сообщение не старше 15 минут и это не
повтор офсета. Пуша за саму ставку нет — только по факту расчёта выигрыша.
`CashComReadCommand` то же для пополнений (`reason` = deposit) → `push-cash`.
Разбирать «пуш не пришёл»: `grep <логин>` в `storage/logs/kafka/reader/bet-com-*.log`
внутри контейнера ридера, потом `storage/logs/push/win-*.log` в пуш-сервисе.
Нет в логе ридера — событие до ридера не дошло (не рассчитано / слепое окно).
Есть `push.win.prepared` с `sending` — причина отказа там; `push.win.sent` с
`result.status = NOT_FOUND` — токен FCM протух.

Решения, которые легко случайно сломать:

- `group.id` **не задаётся переменной**, а собирается в `KafkaReader` как
  `KAFKA_READER_GROUP_PREFIX` + имя топика (`…​.bet-com`, `…​.cash-com`).
  Префиксы: локально `olimp.com.local`, дев `olimp.com.dev`,
  прод `olimp.com.prod5` (плюс суффикс поколения из Redis, см. выше).
  Смена префикса = новая группа = чтение с `latest`,
  то есть штатный способ обнулить накопленное отставание.
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
| `prod` | `127.0.0.1:6391` (туннель) | `olimp_admin_com_database_` |

`tunnel.sh` берёт таргет аргументом: `./tunnel.sh dev` (порт 6390) или
`./tunnel.sh prod` (порт 6391), без аргумента — дев. Панель только читает,
на прод-Redis ничего не пишет.

Порт панели — `8091`. На 8090 у Ильи сидит какой-то питон, туда не вставать.

### Языки, бандлы и FCM-проекты

Язык пользователя known: `accounts.lang_id` (дублируется в
`account_devices.lang_id`), справочник — таблица `banner_langs`:
`0 ru, 1 kk, 2 en, 3 cn, 10 kg, 22 uz`, все активны. На проде (1.37 млн
аккаунтов) язык распределён так: ru — 1 336 486 (97.4%), kk — 27 940, en — 4 894,
uz — 1 266, cn — 1 041; плюс мусорные коды, которых нет в справочнике
(11 — 24 аккаунта, 23 — 21, 14 — 10, 6 — 4, 9 — 1), для них нужен фолбэк.
Валюты: KZT 1 305 136 (95%), RUB 46 949, USD 5 554, KGS 5 182, UZS 2 953,
EUR 2 794, Virtual 2 124, UAH 487. То есть аккаунт почти всегда казахстанский,
а интерфейс почти всегда русский.

Тексты win/cash-пушей локализованы: `config/push.php` → `locales` (маппинг
lang_id → локаль), строки — `resources/lang/{ru,kk,en}/push.php`,
`PushMessage` рендерит через `trans(..., $locale)`. Для cn/kg/uz файлов нет,
Laravel отдаёт русский (`app.fallback_locale = ru`). `SetLocale` middleware
сознательно **не** трогаем — у него свой маппинг для HTTP-запросов.

### Бандлов много, а FCM-креденшл один

`accounts.bundle_id` на проде: `com.olimpRF1` — 705 944, `com.olimp.app` —
656 705, `com.olimp.prem2` — 5 293, `com.olmp.premium.client` — 2 204,
`com.arcanite.Olimp` — 964, `com.olimp.app.qa` — 222 и хвост.

В таблице `applications` у каждого бандла свой Firebase-проект (`fb_proj`,
`sender_id`), и проектов несколько:

| fb_proj | sender_id | примеры бандлов |
|---|---|---|
| `olimp-com` | 8 | `com.olimp.app` (default), `com.olimpRF1.app` (android), `com.asiabet.bet`, `com.olmp.premium.client` |
| `olimp-premium` | 4 | `com.olimpRF1` (**ios**), `com.olimppremium2` |
| `olimp-ios` | 3 | `com.olimpbetkz` |
| `olimpcs-f0eb6` | 14 | `com.olympcsn.app`, `com.olimpRF2.app`, `com.oplatinum.mobile.android` |
| `sportquizfake` | 8 | `com.osportquiztop.app` |
| `null` | — | `com.olimp.matchcenter`, `com.olimpbar.app1029`, `com.olimp.soccer` |

#### Как выбирается ключ

`config('push.fcm.apps')` — карта `бандл → платформа → проект`. В неё вносим
**только те бандлы, под которые реально есть ключ** (сама раскладка бандлов по
проектам берётся из прод-таблицы `applications`, поле `fb_proj`). Нет ключа —
нет записи, и джоба напишет `no fcm project for …`. Резолв —
`FcmSender::project($device->bundle_id, $device->platform)`; платформа
нормализуется, `IOS1`/`ANDROID7` из `account_devices` превращаются в
`ios`/`android`. Файл ключа — `{FCM_CREDENTIALS_PATH}/{проект}.json`,
`FCM_CREDENTIALS_PATH` теперь **каталог** (в контейнере `/home/fcm`), а не файл.

Раскладка секретов — каталог монтируется в `/home/fcm` read-only, новый проект
= положить ещё один файл, кода не трогать:

| где | путь | владелец, права |
|---|---|---|
| локально | `~/.olimp/certs/fcm/<проект>.json` | `ilya`, каталог 700 / файлы 600 |
| дев | `/srv/dev-monolith/secrets/fcm/` | uid **999**:admin, каталог 750 / файлы 640 |
| прод | `/srv/prod-monolith/secrets/fcm/` | uid **999**:admin, каталог 750 / файлы 640 |

uid 999 — это пользователь `app` внутри образов `push-service` и `kafka-reader`
(на хостах он отображается как `systemd-coredump`). Локально работает схема
«700 + владелец ilya» только потому, что в `compose.local.yml` сервис бежит под
`${LOCAL_UID:-1000}`; на серверах `user:` не задан, поэтому файлы кладём от 999.

Оба ключа (`olimp-premium.json`, `olimp-com.json`) на 2026-09-08 разложены на
всех трёх площадках, md5 сверены.

**Порядок выкатки FCM на дев** — два действия должны идти вместе с деплоем кода,
не раньше:
1. в `/srv/dev-monolith/.env` заменить `FCM_CREDENTIALS_PATH=/home/fcm/service-account.json`
   на `/home/fcm` (каталог);
2. удалить осиротевший `secrets/fcm/service-account.json`.

Пока код на деве старый, он читает именно `service-account.json`, поэтому файл
оставлен намеренно. Если поменять `.env` заранее, `is_readable()` на каталоге
вернёт true, чтение даст мусор и джоба свалится в failed — тихой деградации не
будет, но пуши встанут.

**Прод подготовлен 2026-09-08**: создан
`/srv/prod-monolith/secrets/` (750, 999:admin), в нём `fcm/` с
`olimp-premium.json` + `olimp-com.json` и `kafka/` с `CARoot.pem`,
`certificate.pem`, `privkey.pem` — всё 640, владелец 999:admin, md5 сверены с
локальными. Бэкап конфига — `/srv/prod-monolith/.env.backup-2026-09-08`.

Прод-`.env` дополнен переменными `FCM_*` и `KAFKA_READER_*`, бэкап —
`.env.backup-2026-09-08`. Состояние на 2026-09-10: `FCM_ENABLED=true`,
**`FCM_ALLOWED_LOGINS=*` — пуши уходят всем** (предохранитель на логин Ильи
снят где-то между 08 и 10 сентября), `HMS_ENABLED=false`,
`KAFKA_READER_LOG_MESSAGES=true` (сырой лог `BET_COM` — ~380 МБ в сутки,
ротация `days=3`), `KAFKA_READER_GROUP_PREFIX=olimp.com.prod5`, ни в коем
случае не легаси `api.ragnaros.net.group2`. Реальный поток: ~150 тыс.
сообщений `BET_COM` и ~16 тыс. выигрышей в сутки, ~5 тыс. отправленных пушей.

`PrepareWinPushJob`/`PrepareCashPushJob` перед отправкой проверяют две вещи и
пишут в лог причину, а не падают: нет бандла в карте →
`no fcm project for <bundle>/<platform>`, нет файла ключа →
`no credentials for fcm project <name>`. Имя проекта попадает в лог
`push.win.sent` полем `project`.

**Ключей два**: `olimp-premium.json` (реальный `project_id`
`olimp-premium-93c72`) — iOS `com.olimpRF1`, `com.olimppremium2` и её QA;
`olimp-com.json` (`project_id` `olimp-com`) — android-бандлы, среди них
`com.olimp.app` (657 тыс. аккаунтов), `com.olimpRF1.app`, `com.asiabet.bet`,
`com.olimpmatch`, `com.olmp.premium.client`. Итого 13 комбинаций в карте.

Ключей **нет** для проектов `olimp-ios` (`com.olimpbetkz`), `olimpcs-f0eb6`
(`com.olympcsn.app`, `com.olimpRF2.app`, `com.oplatinum.mobile.android`,
финансовые приложения) и `sportquizfake` (`com.osportquiztop.app`) — их бандлы
в карту не вносим. Слать их чужим ключом нельзя: FCM v1 привязан к проекту,
ответ будет `SENDER_ID_MISMATCH`.

Бандлы без записи в `applications` (`com.olimp.prem2` — 5 293 аккаунта,
`com.arcanite.Olimp`, `com.olimp.stats.soccer`) и с пустым `fb_proj`
(`com.olimp.matchcenter`, `com.olimpbar.app1029`, `com.olimp.soccer`,
`com.olmpclubprm.app` — там в `fb_proj` вообще мусор «Olmp Clubs Premium QA»)
в карту не попали: под них неизвестно, какой проект.

## Ловушки

- **Прямая правка `accounts` в БД не инвалидирует кеш.** `Account::getByLogin()`
  сначала читает `AccountCache` (Redis) и идёт в базу, только если записи нет или
  не хватает relations. После ручного `UPDATE` (например, поменяли `lang_id`)
  джобы пушей продолжают видеть старый снимок — 2026-09-08 из-за этого пуш ушёл
  на русском при `lang_id=2` в базе. Лечится
  `Account::cache()->forgetByLogin('<логин>')`. Из приложения язык меняется через
  модель, там кеш обновляется штатно — ловушка именно для ручных правок.

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

- [ ] FCM: нет ключей для `olimp-ios`, `olimpcs-f0eb6`, `sportquizfake`.
      Появятся — положить файл в каталог и дописать бандлы в `push.fcm.apps`.
- [ ] На деве переименовать `secrets/fcm/service-account.json` в
      `olimp-premium.json` и заменить в `.env` `FCM_CREDENTIALS_PATH` на каталог
      `/home/fcm` — иначе после выкатки ключ не найдётся.
- [x] Выкатить `push-service` и `kafka-reader` на прод — сделано 2026-09-08.
- [x] `kafka-reader` 1.1.5 выкачен на прод 2026-09-10 12:52 UTC (коммит
      `c04b41fb`). Дублей `card_id` после деплоя нет, но через 20 минут
      `BET_COM` встал на 19 минут (см. «ловушка той же группы»).
- [ ] `kafka-reader` 1.1.6 (`b70ab27a`, fetch 64 КБ + предохранитель +
      `KAFKA_READER_DEBUG`) запушен в `master` и `dev` 2026-09-10 ~13:31 UTC.
      На деве с 13:50 (работает, см. выше). На прод не выкачен: кнопка
      `deploy-kafka-reader-production` (только CI умеет логиниться в registry).
      Пока прод на 1.1.5 + 443, поколение bet-com = 37 (расклинен 14:17).
- [ ] `kafka-reader` 1.1.7 (`6a96d343`, сторож не сбрасывается на
      переназначении) и 1.1.8 (окно старта `KAFKA_READER_MAX_LAG_MINUTES`)
      закоммичены локально в `dev`/`master`, не запушены. Выкатывать на прод
      сразу 1.1.8. Прод расклинивали руками в 13:32 (g36), 14:17 (g37),
      15:37 (g38) — без 1.1.6+ он встаёт каждые 30–60 минут.
- [ ] Путь Vultr → брокеры теряет ~30% TCP. Варианты: хост в другой сети для
      ридера; спросить владельцев Kafka про фильтрацию/шейпинг иностранных
      адресов; попробовать `KAFKA_READER_SOCKET_TIMEOUT_MS=60000` и
      `KAFKA_READER_SESSION_TIMEOUT_MS=90000`, чтобы реже рвать сессии (сначала
      на деве).
      После деплоя проверить: при рестарте сторожа `restarts_without_progress`
      в логе, поток восстанавливается без смены группы, `next_generation`
      появляется только на третьем пустом рестарте.
- [ ] Причина ребалансов ридера на проде каждые 1–4 минуты. Улика из
      `docker logs old-cms-prod-kafka-reader-1` (stderr librdkafka): ко всем
      трём брокерам `apache-kafka-0{1,2,3}.mgr.com.ru:9093` регулярно
      `Timed out FetchRequest/HeartbeatRequest/MetadataRequest in flight
      (after ~30000ms)` → `disconnect (after 30–100 s in state UP)`. То есть
      TCP-сессия жива, а ответы перестают приходить на 30+ с
      (`socket.timeout.ms=30000`), и так по кругу. Это не CPU (2%) и не
      залипание группы. Подозревать путь сеть↔брокеры (NAT/conntrack/балансер
      перед 9093), сравнить с devом и с легаси-читателем `ContextKafka` на том
      же хосте. Пока последствия закрыты дедупом и рестартом без смены группы.
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
