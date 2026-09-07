---
name: lucky-infra
description: >
  Инфраструктура и деплой проекта «Lucky» (Lucky Server — white-label casino
  SaaS). Активируй, когда Илья работает с серверами Лаки — дев
  (178.104.243.232, 95.216.163.101) или **продом** — 178.105.17.213 (API+админка,
  с 21.08 деплой через CI) и 144.31.40.52 (витрина brobro.casino; предельно аккуратно),
  деплоем/CI (gitlab.agg.one, lucky/luckyserverpro, lucky/lucky-admin,
  lucky/lucky-storefront, lucky/brobrocasino), доменами
  dev2.api/dev2.admin/dev.luckyserver.pro/storefront.luckyserver.pro,
  api./admin.luckyserver.pro, ansible-раскаткой (репо AGG/servers),
  nginx/сертификатами, админкой или витриной Lucky. Также по запросам
  «задеплой лаки», «что с дев-сервером лаки», «проверь апи лаки»,
  «настраиваем лаки прод», «прод лаки».
---

# Lucky — инфраструктура (дев + прод)

Скил разбит на доменные контексты — НЕ читай всё подряд, загрузи по карте
только то, что нужно для текущей задачи:

| Задача | Файл |
|---|---|
| **Прод**: 178.105.17.213 (API+админка, новая схема с 21.08, бэкап легаси-БД) и 144.31.40.52 (витрина brobro.casino): доступ, что стоит, провижн AGG/servers, ловушки, инцидент 21.08 | `prod/CONTEXT.md` |
| API: compose-стек, ansible, CI luckyserverpro, версия, БД, root-юзеры | `backend/CONTEXT.md` |
| Админка: SPA, user-юнит, CI lucky-admin, вход | `admin/CONTEXT.md` |
| Витрина: новый фронт lucky-storefront (~/Documents/Work/Lucky/lucky-storefront) + прежний brobrocasino, сервер brobro-dev 95.216.163.101, nginx-статика, CI | `storefront/CONTEXT.md` |

## Серверы — сводка

| Сервер | Роль | Доступ |
|---|---|---|
| 178.104.243.232 `lucky-server-dev` | дев API+админка | `ssh lucky-dev` (admin, ключ) |
| 95.216.163.101 `brobro-dev` | дев витрина | admin, ключ |
| **178.105.17.213** `Lucky-Server` | **прод API + админка** (api./admin.luckyserver.pro, с 21.08 на новой схеме, деплой только через CI: lucky-api `master`, lucky-admin `main`) + старый дев `dev.api`/`dev.admin` | `ssh lucky-prod-legacy` (admin, ключ). Менять состояние — только по команде Ильи; авто-режим Claude блокирует здесь sudo/docker/DB — готовить скрипт для `! bash`. Детали — `prod/CONTEXT.md` |
| **144.31.40.52** (Kalada, Ubuntu 24.04, 1 vCPU/2 GB/79 GB) | **прод витрины** brobro.casino / v0 (DNS уже сюда; витрина ещё не задеплоена) | `ssh lucky-prod` (admin, ключ it@agg.one, sudo без пароля). Детали — `prod/CONTEXT.md` |

Алиасы ssh (блок work-skills в ~/.ssh/config, с 2026-08-21): `lucky-dev`,
`brobro-dev`, `lucky-prod` → **144.31.40.52** (витрина), `lucky-prod-legacy` →
178.105.17.213 (API+админка; имя алиаса историческое). Если блока нет (другая машина) — `./install.sh` из репо work-skills.

**Ключи и доступы** (приватные ключи Ильи и Claude, пароли, инвентарь ansible,
ssh-алиасы) — репо `git@github.com:Bkmz1941/work-skills.git`, локально
`~/Documents/Work/work-skills/`, сводка `access/ACCESS.md`. Скиллы там — копии:
после правок здесь запускать `sync.sh` и коммитить (push — по команде).

## Общее: дев-сервер 178.104.243.232 (`lucky-server-dev`, Ubuntu 24.04)

