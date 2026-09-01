---
name: table-filter
description: Спецификация компонента `TableFilter` (контейнер фильтров для таблицы) — состояния, поведение, режимы Classical/Simple, +N overflow, двухпанельный FilterDropdown. Источник — скрины дизайнера в `~/Pictures/Screenshots/Admin-UI/TableFilter/`.
---

# TableFilter

Контейнер фильтров для таблицы. Объединяет: поиск, кнопку «Filters» (или отдельные filter-кнопки в Simple-режиме), chips применённых фильтров, +N overflow, кнопку Reset, правую часть с refresh + основным CTA (например, `+ Add`).

**Источник дизайна:**

Канонический — Figma-файл `Shadcn-Universal-DS` (`file_id=hDYKtl651NL0aPgg7owedU`). Каждый атом компонента живёт в отдельном фрейме:

| Часть | node_id | URL |
|-------|---------|-----|
| Обзорная страница «Фильтры» | `25374:132124` | [→](https://www.figma.com/design/hDYKtl651NL0aPgg7owedU/Shadcn-Universal-DS?node-id=25374-132124) |
| **Filter field** (контейнер) | `25374:131522` | [→](https://www.figma.com/design/hDYKtl651NL0aPgg7owedU/Shadcn-Universal-DS?node-id=25374-131522) |
| **Filter Button Primary** | `25374:131502` | [→](https://www.figma.com/design/hDYKtl651NL0aPgg7owedU/Shadcn-Universal-DS?node-id=25374-131502) |
| **Filter Button Secondary** | `25374:131541` | [→](https://www.figma.com/design/hDYKtl651NL0aPgg7owedU/Shadcn-Universal-DS?node-id=25374-131541) |
| **Filter Dropdown** | `25374:131538` | [→](https://www.figma.com/design/hDYKtl651NL0aPgg7owedU/Shadcn-Universal-DS?node-id=25374-131538) |
| **Counter** | `25374:131514` | [→](https://www.figma.com/design/hDYKtl651NL0aPgg7owedU/Shadcn-Universal-DS?node-id=25374-131514) |

Читается через Figma MCP (Framelink, после рестарта CLI) или напрямую: `curl -H "X-Figma-Token: $TOKEN" "https://api.figma.com/v1/files/hDYKtl651NL0aPgg7owedU/nodes?ids=25374:131522,25374:131502,..."`.

**Скрины (исторический срез):** `~/Pictures/Screenshots/Admin-UI/TableFilter/` (11 скринов, 14:41–14:42, 27.04.2026). Если Figma и скрин расходятся — **Figma источник правды**.

**Где живёт сейчас:** контейнера-оркестратора нет. В админке есть узкие фильтры под колонки: `src/components/shared/table/filters/TableFilterCalendar.tsx`, `TableFilterVersions.tsx`. Их потенциально надо переписать поверх нового контейнера.

## Анатомия

```
[ Search ] [ Filters N ]  [ chip 5 × ] [ chip × ] [ +N ]  Reset       [ ↻ ] [ + Add ]
└────────── filter bar (fill, gap=24px до правой части) ──────────┘   └ actions ┘
```

Слева направо в filter bar:
1. **Search** — `input-search`.
2. **Filters button** (Primary) — открывает `FilterDropdown` со списком всех фильтров. В Simple-режиме (<3 фильтров) **отсутствует**.
3. **Chips применённых фильтров** (Secondary) — каждый chip = название + counter значений + крестик. Клик по телу chip'а (не по крестику) открывает `FilterDropdown` уже на своей секции.
4. **+N overflow** — кнопка с числом скрытых фильтров. Клик открывает `FilterDropdown` на самом левом скрытом.
5. **Reset** (текстовая ссылка) — сбрасывает все фильтры. Появляется только когда применён ≥1 фильтр.

В Simple-режиме блок 2–4 заменяется на ряд отдельных filter-кнопок-dropdown'ов (по одной на фильтр). Reset работает так же.

## Состояния контейнера

| # | Состояние | Что видно |
|---|-----------|-----------|
| 1 | Пусто | Search + `Filters` (без счётчика). Reset скрыт. |
| 2 | Есть ≥1 фильтр | `Filters N` (счётчик = число применённых **фильтров**, не значений) + chips + Reset. |
| 3 | Overflow | Лишние chips прячутся за `+N`. Видимые ранжируются по порядку добавления. |
| 4 | Edge-case: 1 длинный фильтр не влез | Chip скрывается, `+N` **не показывается** (счётчик в `Filters` уже сообщает). |
| 5 | Simple (<3 фильтров) | Нет `Filters`, отдельные filter-кнопки. |

Счётчик в `Filters N` = количество **фильтров** с непустым значением. Counter внутри chip = количество **значений** в этом фильтре (для multi-select).

## Правила overflow

- Контейнер занимает доступную ширину (`fill`), gap до правой части — **24px**.
- Фильтры показываются слева направо в **порядке выбора**. Раньше выбранный — выше по приоритету (его не прячут первым).
- При нехватке места — лишние схлопываются в `+N` справа от видимых chips.
- При повторном открытии/изменении уже применённого фильтра порядок **не меняется**.
- UX-совет дизайнера: «если важно, чтобы конкретный фильтр всегда оставался видимым (например, дата или язык), рекомендуется выбирать его первым».

### Исключение
Если применён ровно один фильтр и его chip не помещается (длинное название/значение), chip скрывается полностью, `+N` **не показывается**. Информация о наличии фильтра дублируется счётчиком `Filters 1`.

## FilterDropdown

Источник: Figma node `25374:131538`. Также присутствует в `State=Opened` у обоих FilterButton'ов.

**База:**
- Размер контейнера: **776×523 px** (фиксирован в эталоне; в реальности ширина высоты могут адаптироваться к контенту слота).
- Border-radius **10px**, stroke 1px **`#e5e5e5`**.
- Layout: горизонтально, две панели + общий скроллбар справа.

**Левая панель — список фильтров (Sidebar 07.):**
- 256×523, fill `#fafafa`, stroke справа `#e5e5e5` (разделитель панелей).
- Построена на shadcn `Sidebar/*` примитивах (см. ниже).
- Структура:
  - **SidebarHeader** (256×64, padding 8): слот для заголовка/выбора (в дизайне — `SidebarMenuButton` 240×48 с MediaAsset 32×32 + Flex Vertical для текста + CollapseIcon).
  - **SidebarContent** (gap 8): несколько `SidebarGroup`'ов. В референсе показаны 3 группы — каждая `padding: 8/16` + GroupLabel + SidebarMenu.
  - **SidebarFooter** (256×52, padding 16 top / 8 bottom / 16 left/right): кнопка `Reset all`. Текст «Reset all», шрифт Geist 500 / 14, цвет **`#3b82f6`** (синий, ссылка). Background прозрачный.

**Правая панель — содержимое активной секции (Slot):**
- 520×523, fill `#ffffff`.
- Внутри:
  - **Slot** 520×471: padding `16 top / 24 bottom / 16 left / 16 right`, gap **14**. Сюда host-компонент (FilterField) рендерит `renderDropdown` активного фильтра. Контент свободный — radio-list, calendar, multi-select.
  - **SidebarFooter** 520×52: кнопка `Reset` (только активная секция). Стиль идентичен `Reset all` — Geist 500/14 / `#3b82f6` / прозрачный фон.

**Scrollbar:** 7px, rounded 100, fill `#e4e4e7`. Внутренний (overlay), не системный.

> ⚠️ **Архитектурный сигнал:** левая панель — это shadcn `<Sidebar>` со всеми его компонентами (`SidebarHeader`, `SidebarContent`, `SidebarGroup`, `SidebarGroupLabel`, `SidebarMenu`, `SidebarFooter`). Это значит — **в либе `@agg/admin-ui` сначала надо иметь shadcn Sidebar в `ui/`** (если ещё нет), и поверх него собирать FilterDropdown. Не писать двухпанельный popover с нуля.

**Двухпанельная композиция:**

```
┌─────────────────┬────────────────────────────────┐
│ ▢ Date     1    │  Show date for                 │
│ ▢ OS       5    │  [ Custom ▾ ]                  │
│ ▢ Friendly 2    │  Start date     End date       │
│ ▢ Language 1    │  [ ... ]      [ ... ]          │
│ ▢ Segment  3    │  ◀  Jan 2026   Feb 2026  ▶    │
│                 │   ...                          │
│ Reset all       │                          Reset │
└─────────────────┴────────────────────────────────┘
```

- **Левая колонка** — список всех фильтров с counter'ами (= число значений в каждом). Активная секция выделена. Реализуется через shadcn `SidebarMenu` с активным `SidebarMenuButton`.
- **Правая колонка** — содержимое активной секции. Полностью кастомное (radio-list с поиском, calendar range, multi-select). Slot принимает любой ReactNode.
- **Reset all** (слева внизу, в `SidebarFooter`) — сбрасывает значения всех фильтров.
- **Reset** (справа внизу) — сбрасывает только активную секцию.

### Откуда открывается, какая секция активна по умолчанию

| Источник | Активная секция |
|----------|-----------------|
| Кнопка `Filters` | Первая по конфигу (или Date — нужно уточнить у дизайнера) |
| Chip применённого фильтра | Соответствующая секция |
| `+N` | Самый левый из скрытых фильтров (т.е. с наибольшим приоритетом среди скрытых) |

Если пользователь меняет параметры скрытого фильтра через `+N`, **порядок не изменяется** (он остаётся скрытым на своём месте).

## Атомы дизайн-системы

Из скринов выделяются переиспользуемые атомы:

### Counter

Бейдж-счётчик. Источник: Figma node `25374:131514`.

| | Primary | Secondary |
|---|---|---|
| Размер | 16×16 px | 16×16 px |
| Padding | 2px (все стороны) | 2px (все стороны) |
| Border radius | 4px | 4px |
| Background | `#e5e5e5` (FigmaVar `23354:17355`) | `#f5f5f5` (FigmaVar `1:447`) |
| Цвет текста | `#0a0a0a` (FigmaVar `1:455`) | `#0a0a0a` (FigmaVar `1:455`) |
| Шрифт | Geist 400, 12px / lh 16px | Geist 400, 12px / lh 16px |
| Контент | число (например `2`) | число |

**Где используется:**
- **Primary** — внутри кнопки `Filters N` (Filter Button Primary в состоянии Chosen) и, вероятно, в строках `FilterDropdown` для счётчика значений в каждом фильтре.
- **Secondary** — внутри chip применённого фильтра (Filter Button Secondary).

⚠️ Уточнение от Figma: оба варианта **светлые**, отличаются только оттенком фона (`#e5e5e5` vs `#f5f5f5`). В исходной спеке со скринов было «Primary — тёмный, Secondary — бледный» — это было неверной интерпретацией. Контраст с фоном кнопки идёт за счёт того, что окружающая кнопка тоже светлая (Counter чуть темнее → читается).

**Реализация:** маленький отдельный компонент в `agg/counter.tsx` (или `ui/counter.tsx`). Через CVA вариант `primary | secondary`. Использует существующие токены ваших компонентов (через Tailwind v4 `--color-*` переменные, которые мапятся на FigmaVar).

### FilterButton

#### Primary (главная кнопка `Filters`)

Источник: Figma node `25374:131502`. COMPONENT_SET с 4 вариантами `State=Default|Hover|Chosen|Opened`.

**Общее для всех состояний:**
- Высота 36px, padding `8px 12px`, gap между элементами 8px, border-radius 8px, stroke 1px.
- Layout: `[icon ListFilter 16×16] [gap 8] [Frame с текстом + опц. Counter, gap 4]`.
- Иконка: `lucide:list-filter`, цвет `#0a0a0a`.
- Текст: «Filters», шрифт **Geist 400 / 14px / lh 20**, цвет `#0a0a0a`.

**Состояния (только что меняется относительно базы):**

| Состояние | Width | Background | Border | Counter (16×16) | Заметки |
|-----------|-------|------------|--------|-----------------|---------|
| Default | 88px | `#ffffff` | `#e5e5e5` | — (нет) | Иконка + «Filters». |
| Hover | 88px | `#ffffff` → `#f5f5f5` | `#e5e5e5` | — | В Figma Hover==Default на уровне токенов (вероятно, дизайнер не дополнил). **Решение в коде:** добавили видимый hover `bg-neutral-100` (#f5f5f5) для UX-обратки. Если дизайнер скажет «не надо» — снимем. |
| Chosen | 112px | `#f5f5f5` | `#e5e5e5` | Counter Primary (`#e5e5e5` fill) с числом | На width: 112 = 88 + 24 (16 counter + 8 gap). Hover в Chosen — `bg-neutral-200` (на ступень темнее). |
| Opened | 112px | `#f5f5f5` | `#0a0a0a` | Counter Primary | Dropdown визуально пристёгнут справа. |

Вспомогательная заметка по dropdown в `State=Opened`: **левая колонка построена на shadcn `Sidebar/*` примитивах** (`SidebarHeader`, `SidebarGroup`, `SidebarGroupLabel`, `SidebarMenu`, `SidebarFooter`). Это означает: для FilterDropdown в либе **можно/нужно опереться на shadcn Sidebar**, а не писать с нуля.

#### Secondary (chip применённого фильтра)

Источник: Figma node `25374:131541`. COMPONENT_SET с 3 вариантами `State=Default|Hover|Opened`.

**Общее для всех состояний:**
- Высота 36px, padding `8px 12px`, gap 8px, border-radius 8px, stroke 1px.
- Border цвет — **`#0a0a0a` (чёрный)** во всех состояниях — это ключевое отличие от Primary, у которого border `#e5e5e5`. Чёрный border = «активный» вид, сообщает что фильтр уже применён.
- Layout: `[icon ListFilter 16×16] [gap 8] [text «Filter name» + Counter, gap 4] [gap 8] [icon X 16×16]`.
- Иконка слева: `lucide:list-filter`, цвет `#0a0a0a`.
- Текст: Geist 400 / 14px / lh 20, цвет `#0a0a0a`.
- Counter: вариант **Primary** Counter (`#e5e5e5` fill), число выбранных значений — например `5`.
  ⚠️ Заметка: Counter в chip'е использует Primary вариант (#e5e5e5), а не Secondary (#f5f5f5). Кажется контр-интуитивным («Secondary chip → Primary counter»), но это нужно для контраста: chip уже на светлом фоне (#ffffff/#f5f5f5), так что counter должен быть чуть темнее, чтобы читался.
- Иконка справа: `lucide:x`, цвет `#0a0a0a`. Кликабельная отдельно — удаляет фильтр без открытия dropdown.

**Состояния:**

| Состояние | Background | Заметки |
|-----------|------------|---------|
| Default | `#ffffff` | Базовый chip. |
| Hover | `#f5f5f5` | Фон затемняется до того же #f5f5f5 что и у Primary в Chosen/Opened — это базовый «touched» оттенок системы. |
| Opened | `#f5f5f5` | Тот же фон что Hover. Dropdown визуально пристёгнут справа, идентичен Filter Dropdown из Primary Opened. |

**Размер:** ширина зависит от длины текста. В референсе на «Filter name» + counter `5` ширина = 140px. Контейнер реализует через `width: fit-content`. Длинное название/значение → переполнение → скрытие в `+N` (см. правила overflow контейнера).

**Поведение:**
- Клик по **телу** (всё кроме X) → открывает FilterDropdown с активной соответствующей секцией.
- Клик по **X** → `onRemove(filterId)`, dropdown не открывается. В implementation: `e.stopPropagation()` на X, отдельный `<button>` внутри.

## Simple-режим

Триггер: `filters.length < 3` (три фильтра — порог, при ≥3 включается Classical).

Особенности:
- Нет общего `Filters` dropdown.
- Каждый фильтр = отдельная кнопка-dropdown прямо в баре, на ней — стрелочка вниз.
- При наличии значения: кнопка получает counter (Secondary) и крестик, ведёт себя как chip из Classical, но клик открывает свой одиночный dropdown (без двухпанельной композиции).
- Reset работает по тем же правилам.
- Правила overflow и edge-case длинного значения — те же.

## Предполагаемая декомпозиция

**Предзависимости (есть в либе):**
- ✅ shadcn `Sidebar/*` (`src/components/ui/sidebar.tsx` в `Admin-ui`) — нужен для FilterDropdown.
- ✅ `better-badge` (`src/components/agg/better-badge`) — может стать базой для Counter (или Counter будет отдельным маленьким компонентом).
- ✅ Tailwind v4 + shadcn `style: new-york`, base `zinc`.

**Порядок имплементации (bottom-up, по мере усложнения):**

1. **Counter** — `agg/counter.tsx` (16×16, 2 варианта Primary/Secondary через CVA). Самый простой компонент, отличный first-PR.
2. **FilterButton** — `agg/filter-button.tsx`. Один компонент с проп `variant: 'primary' | 'secondary'`. Состояния (`default`/`hover`/`chosen`/`opened`) — частично через CVA + data-attrs, частично через Radix Popover state. Использует Counter.
3. **FilterDropdown** — `agg/filter-dropdown.tsx`. Двухпанельная композиция поверх Radix Popover. Левая панель — на shadcn `Sidebar/*` примитивах (уже в либе). Правая панель — slot, принимает любой ReactNode. Использует Counter в строках сайдбара.
4. **FilterField** (контейнер) — `agg/filter-field.tsx`. Принимает `filters: FilterConfig[]`, опции `searchSlot`, `actionsSlot`. Внутри:
   - `useFilterOverflow(filters, ref)` — измеряет ширину, отдаёт `{ visible, hidden }`.
   - Решение Classical vs Simple — по `filters.length`.
   - Связывает chip'ы с открытием FilterDropdown на нужной секции.

## API (черновик)

```ts
type FilterConfig<TValue = unknown> = {
  id: string
  label: string
  icon?: ReactNode
  value: TValue | undefined
  onChange: (value: TValue | undefined) => void
  /** Что показывать в counter chip'а (число выбранных значений). Если undefined — counter не рендерится. */
  getCount?: (value: TValue) => number | undefined
  /** Текст значения в chip'е (для длинных значений вроде "12.01.2026 – 08.06.2026"). */
  formatValue?: (value: TValue) => string
  /** Slot для содержимого dropdown'а (правая колонка / одиночный dropdown в Simple). */
  renderDropdown: (props: {
    value: TValue | undefined
    onChange: (v: TValue | undefined) => void
    onClose: () => void
  }) => ReactNode
}

type FilterFieldProps = {
  filters: FilterConfig[]
  /** Порядок отображения применённых фильтров. Контролируемый (хранится снаружи). */
  appliedOrder: string[]
  onAppliedOrderChange: (order: string[]) => void
  onResetAll: () => void
  searchSlot?: ReactNode
  actionsSlot?: ReactNode  // refresh + Add
  className?: string
}
```

`appliedOrder` нужен снаружи, чтобы переживал ремаунты (например, в URL). Хранит **id фильтров в порядке выбора**.

## Реализационные находки (важные)

### Sub-pixel overflow в `useFilterOverflow`

**Где:** `src/components/shared/table-filter/useFilterOverflow.ts`

**Контекст:** Когда применённый фильтр имеет `formatValue` с длинным текстом (например, Friendly «campaign-summer-2026»), его chip резко расширяется с ~110px до ~250px. Хук пересчитывает overflow и решает сколько chips влезет, **но на грани лимита** flex-layout рендерит чипы с **дробной точностью** (например, last chip.right = 1251.47), а хук считает в integer (`offsetWidth`). Этот subpixel рассинхрон в 0.47-1px по всей цепочке flex может пробивать видимое и давать горизонтальный скролл страницы.

**Решение:** В хук добавлен `SAFETY_MARGIN_PX = 16` — резерв 16px свободного места поверх `limit`. Hook over-collapses на 1 chip, гарантированно вписывая остальные:

```ts
const SAFETY_MARGIN_PX = 16
// ...
limit = trackWidth - plusNWidth - GAP_PX - resetReserve - SAFETY_MARGIN_PX
```

**Симптом который это лечит:** «выбираю 9-10 фильтров → +N появляется → горизонтальный скролл страницы». Без margin визуально может казаться что в `+N` ушло «на один меньше чем нужно».

### Mode-switch vs apply внутри режима

При **переключении** Simple↔Classical React полностью переcоздаёт дерево чипов (разные render-ветки) — никогда не было багов с шириной. При **apply внутри одного режима** (Simple→apply, Classical→apply) chip-элементы переиспользуются — здесь subpixel вылезал. Safety margin ровняет поведение.

## Открытые вопросы

> Статус по состоянию на 2026-04-30 после извлечения данных из Figma.

1. ⏳ **Порог Simple-режима** — `<3` или `≤3`? Извлечь из Figma node `25374:131522` (Filter field) — там должны быть оба референса Classical и Simple с понятным числом фильтров. Пока не вытащено (rate-limit Figma API). Дополнить когда докачаем.

2. ⏳ **Активная секция при открытии через `Filters`** — первая по конфигу или фиксированная (Date)? Из dropdown-структуры видно, что левая панель — `SidebarMenu`, активная подсветка — `SidebarMenuButton[data-active]`. Поведение по умолчанию (какая активна при mount) **не зафиксировано в дизайне** — это поведенческий вопрос к дизайнеру/PM. **Предложение по умолчанию:** первая по `filters[]`, если не передан проп `defaultActiveFilterId`.

3. ✅ **Counter у date-range** — закрыто. Из FilterButton Secondary (Figma `25374:131541`) видно: counter присутствует структурно всегда, в API спрятан/показан через `getCount`. Соглашение: **counter рендерится только если `getCount(value)` возвращает число > 0**. Для date-range `getCount` не передаётся → counter не рендерится; в chip'е остаётся только текст значения через `formatValue`.

4. 🟡 **Куда уезжает контейнер** — **Библиотека `@agg/admin-ui`**, аргумент усилился. Из Figma видно, что левая панель FilterDropdown построена на shadcn `Sidebar/*` примитивах — это «здание базового уровня», которое должно жить в либе. Соответственно, Counter → FilterButton{Primary,Secondary} → FilterDropdown → FilterField — **все в либе**. В админке (`shared/`) остаётся только адаптер под TanStack Table (если он вообще нужен сверху над FilterField, или просто использовать FilterField напрямую).

5. ⏳ **Переиспользование существующих фильтров** (`TableFilterCalendar.tsx`, `TableFilterVersions.tsx`) — это вопрос миграции, отвечается после имплементации FilterField. План: после релиза FilterField в либе — переписать страницы, которые используют эти компоненты, на новую конструкцию (`<FilterField filters={[{id:'date', renderDropdown: <CalendarRangePicker/>}]} ...>`). Старые файлы удалить.

## Скрины

Все в `~/Pictures/Screenshots/Admin-UI/TableFilter/`:

- `14-41-06.png` — обычное состояние + состояние с одним фильтром
- `14-41-14.png` — максимальное количество фильтров (fill контейнера, gap 24px)
- `14-41-22.png` — overflow с `+N` + правила приоритета
- `14-41-37.png` — поведение `+N` (открытие dropdown'а скрытого фильтра)
- `14-41-59.png` — Filter field simple
- `14-42-09.png` — Counter (Primary/Secondary)
- `14-42-17.png` — Filter Dropdown (двухпанельный)
- `14-42-24.png` — Filter Button Primary (4 состояния)
- `14-42-29.png` — Filter Button Secondary (3 состояния)
- `14-42-45.png` — Filter field Classical (Default/Filled)
- `14-42-52.png` — Filter field Simple (с/без значений) + actions
