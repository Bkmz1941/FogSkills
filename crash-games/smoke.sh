#!/usr/bin/env bash
# Проверка живости Crash Heroes. Запускать НА СЕРВЕРЕ (нужны pm2, доступ к БД и модуль ws).
#
# Главное, что проверяется: игра активна, раунды идут И КОЭФФИЦИЕНТ МЕНЯЕТСЯ.
# Просто «сайт отвечает» и «процесс online» этого не ловят — движок может крутиться,
# отдавая один и тот же коэффициент. Поэтому смотрим с двух независимых сторон:
#   • живьём через публичный вебсокет — история коэффициентов должна ПОПОЛНЯТЬСЯ;
#   • по БД — у последних раундов каждой игры коэффициенты должны РАЗЛИЧАТЬСЯ.
#
# Шаги:
#   1. Публичные сайты (demo, api, admin, games)
#   2. Вебсокет каждой игры: приветствие + два замера rates с паузой
#   3. БД: раунды свежие, коэффициенты разные
#   4. pm2: процессы online, рестарты не копятся
#   5. Диск (переполнение логами роняло прод 15.08)
#
# Среда определяется автоматически. Код возврата: 0 — всё хорошо, 1 — проблемы.
#
# Переменные: RATES_GAP (пауза между замерами, по умолчанию 35 — раунд идёт ~14 c),
#             WAIT_SEC (таймаут одного вебсокета, по умолчанию 12).

RATES_GAP="${RATES_GAP:-35}"
WAIT_SEC="${WAIT_SEC:-12}"
ROOT=/home/admin/crashgames
export ENGINE_WS="$ROOT/minigames-server/app_service/node_modules/ws"
ENV_FILE="$ROOT/minigames-admin-back/.env"

if [ -f /etc/nginx/conf.d/dev.demo.crash-heroes.com.conf ]; then
  ENVN=dev
  DEMO=https://dev.demo.crash-heroes.com/;   API=https://dev.api.crash-heroes.com/api/
  ADMIN=https://dev.admin.crash-heroes.com/; GAMES=https://dev.games.crash-heroes.com/fatguy/
  WSHOST=dev.server.crash-heroes.com
else
  ENVN=prod
  DEMO=https://demo.crash-heroes.com/;   API=https://api.crash-heroes.com/api/
  ADMIN=https://admin.crash-heroes.com/; GAMES=https://games.crash-heroes.com/fatguy/
  WSHOST=server.crash-heroes.com
fi
# У games нет индекса каталога: корень штатно отдаёт 403, поэтому проверяем
# конкретную сборку игры (/fatguy/), а не корень домена.

FAIL=0
say() { printf '%s\n' "$*"; }
ok()  { printf '  ✓ %s\n' "$*"; }
bad() { FAIL=1; printf '  ✗ %s\n' "$*"; }
# читает строки "OK<TAB>текст" / "FAIL<TAB>текст" из файла, без подоболочки
consume() { local st msg; while IFS=$'\t' read -r st msg; do
    [ "$st" = "OK" ] && ok "$msg" || bad "$msg"; done < "$1"; }

say "═══ Crash Heroes: проверка живости [$ENVN] $(date '+%Y-%m-%d %H:%M:%S') ═══"

