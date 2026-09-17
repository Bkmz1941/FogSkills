---
name: olimp-proxy
description: Прокси-серверы «Olimp» — реестр серверов (первый 151.245.230.200), доступ admin по ключу it@agg.one, пароли в ~/password.txt, как поднять и проверить прокси, как заводить новый сервер. По «прокси олимп», «зайди на прокси», «подними прокси», «добавь прокси-серв».
---

# Olimp — прокси-серверы

Скил про **сетевые прокси** (HTTP / SOCKS5) для нужд Olimp: реестр машин, доступ,
runbook'и. НЕ путать с `proxy-server-bff` / `proxy-server-dev` из скила `olimp-api` —
это BFF-приложение на серверах монолита, к прокси не относится.

## Реестр серверов

| # | IP | Хост | ОС / железо | Прокси-софт | Заведён |
|---|---|---|---|---|---|
| 1 | `151.245.230.200` | `srv713851867` | **Ultahost VPS Basic** (`srv713851867.host`), Ubuntu 24.04.5, KVM, 1 vCPU / 1 GB / 29 GB, без swap | haproxy 2.8 :443 → API `olimpapi.cc` (домен `dlyamastera.com`), nginx снесён 2026-09-16 | 2026-09-15 |

Новый сервер — дописать строку сюда, пароль в `~/password.txt`, алиас в `~/.ssh/config`.

## Доступ

- Вход: `ssh olimp-proxy` (алиас в `~/.ssh/config`, стоит ПОСЛЕ управляемого блока
  work-skills — установщик его не перетирает) или `ssh admin@151.245.230.200`.
- Пользователь **`admin`** (uid 1000, группы `admin`+`sudo`), ключ `~/.ssh/id_ed25519`
  (`it@agg.one`). Других ключей на сервере нет — `claude@agg.one` НЕ добавлен.
- **sudo без пароля** (`/etc/sudoers.d/90-admin-nopasswd`, с 2026-09-15): `sudo -n <cmd>`
  работает из любой одноразовой `ssh olimp-proxy 'cmd'`. Пароль admin всё равно есть —
  в `~/password.txt` (локально у Ильи, `chmod 600`) — на случай консоли провайдера.
- **root по SSH закрыт, парольный вход закрыт**: `PermitRootLogin no`,
  `PasswordAuthentication no`, `KbdInteractiveAuthentication no` — и в
  `/etc/ssh/sshd_config`, и дублем в `/etc/ssh/sshd_config.d/10-hardening.conf`.
  Бэкап исходного конфига: `/etc/ssh/sshd_config.bak-20260915-162559`.
- 2026-09-16 пароль для admin ненадолго открывали (`Match User admin` →
  `PasswordAuthentication yes` в конце `sshd_config`) и в тот же день по решению Ильи
  закрыли обратно — **сейчас admin тоже только по ключу**. Если снова понадобится — тот же
  блок в самом конце файла. Проверка извне без пароля:
  `ssh -v -o PubkeyAuthentication=no -o PreferredAuthentications=none -o BatchMode=yes admin@151.245.230.200 true 2>&1 | grep 'can continue'`
  → `publickey` (закрыто) или `publickey,password` (открыто).
- Root-пароль от провайдера по SSH больше не работает. Потерян ключ → только консоль
  или rescue у провайдера.
- Секреты — только в `~/password.txt`, не в скиле и не в гите.

## Состояние на 2026-09-15

Чистая машина сразу после установки: слушают только `sshd:22` и `systemd-resolved`.
Система обновлена полностью (`apt full-upgrade` + ребут, ядро 6.8.0-139). Обновлять
с флагом `-o APT::Get::Always-Include-Phased-Updates=true`, иначе apt отложит часть
пакетов «due to phasing» и скажет «0 upgraded», хотя `apt list --upgradable` их видит.
`ufw` есть, но неактивен; fail2ban и docker не стоят. С 2026-09-16 слушает haproxy:443
(80 свободен), см. ниже. SOCKS/HTTP-прокси (3proxy) не ставили.

## haproxy — reverse-proxy на API Olimp (2026-09-16)

Смысл: клиент ходит на наш домен, haproxy проксирует на API, конечный адрес клиенту не виден.
nginx по решению Ильи снесён (`apt purge`, бэкап `/etc/nginx` —
`/home/admin/nginx-etc-backup-20260916-094355.tar.gz`); `/var/www/dlyamastera.com` осталась.

