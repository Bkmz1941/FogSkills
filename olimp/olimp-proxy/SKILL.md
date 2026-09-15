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
| 1 | `151.245.230.200` | `srv713851867` | Ubuntu 24.04.5, KVM, 1 vCPU / 1 GB / 29 GB, без swap | **ещё не поднят** | 2026-09-15 |

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
- Root-пароль от провайдера по SSH больше не работает. Потерян ключ → только консоль
  или rescue у провайдера.
- Секреты — только в `~/password.txt`, не в скиле и не в гите.

## Состояние на 2026-09-15

Чистая машина сразу после установки: слушают только `sshd:22` и `systemd-resolved`.
Система обновлена полностью (`apt full-upgrade` + ребут, ядро 6.8.0-139). Обновлять
с флагом `-o APT::Get::Always-Include-Phased-Updates=true`, иначе apt отложит часть
пакетов «due to phasing» и скажет «0 upgraded», хотя `apt list --upgradable` их видит.
`ufw` есть, но неактивен; fail2ban и docker не стоят. **Прокси-софт не установлен** —
тип (HTTP / SOCKS5), порт и авторизация решаются Ильёй, потом ставим по runbook ниже.

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
