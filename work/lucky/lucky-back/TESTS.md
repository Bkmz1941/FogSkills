# Тесты lucky-api: как устроены и что покрывают

Vitest, `npm run test` (59 файлов, ~320 тестов, ~2 с). Один файл или папка:
`npx vitest run <путь>`. Конфига vitest нет: подхватывается любой `*.spec.ts` под
`src/`, tsconfig включает спеки, поэтому `npm run typecheck` проверяет и их (ошибка
типов в тесте валит typecheck, а не только тест). Перед «готово»: `typecheck`, `lint`,
`test`, `build` — и коммит только после зелёного результата, а не в одной цепочке с ним.

## Где лежат

| Модуль | Расположение | Стиль |
|---|---|---|
| Все модули, кроме integrations | рядом с кодом: `foo.service.spec.ts` | как исторически сложилось у Кости |
| `integrations` | `src/modules/integrations/resources/tests/<слой>/…` | зеркалит слои модуля: `web/`, `game-provider/`, `config/` |

Тесты чисто модульные: базы и HTTP нет, зависимости передаются в конструктор
объектами-заглушками с `as never`. Интеграционный контур проверяется отдельно на
дев-стенде — `REGRESS.md`.

## Модуль integrations (47 кейсов)

**`web/game-provider.route-contract.spec.ts`** — контракт роутов через метаданные Nest:
префикс `external/game-provider`, пять методов с глаголами и кодами (`player/info` 200,
остальные 201), guard подписи на контроллере, аргументы хендлеров = body + request.
Любая смена пути или кода ответа ломает его первым — так и задумано.

**`web/game-provider-signature.guard.spec.ts`** — `GameProviderSignatureGuard`: подпись
считается по сырому телу (`request.rawBody`) со всеми полями, включая неизвестные DTO;
без сырого тела берётся разобранное; не-объект в теле даёт `invalid_request` до проверки
подписи; ошибки сервиса подписи пробрасываются.

**`config/api-exception.filter.spec.ts`** — конверт ошибок `{error:{code,message}}`:
типизированная `GameProviderError` как есть, массив сообщений class-validator склеен
через `; `, любая не-HTTP ошибка → 500 `internal_error`, отказ парсера тела Fastify
(объект со `statusCode`, не `HttpException`) → 400 `invalid_request`.
`ProviderErrorEnvelopeFilter`: под `/v1/external/game-provider/` конверт наш, вне него —
стандартный обработчик Nest (заглушка `host` обязана иметь `getArgByIndex`, иначе
`BaseExceptionFilter` падает).

**`game-provider/game-provider.service.spec.ts`** (31) — ядро:
- `verifySignature`: пустой payload с верной подписью принят, нет заголовков / чужой
  ключ / провайдер без секрета / неверная подпись — отказ;
- `toMinorUnits` / `fromMinorUnits`: точность без float, знак, усечение, обратный проход,
  minor unit ≠ 2;
- `makeBet` и компания: игрок и проект берутся из сессии, а не из тела; чужой провайдер,
  неизвестный токен, отключённый провайдер — типизированные коды; валюта фиксирована на
  сессии; отмена идёт как `CancelBet`; rollback отдаёт `reversed`;
- «signs the method and the path, matching the provider byte for byte» — **пиновый
  вектор**: HMAC-SHA256 от `POST\n/v1/external/game-provider/bet\n{}\n<канонический JSON>`
  ключом `s3cr3t`. Меняешь путь или каноническую форму — пересчитывай вектор той же
  функцией `signedPayload`, не руками (см. ловушки);
- жизнь сессии: закрытая (`closedAt`) и просроченная дольше одного лишнего TTL →
  `session_expired`; просроченная недавно (60 с) — расчёт проходит;
- `playerInfo`: читает кошелёк по `currency_code` и `balance_code` сессии, без валюты —
  любой кошелёк этого кода;
- ответы: повтор отдаёт сохранённый ответ и ничего не пишет; свежий расчёт берёт
  `createdAt` из `completedAt` финансов и сохраняет ответ; `balanceCode` сессии
  уходит в финансы.

**`game-provider/game-launch.service.spec.ts`** — custom-code игра запускается без
провайдера; провайдер без ключей/launch URL даёт `unavailable:true`. Конструктор
сервиса принимает 7 зависимостей (последняя — `PlayerBalancesService`).

## Финансы, игровые раунды (`src/modules/transactions`)

**`finance-game-round.spec.ts`** — `FinanceService` с фальшивым `DataSource.transaction`
и менеджером, который по классу сущности отдаёт заглушку репозитория и пишет журнал
вызовов (`wallet:lock`, `tx:existsBy`, `tx:insert`…):
блокировка кошелька раньше проверок повтора и надгробия; строка пишется `insert`, не
`save`; повтор отдаёт сохранённый ответ и не двигает деньги; откат ставки возвращает
ставку; откат отмены и выигрыша **списывает** обратно; повторный откат отвечает тем же.
Детерминированные id транзакций получаются прогоном на отдельном harness — отдельного
хелпера для `game-round:` id нет, экспортирован только `toRollbackId`.

**`money.spec.ts`** — `moneyUnits`/`formatMoney`: без float, отказ на мусор и лишнюю
точность, minor unit валюты, потолок 16 целых цифр (`numeric(24,8)`).

## Ловушки

- В `game-provider.service.spec.ts` два 64-hex значения: константа `privateKey` вверху
  и пиновый вектор в `.toBe(...)`. `grep`-замена «первого hex» задевает ключ, а не
  вектор — 2026-09-09 так ушёл красный коммит. Считать вектор так:
  `node -e` с той же канонизацией (`JSON.stringify` отсортированных ключей, `/` → `\/`),
  а не вручную экранировать строку.
- Логгер `ApiExceptionFilter` пишет в stderr при тесте на 500 — это ожидаемый шум.
- Заглушки `createQueryBuilder` должны поддерживать всю цепочку конкретного запроса
  (`innerJoin/select/addSelect/where/andWhere/orderBy/limit/getRawOne` у `getBalance`,
  `setLock/where/andWhere/getOne` у блокировки кошелька) — при добавлении звена в
  запрос тест падает с `is not a function`, это подсказка, а не баг.
- Финансовые заглушки в тестах модуля возвращают `{ txId }` вместо `{ transactionId }`:
  сервис к этому терпим (`completedAt ?? new Date()`), проверяются только входы.