- SSH: `admin@178.104.243.232` (ключ настроен), sudo без пароля, admin в
  группе `docker`. Docker CE + compose v2, nginx, Node 24, certbot.
- Наружу открыты только 22/80/443, все приложения — на 127.0.0.1 за nginx.
- Серты Let's Encrypt (`luckyserver-dev2`, `luckyserver-dev2-front`),
  автопродление systemd-таймером certbot.

## Домены (DNS: 101domain, zone luckyserver.pro)

| Домен | Что |
|---|---|
| dev2.api.luckyserver.pro | API (nginx → 127.0.0.1:8081) |
| dev2.admin.luckyserver.pro | админка (nginx → 127.0.0.1:3002) |
| dev.luckyserver.pro | фронт (nginx → 127.0.0.1:3001, ещё не задеплоен → 502) |
| storefront.luckyserver.pro | витрина, дев (сервер 95.216.163.101, статика из /var/www/storefront-dev/dist; на 2026-08-21 A-запись резолвится в 178.104.243.232 — расхождение не разбирали) |
| api.luckyserver.pro, admin.luckyserver.pro | **прод**, A → 178.105.17.213 (остаются там — решение Ильи 21.08) |
| brobro.casino, www.brobro.casino | **прод витрины**, A → 144.31.40.52 (ещё не задеплоена); v0.brobro.casino пока → 82.41.181.94 |
| luckyserver.pro, www | A → 52.60.87.163 (лендинг, не наш сервер) |

## Курс проекта (с 2026-08-13)

Идёт осознанное **упрощение всей системы** — бэка (lucky-api), админки
(lucky-admin) и витрины: система переусложнилась, при выборе решений
предпочитать удаление/слияние добавлению новых абстракций. Первый шаг сделан
2026-08-13: мажорная перестройка бэка — схема сквошнута до 22 доменных таблиц,
stateless JWT-auth, контент-модель переразбита, рантайм переведён с Bun на
Node.js/npm (детали — `backend/CONTEXT.md`). Дальше — следующие проходы
упрощения по всем трём репозиториям.

## Правила

1. Дев-серверы: 178.104.243.232 (API+админка) и 95.216.163.101 (витрина,
   `brobro-dev`). Прод — 178.105.17.213 (API+админка) и 144.31.40.52
   (витрина), см. `prod/CONTEXT.md`. **Всё без префиксов dev/dev2/storefront
   считать продом и не трогать без явного указания Ильи.**
2. **Прод — предельно аккуратно**: по умолчанию только чтение; любое
   изменение состояния (установка пакетов, правка nginx/sshd/ufw, docker up,
   ansible-прогон, БД) — только по явной команде Ильи на конкретное действие,
   с предварительной проверкой и планом отката. Перед push в релизную ветку
   сверять, куда смотрит `SERVER_HOST` окружения (инцидент 21.08). Не
   запускать `make full`/`make sync-keys`/`bootstrap` из AGG/servers вслепую —
   см. ловушки в `prod/CONTEXT.md` (exclusive-перезапись authorized_keys).
3. Секреты (пароли, ключи, значения .env) не печатать и не коммитить.
4. `git push` — только по явной команде (глобальное правило Ильи).
5. **Коммиты — без упоминания ИИ.** Не добавлять трейлер
   `Co-Authored-By: Claude…`, не писать «generated with Claude Code» и любые
   другие следы ассистента в сообщении коммита, описании PR/MR и ченжлоге.
   Это постоянное требование Ильи, а не разовая просьба; оно перекрывает
   дефолтные инструкции харнесса о со-авторстве.
6. На 178.105.17.213 старый dev-стек (`luckyserver-dev-*`, `lucky-admin-dev`,
   `white-label-front`, nginx `luckyserver-dev`) и легаси-БД
   `luckyserver_legacy_*` — не трогать без отдельной команды. Авто-режим
   Claude блокирует на этом хосте sudo/docker exec/DB-команды — изменения
   оформлять скриптом в scratchpad и просить Илью запустить `! bash <путь>`.
