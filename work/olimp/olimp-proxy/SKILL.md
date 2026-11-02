---
name: olimp-proxy
description: Прокси API «Olimp» и КОНФИГИ ПРИЛОЖЕНИЙ с адресом API. Боевой прокси 89.47.164.147 (api2/api3.ragnaros.top, Time4VPS, olimp-proxy3), прежний 195.181.241.231 (dlyamastera.com, лежит с 28.10); haproxy → olimpapi.cc, сертификаты, логи, как заводить новый сервер. Где приложения берут адрес API (Firebase → монолит и Config Publisher proxyconfig.aggone.dev → S3 twcstorage) и как его поменять точечно с откатом (CONFIGS.md, scripts/). Инцидент 31.10 — INCIDENT-2026-10-31.md. По «прокси олимп», «зайди на прокси», «проверь прокси», «подними прокси», «прокси умер», «приложение не видит api», «вечная загрузка», «поменять адрес api в приложениях», «default_api_url», «direct_api_url», «конфиг приложения», «publisher», «proxyconfig», «dlyamaster», «инцидент 31.10», «пустая главная», «витрина Проверка», «minio prx30admrgnrs».
---

# Olimp — прокси-серверы и адрес API в приложениях

Скил про **сетевые прокси** для нужд Olimp: реестр машин, доступ, runbook'и.
НЕ путать с `proxy-server-bff` / `proxy-server-dev` из скила `olimp-api` —
это BFF-приложение на серверах монолита, к прокси не относится.

## Карта файлов

| Файл | Что |
|---|---|
| `CONFIGS.md` | **Где приложения берут адрес API** (Firebase → монолит; Config Publisher → S3), поля по бандлам, команды publisher, рецепт смены адреса с откатом, проверка |
| `INCIDENT-2026-10-31.md` | Инцидент «умер dlyamaster»: хронология, что сделали, id публикаций для отката, что осталось, грабли |
| `scripts/pub_inventory.py` | расшифровать все публикации publisher и показать адреса (только чтение) |
| `scripts/pub_set_field.py` | поменять одно поле одного документа в publisher (сухой прогон / `--send`) |
| `scripts/pub_replace_host.py` | заменить хост старого прокси в документах коллекции (в т.ч. вложенные `payment_url`) |
| `scripts/pub_compare.py` | сравнить две публикации (бэкап ↔ текущая) |
| `scripts/mono_replace_host.php` | МОНОЛИТ (прод): найти старый хост во всех `application_settings` и переслать исправленные документы через вебхук `/api/firebase/settings` (tinker в контейнере `app`; сухой прогон без `SEND=1`) |
| `scripts/pub_send_from_monolith.py` | переслать в publisher документ из БД монолита |
| `backups/2026-10-31/` | зашифрованные копии S3-конфигов ДО правок 31.10 |
| `haproxy/` | конфиг haproxy 89.47.164.147, deploy-хук certbot, крон продления |

**Сменился адрес прокси → менять в трёх местах: Firebase, монолит (приходит из Firebase сам), publisher (НЕ приходит сам).** Подробно — `CONFIGS.md`.

## Реестр серверов

| IP | Хост | ОС / железо | Что крутится | Заведён |
|---|---|---|---|---|
| `195.181.241.231` | `5xft.l.time4vps.cloud` | **Time4VPS**, Вильнюс (AS212531, UAB «Interneto vizija», панель billing.time4vps.com), Ubuntu 24.04.5, ядро 6.8.0-139, **3 vCPU / 8 GB / 99 GB** (тариф подняли 2026-09-17, до этого 1/2/25), без swap, IPv6 `2a02:7b40:c3b5:f1e7::1` | haproxy 2.8 :443 → API `olimpapi.cc`, домен `dlyamastera.com`. **Не отвечает с 2026-10-28** | 2026-09-17 |
| `89.47.164.147` | `5ysg.l.time4vps.cloud` | **Time4VPS**, Ubuntu 24.04.5, ядро 6.8.0-53, **2 vCPU / 4 GB / 50 GB**, IPv6 `2a02:7b40:592f:a493::1`. База AGG уже была (`audit`, fail2ban, UFW 22) — открыли 80, 443 | **БОЕВОЙ с 31.10.** haproxy 2.8.30 :443 → `olimpapi.cc`, тот же конфиг (`nbthread 2`, `cpu-map auto:1/1-2 0-1`, копия в `haproxy/`), **домены `api2.ragnaros.top` и `api3.ragnaros.top`** (LE, SAN api2+api3, до 2027-01-29; NS dnsowl = NameSilo, правит Вальтер). Вход `ssh olimp-proxy3` | 2026-10-31 |