- haproxy 2.8.16 из apt, `systemctl enable`. Конфиг `/etc/haproxy/haproxy.cfg` — конфиг
  Козлова Александра (IT), отличия: **`resolve-prefer ipv4`** в строках `server` (см. грабли)
  и включённые логи (ниже). Перед каждой правкой — бэкап `/etc/haproxy/haproxy.cfg.bak-<дата>`. Локальная копия: `~/Documents/Work/Olimp/proxy/haproxy/haproxy.cfg`.
  Штатный убунтовский — `/etc/haproxy/haproxy.cfg.ubuntu-default`.
- `:443 ssl` → `default_backend one` = `olimpapi.cc:443` (Host/SNI `olimpapi.cc`, verify none,
  XFF = IP клиента). `backend two` = `olimpapi2.com` — объявлен, но **трафик в него не идёт**:
  `use_backend` закомментирован, правила переключения нет. Проверено 2026-09-16 в docker:
  `one` лёг → 503 «No server is available», на `two` не уходит. Для автопереключения нужна
  строка `use_backend two if { nbsrv(one) eq 0 }`, но и тогда `check` (TLS до Cloudflare)
  не видит падения бэка за Cloudflare. Оба домена — за Cloudflare, одни и те же IP.
- **Логи включены 2026-09-16** (раскомментированы `log /dev/log local0`, `option httplog`,
  `log global` + добавлен `error-log-format` с причиной TLS-ошибки) → rsyslog (пакетный
  `/etc/rsyslog.d/49-haproxy.conf`) → **`/var/log/haproxy.log`** (syslog:adm 640 — через sudo),
  ротация daily × 7 (`.1`, дальше `.gz` → `zgrep`). DOWN/UP серверов и reload — там же и в `journalctl -u haproxy`.
  - живьём: `sudo tail -f /var/log/haproxy.log`
  - ошибки соединений: `sudo grep conn_err= /var/log/haproxy.log` (`ssl_err=…http request` —
    голый HTTP на 443, `unsupported protocol` — старый TLS, `sni=-` без SNI — обычно сканеры)
  - битые запросы/ответы: `sudo grep -E '<BADREQ>| (400|408|502|503|504) ' /var/log/haproxy.log`
  - по клиенту: `sudo grep '<IP>:' /var/log/haproxy.log`
  - строка запроса: `IP:port [время] http~ one/<server> Tq/Tw/Tc/Tr/Ta статус байты - - <флаги завершения> conns {Host|Referer|UA} "запрос"`;
    Tr — ответ апстрима, Ta — всего, мс; флаги `----` = норм, `CD`/`SD`/`sH` и т.п. — кто и на каком этапе оборвал.
- Счётчики без логов (сокет мастера): `echo "@1 show stat" | sudo nc -U -q 2 /run/haproxy-master.sock`
  (`ssl_failed_handshake`, `h2_detected_conn_protocol_errors`, `ereq`, `eresp`…),
  `@1 show info`, `@1 show errors` (последний битый запрос целиком). Сбрасываются при reload.
- 2026-09-16 HAR из Proxyman (приложение `com.olimpRF1` через домен): 40×200 и 141×`999 Error`
  (так Proxyman пишет «ответа не было»), а haproxy насчитал `ssl_failed_handshake=142` и
  `h2_detected_conn_protocol_errors=23`. Подозрение — HTTP/2: haproxy 2.8 сам отдаёт ALPN `h2`
  (старые версии — только http/1.1). Если логи подтвердят — `alpn http/1.1` в `bind`. Не решено.
  С 15:03 UTC `option dontlognull` закомментирован (логируем и соединения без запросов) —
  после отладки вернуть. 14:45–15:05 коллега (`81.88.223.41`) ловил ошибки в приложении, а в
  логе все ~75 запросов 200/`----`, 1 TLS-обрыв клиентом (`ssl_err=-`). Телефон открывает новое
  соединение почти на каждую пачку запросов (живут секунды, `timeout http-keep-alive 5s`).