# --- 1. сайты ---------------------------------------------------------------
say; say "[1/5] Публичные сайты"
for pair in "demo|$DEMO" "api|$API" "admin|$ADMIN" "games|$GAMES"; do
  name=${pair%%|*}; url=${pair#*|}
  read -r code time < <(curl -s -o /dev/null -w '%{http_code} %{time_total}' --max-time 20 "$url")
  line=$(printf '%-6s %s  %ss' "$name" "$code" "$time")
  [ "$code" = "200" ] && ok "$line" || bad "$line  $url"
done

IDS=$(grep -oP 'GAME_ID:\s*\K[0-9]+' "$ROOT/minigames-server/ecosystem.config.js" 2>/dev/null | sort -n -u | tr '\n' ' ')

# --- 2. вебсокеты: коэффициент должен меняться ------------------------------
say; say "[2/5] Вебсокеты игр: история коэффициентов пополняется (пауза ${RATES_GAP}с)"
if [ -z "$IDS" ]; then
  bad "не удалось получить список игр из ecosystem.config.js"
else
  source ~/.nvm/nvm.sh >/dev/null 2>&1
  TMP=$(mktemp)
  node -e '
// Тики (type:"tick") движок шлёт ТОЛЬКО авторизованным клиентам
// (main.mjs: client.player && client.player.token), анонимно их не увидеть.
// Зато "rates" отдаётся без авторизации и возвращает историю коэффициентов
// завершённых раундов. Снимаем её дважды с паузой: если история не изменилась —
// раунды не доигрывают или коэффициент залип.
const WebSocket = require(process.env.ENGINE_WS);
// argv: [node, -e, host, waitSec, gapSec, id1, id2, ...]
const H = process.argv[1];
const wait = Number(process.argv[2]) * 1000;
const gap  = Number(process.argv[3]) * 1000;
const list = process.argv.slice(4);

const sample = (id) => new Promise(res => {
  const out = { hello:false, rates:null, err:null };
  let ws;
  try { ws = new WebSocket(`wss://${H}/${id}`); }
  catch (e) { out.err = e.message; return res(out); }
  const done = () => { try { ws.terminate(); } catch(e){} res(out); };
  const t = setTimeout(done, wait);
  ws.on("open", () => setTimeout(() => { try { ws.send(JSON.stringify({type:"rates"})); } catch(e){} }, 300));
  ws.on("message", m => {
    try {
      const d = JSON.parse(m);
      if (d.success === true) out.hello = true;
      if (d.type === "rates") { out.rates = String(d.rates || "").trim(); clearTimeout(t); done(); }
    } catch(e) {}
  });
  ws.on("error", e => { out.err = e.message; clearTimeout(t); done(); });
});

(async () => {
  const a = await Promise.all(list.map(sample));
  await new Promise(r => setTimeout(r, gap));
  const b = await Promise.all(list.map(sample));
  list.forEach((id, i) => {
    const x = a[i], y = b[i];
    const err = x.err || y.err;
    if (err) return console.log(`FAIL\tигра ${String(id).padEnd(2)} ошибка: ${err}`);
    if (!x.hello || x.rates === null) return console.log(`FAIL\tигра ${String(id).padEnd(2)} нет ответа на rates`);
    const n1 = x.rates.split(/\s+/).filter(Boolean);
    const n2 = y.rates.split(/\s+/).filter(Boolean);
    const changed = x.rates !== y.rates;
    // main.mjs кладёт свежий коэффициент через unshift(), а pop() выбрасывает
    // самый старый, поэтому актуальное значение — нулевой элемент. Последний
    // меняется раз в 20 раундов (~5 минут) и при паузе в 35с всегда выглядит
    // застывшим — печатать его значило показывать «залипло» на живой игре.
    const new1 = n1[0], new2 = n2[0];
    console.log(`${changed ? "OK" : "FAIL"}\tигра ${String(id).padEnd(2)} ` +
      (changed ? `свежий коэффициент: ${new1} → ${new2}`
               : `КОЭФФИЦИЕНТ ЗАЛИП: за ${gap/1000}с история не изменилась (свежий ${new1})`));
  });
})();
' "$WSHOST" "$WAIT_SEC" "$RATES_GAP" $IDS > "$TMP" 2>/dev/null
  [ -s "$TMP" ] && consume "$TMP" || bad "node/ws не отработал (модуль $ENGINE_WS)"
  rm -f "$TMP"
fi

# --- 3. БД: раунды свежие, коэффициенты разные ------------------------------
say; say "[3/5] БД: раунды идут и коэффициенты различаются"
if [ ! -f "$ENV_FILE" ]; then bad "не найден $ENV_FILE"; else
  v() { grep -m1 "^$1=" "$ENV_FILE" | cut -d= -f2- | tr -d '"'; }
  export MYSQL_PWD=$(v DB_PASSWORD)
  Q="mysql -h127.0.0.1 -u$(v DB_USERNAME) $(v DB_DATABASE) -N -B"
  TMP=$(mktemp)
  # по каждой игре берём 10 последних раундов за полчаса:
  # сколько их, сколько среди них РАЗНЫХ коэффициентов и давно ли был последний
  $Q -e "
    SELECT g.game_id, COUNT(*), COUNT(DISTINCT g.coefficient),
           TIMESTAMPDIFF(SECOND, MAX(g.started_at), NOW())
    FROM (SELECT game_id, coefficient, started_at,
                 ROW_NUMBER() OVER (PARTITION BY game_id ORDER BY id DESC) rn
          FROM game_crash_rounds WHERE started_at > NOW() - INTERVAL 30 MINUTE) g
    WHERE g.rn <= 10 GROUP BY g.game_id;" > "$TMP" 2>/dev/null

  if [ ! -s "$TMP" ]; then bad "БД не ответила или раундов за 30 минут нет вообще"; else
    for id in $IDS; do
      row=$(awk -v g="$id" '$1==g {print; exit}' "$TMP")
      if [ -z "$row" ]; then bad "игра $id — за 30 минут ни одного раунда"; continue; fi
      set -- $row; n=$2; uniq=$3; age=$4
      if   [ "$age" -gt 120 ];  then bad "игра $(printf '%-2s' "$id") последний раунд ${age}с назад — раунды встали"
      elif [ "$uniq" -lt 2 ];  then bad "игра $(printf '%-2s' "$id") КОЭФФИЦИЕНТ ЗАЛИП: одно значение на $n раундов"
      else ok "игра $(printf '%-2s' "$id") раундов=$n разных кэфов=$uniq последний ${age}с назад"; fi
    done
  fi
  rm -f "$TMP"
fi

# --- 4. pm2 -----------------------------------------------------------------
say; say "[4/5] Процессы pm2"
source ~/.nvm/nvm.sh >/dev/null 2>&1
TMP=$(mktemp)
pm2 jlist 2>/dev/null | node -e '
let s=""; process.stdin.on("data", d => s += d).on("end", () => {
  let a; try { a = JSON.parse(s); } catch (e) { console.log("FAIL\tpm2 не отвечает"); return; }
  const off = a.filter(x => x.pm2_env.status !== "online");
  console.log(`${off.length ? "FAIL" : "OK"}\tonline ${a.length - off.length}/${a.length}` +
    (off.length ? ` — не работают: ${off.map(x => x.name).join(", ")}` : ""));
  // Модули pm2 (pm2-logrotate) перезапускаются на каждый `pm2 set`, их счётчик
  // рестартов ничего не говорит о здоровье игр — считаем только приложения.
  const hot = a.filter(x => !x.pm2_env.pmx_module && x.pm2_env.restart_time > 5);
  if (hot.length) console.log(`FAIL\tмного рестартов: ${hot.map(x => `${x.name}=${x.pm2_env.restart_time}`).join(", ")}`);
});' > "$TMP" 2>/dev/null
[ -s "$TMP" ] && consume "$TMP" || bad "pm2 не отвечает"
rm -f "$TMP"

# --- 5. диск ----------------------------------------------------------------
say; say "[5/5] Диск"
USE=$(df --output=pcent / | tail -1 | tr -dc '0-9')
AVAIL=$(df -h --output=avail / | tail -1 | tr -d ' ')
if [ "${USE:-100}" -lt 85 ]; then ok "занято ${USE}%, свободно $AVAIL"
else bad "занято ${USE}%, свободно $AVAIL — проверь логи в $ROOT/logs"; fi

say
[ "$FAIL" = "0" ] && say "ИТОГ: всё работает" || say "ИТОГ: ЕСТЬ ПРОБЛЕМЫ (см. ✗ выше)"
exit "$FAIL"