⚠️ 2026-10-31: у `api.ragnaros.top` ДВЕ A-записи — `89.47.164.147` и чужая `95.179.168.249`
(серт `remote.apexcrm.cc`, отдаёт какую-то веб-панель). LE http-01 бьёт в случайную → 404 (3 неудачи).
На `.147` пока самоподписанный `cert.cer` (= `cert.cer.selfsigned`); deploy-хук, крон `certbot-haproxy`,
отключённый `certbot.timer` уже стоят. После удаления чужой записи:
`sudo certbot certonly --standalone -n -d api.ragnaros.top`, затем
`sudo env RENEWED_LINEAGE=/etc/letsencrypt/live/api.ragnaros.top /etc/letsencrypt/renewal-hooks/deploy/haproxy.sh`.
В вики «Сервера» строки нет.
Итог 2026-10-31 ~01:34 UTC: Вальтер завёл `api2`/`api3.ragnaros.top` → 89.47.164.147 (сначала `api2` по
ошибке на 95.179.168.249). **Выпущен LE на `api3.ragnaros.top`** (до 2027-01-29, lineage
`/etc/letsencrypt/live/api3.ragnaros.top`), стоит в `cert.cer`, `renew --dry-run` ok. 03:47 UTC — **`api2` добавлен
в тот же серт** (`--cert-name api3.ragnaros.top --expand -d api3… -d api2…`), SAN = api2+api3, до 2027-01-29.
Исправленная (не новая) запись `api2` у NameSilo/dnsowl мигала между старым и новым IP **~80 минут**
(новая `api3` разошлась сразу) — при ошибке в IP проще удалить запись и завести заново.
Порядок без траты лимитов: проверить все NS → порт 80 листенером → `--dry-run` → один боевой.

Новый сервер — дописать строку сюда, пароль в `~/password.txt`, алиас в `~/.ssh/config`.

Почему Вильнюс: на прошлом хостинге у российских провайдеров была «заморозка ~16 КБ»
(см. «Причина 999» ниже). Тот же AS, что у рабочего `dlyamasterapoblokirovkam.top` (80.209.236.223).

## Доступ

- Вход: `ssh olimp-proxy2` (алиас в `~/.ssh/config`, стоит ПОСЛЕ управляемого блока
  work-skills — установщик его не перетирает) или `ssh admin@195.181.241.231`.
- Пользователь **`admin`** (группы `admin`+`sudo`; группу `admin` в образе Time4VPS пришлось
  создать), ключ `~/.ssh/id_ed25519` (`it@agg.one`). Других ключей нет — `claude@agg.one` НЕ добавлен.
- **sudo без пароля** (`/etc/sudoers.d/90-admin-nopasswd`): `sudo -n <cmd>` работает из любой
  одноразовой `ssh olimp-proxy2 'cmd'`.
- **root по SSH и пароли закрыты**: `PermitRootLogin no`, `PasswordAuthentication no`,
  `KbdInteractiveAuthentication no` — `sshd_config` и `50-cloud-init.conf` правлены на `no`,
  плюс drop-in `/etc/ssh/sshd_config.d/10-hardening.conf`. Проверка: `sudo sshd -T | grep -Ei 'permitroot|passwordauth|kbdinteractive'`.
  Снаружи без пароля:
  `ssh -v -o PubkeyAuthentication=no -o PreferredAuthentications=none -o BatchMode=yes admin@195.181.241.231 true 2>&1 | grep 'can continue'`
  → `publickey` (закрыто) или `publickey,password` (открыто).