- **Причина «999 / таймаут без ответа» (найдена 2026-09-16 ~15:10 UTC) — сеть клиента, не прокси.**
  Коллега в РФ (`81.88.223.41`, домашний PPPoE, country RU). Зависшие сокеты на сервере:
  `ss -tin dst <IP>` → `FIN-WAIT-1`, Send-Q 17–82 КБ, `bytes_acked:14381` при `bytes_sent:~45 КБ`,
  `backoff:8`, `lost:15` — после первых ~14 КБ (10 полных сегментов по 1440) клиент больше
  ничего не подтверждает. Не MTU (полноразмерные пакеты первой пачки прошли). В haproxy-логе при
  этом `200 ----` — он отдал ответ в сокет. Мелкие ответы (~1–8 КБ) проходят, `slice` (20–64 КБ),
  картинки — виснут. Из Сербии всё ок, 197 КБ за 0.4 с. Похоже на известную «заморозку ~16 КБ»
  у российских провайдеров к IP зарубежных хостингов. Лечится размещением прокси в РФ /
  в неподверженной сети, не конфигом. Счётчики: `nstat -az | grep -E 'TcpRetransSegs|TCPTimeouts'`.
- Сертификат `/etc/haproxy/ssl/cert.cer` (fullchain + key в одном файле, 600) — Let's Encrypt
  на `dlyamastera.com` + `www` с 2026-09-16, выпущен `certbot certonly --standalone` (80 порт
  свободен, haproxy его не слушает). Продление — cron `/etc/cron.d/certbot-haproxy`
  (`17 3,15 * * *`, `certbot renew -q`, ошибки в `/var/log/certbot-cron.log`; по просьбе Ильи
  2026-09-16), перевыпуск только за 30 дней до конца. **`certbot.timer` отключён**
  (`systemctl disable --now`, решение Ильи — продление только кроном). Пакетный
  `/etc/cron.d/certbot` при systemd сам себя пропускает, на него не рассчитывать. Не из TTY
  certbot перед продлением спит случайно до 8 мин («random delay» в
  `/var/log/letsencrypt/letsencrypt.log`) — это не зависание. После продления
  `/etc/letsencrypt/renewal-hooks/deploy/haproxy.sh` склеивает `fullchain`+`privkey` в
  `cert.cer` и делает `reload`. `renew --dry-run` проходит. Хуки из `renewal-hooks/deploy`
  при ПЕРВОМ выпуске не запускаются — после нового `certonly` скрипт дёрнуть руками:
  `sudo env RENEWED_LINEAGE=/etc/letsencrypt/live/<домен> /etc/letsencrypt/renewal-hooks/deploy/haproxy.sh`.
  Старый самоподписанный — `/etc/haproxy/ssl/cert.cer.selfsigned`.
- Правка конфига: `sudo haproxy -c -f /etc/haproxy/haproxy.cfg && sudo systemctl reload haproxy`.
- Проверка снаружи: `curl -sk --resolve dlyamastera.com:443:151.245.230.200 -D - -o /dev/null https://dlyamastera.com/`
  → 200, `server: cloudflare`, `cf-ray: …-WAW` (колокейшн рядом с сервером — значит, прошло через него).

## Домен dlyamastera.com

- Куплен 2026-09-15 на **Ultahost**, NS `ns1..ns4.ultahost.com`, DNSSEC unsigned.
- Купить домен ≠ привязать к серверу: зону надо создать руками. Сначала не резолвился —
  NS Ultahost отвечали **REFUSED** (зоны нет), 8.8.8.8 → SERVFAIL.
- Где заводить: bill.ultahost.com → левое меню **Domains → Manage DNS** (DNS Manager) →
  **Add DNS Zone** в блоке сервера `srv713851867.host - VPS Basic` (не «Other»). На странице
  самого домена (Nameservers/Addons) записей нет. Nameservers не трогать — там `ns1..ns4.ultahost.com`.
- 2026-09-16 зону создали: A `dlyamastera.com` → `151.245.230.200`, `www` — CNAME на него.
  8.8.8.8 / 1.1.1.1 / 77.88.8.8 резолвят. Сразу после создания ns3/ns4 отдавали записи,
  ns1 ещё REFUSED, ns2 (`51.38.114.43`) — connection refused; резолверам хватает живых.
- Проверка: `for ns in ns1 ns2 ns3 ns4; do dig +norec +short dlyamastera.com @$ns.ultahost.com; done`.

