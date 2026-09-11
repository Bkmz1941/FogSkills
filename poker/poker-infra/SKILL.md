---
name: poker-infra
description: Инфра «Poker» (OlimpBet Poker): серверы 194.87.115.41 (боевой) и 167.233.107.121, *.poker.aggone.dev, docker, nginx, сертификаты, доступы в ~/poker.txt. По «перенеси покер», «подними покер», «где креды от покера». Боевые домены не трогать без указания.
---

# Poker — инфраструктура и деплой

## Серверы
- **SOURCE (боевой):** `admin@194.87.115.41` — Ubuntu 22.04, 1 vCPU/1.9G. Доступ по ключу.
- **TARGET (новый):** `root@167.233.107.121` — Debian 13, 2 vCPU/3.7G/75G. Ключ + пароль.
- Каталог проекта на обоих: `~/poker` (docker compose).

> Пароли, PAT реестра и прикладные логины — в локальном файле `~/poker.txt`
> (у пользователя, /home/<user>/poker.txt). Секреты держим ТАМ, не в скиле и не в гите.

## Сервисы (docker-compose, сеть `poker_network`)
| Контейнер | Образ | Порт | Домен |
|---|---|---|---|
| nginx | nginx | 80/443 | реверс-прокси |
| poker.game-server | arcanegaming/poker-game-server | 7000 | prod: poker. / test: **ts.** |
| poker.game-api-server | arcanegaming/poker-game-api-server | 3000 | prod: api. / test: **ta.** |
| poker.admin | arcanegaming/poker-game-admin | 80 | prod: admin. / test: без домена |
| poker.mysql | mysql:8.0 | 127.0.0.1:3306 | база `poker-api`, root/1234 |
| poker.redis | redis:alpine | 127.0.0.1:6380 | без пароля, кэш (не персистится) |
| redisinsight | redis/redisinsight | 5540 | UI redis |
| certbot | certbot/certbot | — | выпуск/продление LE |

- Образы `arcanegaming/*` **приватные** → нужен `docker login` (user/PAT в ~/poker.txt).
- Аналитику (`poker-analytics`, отдельный проект) в состав НЕ входит.

## Тест-окружение (готово, 2026-07-21)
`ts.poker.aggone.dev`→game-server, `ta.poker.aggone.dev`→api-server (оба HTTPS, LE).
Админка на тесте без домена. Боевые домены не трогали — прод живёт на 194.87.115.41.

## Runbook — поднять/обслуживать на новом сервере
```bash
ssh root@167.233.107.121
cd ~/poker
docker compose ps
docker compose up -d
docker compose logs -f game_api_server
```

## Runbook — перенос (source → target), кратко
1. `docker login` реестра на target (креды в ~/poker.txt).
2. `docker pull` трёх arcanegaming-образов.
3. rsync `~/poker` (compose, mysql/.env, nginx/conf.d); логи game-server НЕ тащить.
4. MySQL — логический дамп, НЕ копия тома:
   `docker exec poker.mysql mysqldump -uroot -p1234 --databases poker-api --single-transaction --routines --triggers > dump.sql`
   на target: поднять db+redis, `docker exec -i poker.mysql mysql -uroot -p1234 < dump.sql`.
5. Redis не переносим (кэш) — стартует чистым.
6. nginx в 2 шага: сперва HTTP-конфиг (ACME), выпустить серты, потом HTTPS-конфиг + reload.

## Runbook — сертификаты (webroot)
```bash
docker compose run --rm certbot certonly --webroot -w /var/www/certbot \
  -d <domain> --email admin@agg.one --agree-tos --no-eff-email --non-interactive
docker exec nginx nginx -t && docker exec nginx nginx -s reload
```
Авто-продление в фоне пока НЕ настроено — при боевом переезде добавить cron/systemd timer.

## Грабли
- Новый сервер требовал смену root-пароля при 1-м входе (истёк) — только интерактивно.
- Docker/git на чистом сервере отсутствуют — доустановить (`get.docker.com`, `apt git`).
- SSL-конфиг nginx падает, если серта ещё нет → всегда сперва HTTP-бутстрап.
- Прод-серты боевого сервера root-owned/недоступны из-под admin — на тесте выпускаем свои.