- Пароли admin и root (root — для VNC-консоли Time4VPS) — в `~/password.txt` (локально у Ильи,
  `chmod 600`). Потерян ключ → только консоль или rescue у провайдера.
- Секреты — только в `~/password.txt`, не в скиле и не в гите.
- Таймзона провайдера была Europe/Vilnius — выставлена `Etc/UTC`. htop, mc стоят.
  Обновлять с `-o APT::Get::Always-Include-Phased-Updates=true`, иначе apt отложит часть
  пакетов «due to phasing» и скажет «0 upgraded», хотя `apt list --upgradable` их видит.
  `ufw` неактивен; fail2ban, docker, SOCKS/HTTP-прокси (3proxy) не стоят.

## Проверка сервера (последняя — 2026-09-17 16:10 UTC, после апгрейда тарифа и ребута)

**⚠️ 2026-10-28 ~09:45 UTC — сервер не отвечает.** Ping, :22 и :443 закрыты с трёх точек
(машина Ильи, `kafka-com`, `lucky-dev`), IPv6 не проверялся. Upstream `olimpapi.cc` отвечает 200,
запасной `dlyamasterapoblokirovkam.top` (80.209.236.223) отвечает 200, DNS `dlyamastera.com`
по-прежнему → 195.181.241.231. Причина не установлена — смотреть панель / VNC-консоль Time4VPS
(root для VNC — в `~/password.txt`). После подъёма — прогнать блок проверки ниже.

```bash
ssh olimp-proxy2 'uptime; nproc; free -m; df -h /; systemctl is-active haproxy; sudo -n ss -ltnp'
ssh olimp-proxy2 'sudo -n haproxy -c -f /etc/haproxy/haproxy.cfg; md5sum /etc/haproxy/haproxy.cfg'   # = md5 локальной копии
ssh olimp-proxy2 'echo "@1 show servers state" | sudo -n nc -U -q 2 /run/haproxy-master.sock'       # srv_op_state 2 = UP
ssh olimp-proxy2 'sudo -n openssl x509 -in /etc/haproxy/ssl/cert.cer -noout -enddate'
curl -sk --resolve dlyamastera.com:443:195.181.241.231 -D - -o /dev/null https://dlyamastera.com/   # 200, cf-ray …-VNO
dig +short dlyamastera.com @8.8.8.8                                                                 # 195.181.241.231
```

Итог 2026-09-17: слушают только ssh:22 и haproxy:443, haproxy enabled/active, конфиг валиден и
совпадает с локальной копией, оба бэка UP, серт LE до 2026-12-15, крон на месте, `certbot.timer`
disabled, sshd закрыт, обновлений нет. После ребута (15:47) ~300 ответов 200, 502/503/504 нет.
Коллега из РФ (`81.88.223.41`) получает `slice` по 57 КБ за ~1.8 с (`200 ----`), зависших
`FIN-WAIT-1` нет, `TcpRetransSegs` 2 на ~15 000 — «заморозки 16 КБ» здесь нет.

## haproxy — reverse-proxy на API Olimp

Смысл: клиент ходит на наш домен, haproxy проксирует на API, конечный адрес клиенту не виден.

- haproxy 2.8.16 из apt, `systemctl enable`. Конфиг `/etc/haproxy/haproxy.cfg` — конфиг
  Козлова Александра (IT, оригинал — `~/Documents/Work/Olimp/proxy/config`), отличия:
  **`resolve-prefer ipv4`** в строках `server` (см. грабли) и включённые логи (ниже).
  Перед каждой правкой — бэкап `/etc/haproxy/haproxy.cfg.bak-<дата>`.
  Локальная копия боевого: `~/Documents/Work/Olimp/proxy/haproxy/haproxy.cfg`.