## Runbook — быстрый прокси без установки (SOCKS5 через ssh)

```bash
ssh -N -D 1080 olimp-proxy          # держать в фоне
curl -x socks5h://127.0.0.1:1080 https://api.ipify.org   # → 151.245.230.200
```

Годится для разовых проверок «как выглядит сайт с этого IP». Для постоянного
прокси — вариант ниже.

## Runbook — поднять постоянный прокси (3proxy: HTTP + SOCKS5 с логином)

```bash
ssh olimp-proxy
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
sudo ufw allow OpenSSH && sudo ufw allow 3128/tcp && sudo ufw allow 1080/tcp && sudo ufw --force enable
```

Логин/пароль прокси — тоже в `~/password.txt`, строкой `proxy <IP> / <USER> / <PASS>`.
Если нужен только SOCKS5 — `dante-server`; только HTTP — `squid`. Порты не светить
наружу без `auth strong` или `allow <ip-клиента>`.

## Runbook — проверить прокси снаружи

```bash
curl -sS -x http://USER:PASS@151.245.230.200:3128  https://api.ipify.org; echo
curl -sS -x socks5h://USER:PASS@151.245.230.200:1080 https://api.ipify.org; echo
```

Оба должны вернуть `151.245.230.200`. Таймаут → порт закрыт (ufw / не слушает);
`407` → неверные креды.

## Runbook — завести новый прокси-сервер (как делали №1)

1. Первый вход root-паролем провайдера: `sshpass -p '<pw>' ssh root@<IP>`.
2. Юзер: `adduser --disabled-password --gecos '' --ingroup admin admin` — в Ubuntu
   группа `admin` уже есть, без `--ingroup` `adduser` падает. Потом
   `echo 'admin:<PW>' | chpasswd && usermod -aG sudo admin` и sudo без пароля:
   `echo 'admin ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/90-admin-nopasswd`,
   `chmod 440`, `visudo -c`.
3. Ключ: `~/.ssh/id_ed25519.pub` → `/home/admin/.ssh/authorized_keys`, права 700/600,
   владелец admin.
4. **До закрытия root** проверить с локальной машины: вход по ключу под admin и
   `ssh admin@<IP> 'sudo -n id -un'` → `root`.
5. sshd: в `/etc/ssh/sshd_config` провайдер дублирует `PermitRootLogin yes` /
   `PasswordAuthentication yes` по 4–5 раз, часть ВЫШЕ `Include sshd_config.d` —
   у sshd побеждает первое вхождение, так что один drop-in не спасёт. Делать
   `sed` по всему файлу на `no` + drop-in `10-hardening.conf`, затем `sshd -t`,
   `systemctl restart ssh`, `sshd -T | grep -Ei 'permitroot|passwordauth'`.
6. Проверить снаружи: root по паролю и admin по паролю → `Permission denied
   (publickey)`; `ssh admin@<IP>` по ключу → ок.
7. Записать: `~/password.txt`, алиас в `~/.ssh/config` (после блока work-skills),
   строка в таблице выше.

## Грабли

- `adduser admin` без `--ingroup admin` → «The group `admin' already exists».
- Пока sudo был по паролю, `sudo -n` в одноразовых `ssh host 'cmd'` падал («a password
  is required») — поэтому и заведён NOPASSWD. Если файл в `sudoers.d` пропал — снова
  `echo "$PW" | sudo -S -p '' <cmd>` с паролем из `~/password.txt`.
- Ставить drop-in в `sshd_config.d` без правки основного файла бесполезно (см. п. 5).
- 1 GB RAM без swap: тяжёлое (docker + squid с кэшем) сюда не тащить.
- У сервера **нет IPv6**, а haproxy в `resolvers` по умолчанию берёт AAAA → оба бэкенда
  DOWN «Network is unreachable», клиенту 503. Поэтому `resolve-prefer ipv4` в `server`.
- `tune.ssl.cachesize 1000000` из исходного конфига сразу забирает ~237 MB shared-памяти
  (из 960). Под нагрузкой на 1 GB это риск OOM — если упрётся, снизить до 100000 (~24 MB).
- haproxy 2.8 на `bind … ssl` сам отдаёт h2 (ALPN `h2,http/1.1` по умолчанию) — HTTP/2 у
  клиента это норма, а не признак, что запрос прошёл мимо.