- `:443 ssl` → `default_backend one` = `olimpapi.cc:443` (Host/SNI `olimpapi.cc`, verify none,
  XFF = IP клиента). `backend two` = `olimpapi2.com` — объявлен, но **трафик в него не идёт**:
  `use_backend` закомментирован, правила переключения нет. Проверено 2026-09-16 в docker:
  `one` лёг → 503 «No server is available», на `two` не уходит. Для автопереключения нужна
  строка `use_backend two if { nbsrv(one) eq 0 }`, но и тогда `check` (TLS до Cloudflare)
  не видит падения бэка за Cloudflare. Оба домена — за Cloudflare, одни и те же IP.
- Правка конфига: `sudo haproxy -c -f /etc/haproxy/haproxy.cfg && sudo systemctl reload haproxy`.
- **Логи** (раскомментированы `log /dev/log local0`, `option httplog`, `log global` + добавлен
  `error-log-format` с причиной TLS-ошибки) → rsyslog (пакетный `/etc/rsyslog.d/49-haproxy.conf`)
  → **`/var/log/haproxy.log`** (syslog:adm 640 — через sudo), ротация daily × 7 (`.1`, дальше
  `.gz` → `zgrep`). DOWN/UP серверов и reload — там же и в `journalctl -u haproxy`.
  - живьём: `sudo tail -f /var/log/haproxy.log`
  - ошибки соединений: `sudo grep conn_err= /var/log/haproxy.log` (`ssl_err=…http request` —
    голый HTTP на 443, `unsupported protocol` — старый TLS, `sni=-` без SNI — обычно сканеры)
  - битые запросы/ответы: `sudo grep -E '<BADREQ>| (400|408|502|503|504) ' /var/log/haproxy.log`
  - по клиенту: `sudo grep '<IP>:' /var/log/haproxy.log`
  - строка запроса: `IP:port [время] http~ one/<server> Tq/Tw/Tc/Tr/Ta статус байты - - <флаги завершения> conns {Host|Referer|UA} "запрос"`;
    Tr — ответ апстрима, Ta — всего, мс; флаги `----` = норм, `CD`/`SD`/`sH` и т.п. — кто и на каком этапе оборвал.
  - `403` с чужим Host (`radionintendo.com`, `/member/login` от Go-клиента) — сканеры, режет Cloudflare.
  - `option dontlognull` закомментирован с отладки 999 (логируем и соединения без запросов) —
    по желанию вернуть.
- Счётчики без логов (сокет мастера): `echo "@1 show stat" | sudo nc -U -q 2 /run/haproxy-master.sock`
  (`ssl_failed_handshake`, `h2_detected_conn_protocol_errors`, `ereq`, `eresp`…),
  `@1 show info`, `@1 show errors` (последний битый запрос целиком). Сбрасываются при reload.
- **Причина «999 / таймаут без ответа» (2026-09-16) — сеть клиента, не прокси.** HAR из Proxyman
  (приложение `com.olimpRF1`): 141×`999 Error` = «ответа не было», а в логе haproxy — `200 ----`.
  На сервере зависшие сокеты: `ss -tin dst <IP>` → `FIN-WAIT-1`, Send-Q 17–82 КБ,
  `bytes_acked:14381` при `bytes_sent:~45 КБ`, `backoff:8` — после первых ~14 КБ клиент ничего не
  подтверждает. Не MTU, не HTTP/2 (curl-повторы проходили). Мелкие ответы проходили, `slice`
  (20–64 КБ) и картинки — висли. Это «заморозка ~16 КБ» у российских провайдеров к IP ряда
  зарубежных хостингов — лечится только сменой сети сервера, поэтому переехали в Вильнюс.
  Если вернётся: `ss -tin state fin-wait-1`, `nstat -az | grep -E 'TcpRetransSegs|TCPTimeouts'`.
- Сертификат `/etc/haproxy/ssl/cert.cer` (fullchain + key в одном файле, 600) — Let's Encrypt
  на `dlyamastera.com` + `www`, выпущен `certbot certonly --standalone` (80 порт свободен,
  haproxy его не слушает). Продление — cron `/etc/cron.d/certbot-haproxy`
  (`17 3,15 * * *`, `certbot renew -q`, ошибки в `/var/log/certbot-cron.log`), перевыпуск только
  за 30 дней до конца. Крон проверен реальным запуском из cron с `--dry-run` — success.
  **`certbot.timer` отключён** (`systemctl disable --now`, решение Ильи — продление только кроном).
  Пакетный `/etc/cron.d/certbot` при systemd сам себя пропускает, на него не рассчитывать. Не из TTY
  certbot перед продлением спит случайно до 8 мин («random delay» в
  `/var/log/letsencrypt/letsencrypt.log`) — это не зависание. После продления
  `/etc/letsencrypt/renewal-hooks/deploy/haproxy.sh` склеивает `fullchain`+`privkey` в
  `cert.cer` и делает `reload`. Хуки из `renewal-hooks/deploy` при ПЕРВОМ выпуске не
  запускаются — после нового `certonly` скрипт дёрнуть руками:
  `sudo env RENEWED_LINEAGE=/etc/letsencrypt/live/<домен> /etc/letsencrypt/renewal-hooks/deploy/haproxy.sh`.
  Staging LE может отвечать `rateLimited … Service busy; retry later` (503, Retry-After) —
  это их перегруз, повторить через пару минут. Порт 80 проверять листенером через
  `setsid nohup timeout 40 python3 -m http.server 80`, иначе он умирает вместе с ssh-сессией.
  Самоподписанный на случай отката — `/etc/haproxy/ssl/cert.cer.selfsigned`.

## Домен dlyamastera.com

- Куплен 2026-09-15 на **Ultahost**, NS `ns1..ns4.ultahost.com`, DNSSEC unsigned.
  A `dlyamastera.com` → `195.181.241.231` (TTL 14400), `www` — CNAME на него. AAAA нет.
- Купить домен ≠ привязать к серверу: зону надо создать руками (без неё NS Ultahost отвечают
  **REFUSED**, 8.8.8.8 → SERVFAIL).
- Где правят записи: bill.ultahost.com → левое меню **Domains → Manage DNS** (DNS Manager).
  Зона заведена в блоке VPS Ultahost (`… - VPS Basic`, не «Other»); если от того VPS
  отказываться — сначала убедиться, что зона не пропадёт вместе с ним. На странице самого домена
  (Nameservers/Addons) записей нет. Nameservers не трогать.
- ns2 (`51.38.114.43`) отвечает connection refused — резолверам хватает остальных трёх.
- Проверка: `for ns in ns1 ns2 ns3 ns4; do dig +norec +short dlyamastera.com @$ns.ultahost.com; done`.

## Runbook — быстрый прокси без установки (SOCKS5 через ssh)

```bash
ssh -N -D 1080 olimp-proxy2          # держать в фоне
curl -x socks5h://127.0.0.1:1080 https://api.ipify.org   # → 195.181.241.231
```

Годится для разовых проверок «как выглядит сайт с этого IP». Для постоянного
прокси — вариант ниже.

## Runbook — поднять постоянный прокси (3proxy: HTTP + SOCKS5 с логином)

```bash
ssh olimp-proxy2
sudo apt update && sudo apt install -y 3proxy
sudo tee /etc/3proxy/3proxy.cfg >/dev/null <<'CONF'
nserver 1.1.1.1
nscache 65536
timeouts 1 5 30 60 180 1800 15 60
log /var/log/3proxy/3proxy.log D
rotate 7
auth strong
users <USER>:CL:<PASS>
allow <USER>
proxy -p3128          # HTTP
socks -p1080          # SOCKS5
CONF
sudo systemctl enable --now 3proxy
sudo ufw allow OpenSSH && sudo ufw allow 443/tcp && sudo ufw allow 3128/tcp && sudo ufw allow 1080/tcp && sudo ufw --force enable
```

`443/tcp` в ufw обязателен — там haproxy. Логин/пароль прокси — тоже в `~/password.txt`,
строкой `proxy <IP> / <USER> / <PASS>`. Если нужен только SOCKS5 — `dante-server`; только HTTP —
`squid`. Порты не светить наружу без `auth strong` или `allow <ip-клиента>`.

## Runbook — проверить прокси снаружи

```bash
curl -sS -x http://USER:PASS@195.181.241.231:3128  https://api.ipify.org; echo
curl -sS -x socks5h://USER:PASS@195.181.241.231:1080 https://api.ipify.org; echo
```

Оба должны вернуть `195.181.241.231`. Таймаут → порт закрыт (ufw / не слушает);
`407` → неверные креды.

## Runbook — завести новый прокси-сервер

1. Первый вход root-паролем провайдера: `sshpass -p '<pw>' ssh root@<IP>`.
2. Юзер: `getent group admin || groupadd admin` (в одних образах Ubuntu группа есть, в других
   нет; `adduser admin` без `--ingroup` при существующей группе падает), затем
   `adduser --disabled-password --gecos '' --ingroup admin admin`,
   `echo 'admin:<PW>' | chpasswd && usermod -aG sudo admin` и sudo без пароля:
   `echo 'admin ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/90-admin-nopasswd`,
   `chmod 440`, `visudo -c`.
3. Ключ: `~/.ssh/id_ed25519.pub` → `/home/admin/.ssh/authorized_keys`, права 700/600,
   владелец admin.
4. **До закрытия root** проверить с локальной машины: вход по ключу под admin и
   `ssh admin@<IP> 'sudo -n id -un'` → `root`.
5. sshd: провайдеры дублируют `PermitRootLogin yes` / `PasswordAuthentication yes` по
   4–5 раз, часть ВЫШЕ `Include sshd_config.d`, плюс `50-cloud-init.conf` — у sshd побеждает
   первое вхождение, так что один drop-in не спасёт. Делать `sed` на `no` по `sshd_config` и
   всем файлам в `sshd_config.d` + drop-in `10-hardening.conf`, затем `sshd -t`,
   `systemctl restart ssh`, `sshd -T | grep -Ei 'permitroot|passwordauth'`.
6. Проверить снаружи: root по паролю и admin по паролю → `Permission denied
   (publickey)`; `ssh admin@<IP>` по ключу → ок.
7. Таймзона `timedatectl set-timezone Etc/UTC`, `apt full-upgrade` (с phased-флагом выше), ребут.
8. haproxy: `apt install haproxy certbot`, перенести `/etc/haproxy/haproxy.cfg`,
   `/etc/haproxy/ssl/`, `/etc/letsencrypt` целиком (аккаунт, renewal-конфиг, deploy-хук),
   `/etc/cron.d/certbot-haproxy`; `systemctl disable --now certbot.timer`. Переключить A-запись,
   после резолва — `certbot renew --dry-run` и deploy-хук руками.
9. Записать: `~/password.txt`, алиас в `~/.ssh/config` (после блока work-skills),
   строка в таблице выше.

## Грабли

- `adduser admin` без `--ingroup admin` при существующей группе → «The group `admin' already exists».
- Если файл в `sudoers.d` пропал, `sudo -n` в одноразовых `ssh host 'cmd'` падает («a password
  is required») — тогда `echo "$PW" | sudo -S -p '' <cmd>` с паролем из `~/password.txt`.
- Ставить drop-in в `sshd_config.d` без правки основного файла бесполезно (см. п. 5).
- haproxy в `resolvers` по умолчанию берёт AAAA — на машине без IPv6 оба бэкенда DOWN
  «Network is unreachable», клиенту 503. Поэтому `resolve-prefer ipv4` в `server`; на текущем
  сервере IPv6 есть, но настройка оставлена (конфиг один на все серверы), слушаем только IPv4.
- `tune.ssl.cachesize 1000000` сразу забирает ~237 MB shared-памяти (видно в `free` как shared).
  На 8 GB не проблема; на машине с 1–2 GB под нагрузкой — снизить до 100000 (~24 MB).
- haproxy 2.8 на `bind … ssl` сам отдаёт h2 (ALPN `h2,http/1.1` по умолчанию) — HTTP/2 у
  клиента это норма, а не признак, что запрос прошёл мимо.
