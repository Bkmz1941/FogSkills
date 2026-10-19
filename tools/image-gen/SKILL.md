---
name: image-gen
description: Генерация картинок локально на видеокарте Ильи — команда `ig` (ComfyUI + FLUX.2 klein 4B GGUF) на /media/ilya/T714/image-gen. Иконки предметов, одежды, картинки рецептов и справочника «Таверны» в её стилях, промпты под каждый стиль, куда класть результат, лимиты памяти. Активируй на «сгенерируй картинку», «нарисуй иконку», «сделай картинку для инвентаря/рецепта/справочника», «ig», «генерация картинок», «как в леонардо», «nano banana», «локальная генерация».
---

# Генерация картинок (ig)

Картинки считаются локально на RTX 3060 Ti (8 ГБ), наружу ничего не уходит,
лимитов нет. Заменяет Leonardo (nano banana lite) для иконок и простых
картинок; Илья 05.10 после первых проб: «оч прикольно получается, это то что
надо».

**Корень:** `/media/ilya/T714/image-gen` (внешний диск, exFAT). Команда `ig`
в PATH через `~/.local/bin/ig` → симлинк на `$ROOT/ig`.

## ⭐ Правило 0 — ПОДРОБНЫЕ РИСУНКИ НЕ РИСУЕМ (Илья 18.10)

Картинки НА предмете (этикетки, обёртки, наклейки, принты) — простой условный значок, а не
иллюстрация. Илья 18.10 про «Коровку» с подробной коровой на обёртке: «коровку абстрактнее» →
«да, подробные рисунки не рисуем — в скил». Мера: значок узнаётся с первого взгляда в клетке
64 px, но состоит из нескольких плоских форм, без штриховки, мелких черт, теней и фона-пейзажа.
Слишком далеко тоже плохо: «абстрактная эмблема из геометрических фигур» (18.10) дала просто
пятна, корову не узнать. Фраза в промпт:
`printed with a simple flat <что> icon made of a few bold flat shapes, like a minimal sticker,
easy to recognize, no fine details, no shading`.

## ⭐ Правило 1 — КАМЕРА: как камера смотрит на картинку (Илья 05.10, ⭐ эталон — молоко, 19.10)

⭐ **19.10 Илья: «эталон — пачка молока по тому, как стоит объект в иконке».** Эталон камеры —
`Fog/Kitchen/milk_carton/milk_carton_4.png`: ТРИ ЧЕТВЕРТИ спереди-слева и чуть сверху (~30°),
видны лицевая грань, правая боковая (заметно темнее, угол между ними — чёткое ребро) и верх.
(Утром 19.10 было «как у кофе» — вид в лоб с узкой полоской сбоку; Илья: «картинки — не так»,
отменено.) Фраза в промпт (держать дословно, `$CAM`):
`the whole item fully visible and centered with generous empty margin around it, three-quarter view
from the front-left and slightly from above (about 30 degrees), the front panel and the right side
panel both clearly visible, the right side panel about half as wide as the front panel and clearly
shaded darker so the vertical corner edge between them is sharp and visible, the top visible, bold
black outline on every edge`.
Тонкие коробки (Илья: «длина вглубь — её меньше») — убрать из `$CAM` «about half as wide as the front
panel» и добавить к предмету `like a thin book standing upright, the box is very thin, its depth only
one fifth of its width, so the right side panel and the top are narrow strips` — иначе модель рисует кубик.
По правилу сделаны `coffee_pack_2` (`out/coffee_milkcam_1152583912`, пакет с плоским дном `block-bottom
bag … shaped like a box`, этикетка сама встала по центру) и `filter_pack_2` (`out/filterbox_thin3q_1152583911`).
Плоские предметы, которые смотрятся только сбоку (фильтр-лист), — силуэтом сбоку, как `coffee_filter_2`.


Одна камера на все картинки предметов, чтобы инвентарь и справочник читались
как один набор. До 05.10 у одежды был разнобой: футболки, джинсы и куртка
сняты в лоб и обрезаны краем кадра, обувь и сумка — целиком в три четверти.

- ⭐ **Эталон формата — `Fog/Clothes/tshirt_red/tshirt_red_2.png`** (Илья 05.10:
  «вот такие супер, давай под эталон считать формат, только крупнее, чтобы
  отступ был меньше от краёв и почти всю клетку занимал контент»).
- ⭐ **СТАНДАРТЫ ИКОНОК ПО ФОРМЕ КЛЕТКИ** (Илья 18.10: «стандарты надо установить типо 1x1,
  2x1, 2x2, 1x2 и т. д., в таком формате как рисуется, отступы, пропорции»; до того: «на все
  иконки правило — отступы как у молока ×2» → 14 %, «уменьши на 30 %» → 9,8 %; «молоко ниже, а
  вода выше — единые пропорции»). Все иконки одной формы клетки выглядят одного роста:

  | Клетка | Холст | Поле со всех сторон | Рамка под предмет | Предмет упирается в | Пропорция предмета на картинке |
  |---|---|---|---|---|---|
  | 1×1 | 1024×1024 | 100 px | 824×824 | длинной стороной в 824 | любая, компактный предмет |
  | 2×2 | 1024×1024 | 100 px | 824×824 | длинной стороной в 824 | любая |
  | 1×2 (высокая) | 512×1024 | 50 px | 412×924 | **высотой в 924** | высота/ширина **≥ 2,24** |
  | 2×1 (широкая) | 1024×512 | 50 px | 924×412 | **шириной в 924** | ширина/высота **≥ 2,24** |
  | другое N×M | длинная сторона 1024, короткая 1024·min/max | 9,8 % короткой | холст − 2 поля | длинной стороной | как у рамки |

  - Поле = 9,8 % КОРОТКОЙ стороны холста (`MARGIN = 0.098` в `gen.py`). `ig --fit-only a.png
    --cell 1x1|2x2|1x2|2x1` вписывает по таблице.
  - Высокие и широкие клетки заполняются по ДЛИННОЙ стороне: так бутылка, банка и пакет в 1×2 —
    одной высоты 924 px. Если предмет на картинке приземистый (пропорция ниже 2,24), он упрётся
    в ширину и выйдет ниже соседей. `fit()` тогда печатает «⚠ приземистая для клетки…» —
    такую картинку НЕ ставить, а перерисовать вытянутее: в промпт `tall narrow …, three times
    taller than it is wide` (для 2×1 — `long low …, three times wider than tall`). Модель
    обычно недотягивает: 18.10 «two and a half times taller» дало 1,85–1,91.
  - Ориентация холста = ориентация клетки (высокий предмет — на высоком холсте). Страница
    иконок поворачивает картинку, если ориентации не совпали; как поступает инвентарь — не
    проверено.
  - Иконки до 18.10 сделаны по старому полю (7 % длинной стороны, высокие 879 px). Илья 18.10:
    «не надо другие переделывать» — старые НЕ трогать без его слова; по стандарту делаем новые и
    те, что он сам просит переделать. Тогда пересобирать из исходника (`Fog/<тема>/<id>/<id>_1.png`),
    не из ужатой игровой. Не по стандарту на 18.10 (если попросит):  широкие `egg_carton`, `sausage_pack`;
    остальные высокие 1×2 — только перевписать (879 → 924 px). Варианты, нарисованные 18.10 и не
    поставленные: `out/coffee_slim_1152583910` (2,42), `out/filter_kraft_1152583911` (2,5),
    `out/eggs_wide_1152583910` (2,84), `out/banana_wide_1152583910` (2,4),
    `out/sausage_wide_1152583914` (2,48). Скрипт перевписывания:
    scratchpad сессии c43ce975 `refit.py` (`id=исходник`, `--dry` — только проверка).
  - Вытянутость проще получить ХОЛСТОМ генерации: `-W 1024 -H 512` для 2×1 (`-W 512 -H 1024`
    для 1×2) + в промпте `long and low, three times wider than it is tall, lying horizontally`.
    Белая коробка вместо картонной: называть материал явно (`brown kraft cardboard, tan front
    panel and darker brown side panel`).
  - Молоко 18.10 (Илья: «штучка питьевая не там», потом «грань потерялась»): крышка — посередине
    переднего ската крыши (`a small round blue screw cap in the middle of the front sloping roof
    panel of the gable top`), боковая грань заметно темнее лицевой (`the right side panel
    clearly shaded darker blue-grey so the vertical corner edge between them is sharp and
    visible, bold black outline on every edge`). Иначе на тёмной клетке белый пакет сливается
    в одно пятно. В игре и на сайте — `Fog/Kitchen/milk_carton/milk_carton_3.png`
    (`out/milk_slim_1152583913`, пропорция 2,18 → 898 из 924 px; промпт — высокий литровый пакет
    `shaped like a tall narrow box, three times taller than it is wide`).
- ⭐ **Переделал иконку → СРАЗУ меняй её и на сайте** (Илья 18.10: «а на сайте меняй тоже
  сразу иконку»). Сайт — раздел «Иконки» путеводителя «Бумаги в доме»
  https://claude.ai/artifact/DJ5sV1bE4S3DuDnnro3PWs (картинки в `icons/<файл>.png`,
  подробности — скил tavern-newspaper). Страница принадлежит аккаунту **bkmz1941f@gmail.com**:
  из-под it@agg.one она даёт 404 — сначала `/login` в gmail (18.10 так и сделали). Порядок:
  Artifact `read` по url (без path — засчитывает просмотр), `read` с `path: "index.html"` →
  файл в scratchpad; ⚠️ в сохранённом файле сверху обёртка публикации (`<!doctype html><html>
  <head><meta charset=utf8>…<body>` до второго `<!doctype html>`) и `</body></html>` в конце —
  срезать, иначе обёртка задвоится; поднять кэш-метку `.png?v=N` (в двух местах; 18.10 → v=6);
  положить новую иконку в `icons/<файл>.png` ПОЛНОГО размера (как в игре, не миниатюру) и
  publish с тем же `url`, `file_path` = index.html, `files: {"icons/<файл>.png": …}`.
- `candy_korovka` 18.10 (Илья: «иконку конфеты коровки переделаем», потом «коровку абстрактнее»):
  бумажная обёртка с подогнутыми концами, сверху ПРОСТОЙ значок — голова коровы на голубой плашке
  (правило 0). Промпт: `a single soft fudge candy wrapped in a small rectangular chunky cream-white
  paper wrapper with both ends neatly folded under like an envelope, the top of the wrapper printed
  with a simple flat white cow head icon with two black spots and pink nose made of a few bold flat
  shapes on a sky blue panel, like a minimal sticker, easy to recognize, no fine details, no
  shading, the candy plump and three-dimensional with visible thickness`, seed 1152583910 →
  Илья «2 глаза сделай» → в промпт `simple flat symmetrical front-facing white cow head icon with two
  round black eyes, two ears and a pink nose` (без «symmetrical front-facing» модель рисует профиль с
  одним глазом). Потом Илья: «форма сломалась прямоугольника» → в начало промпта `a single soft fudge
  candy in a neat crisp rectangular cream-white paper wrapper, a clean rectangular box shape with
  straight parallel edges and sharp corners`, а значок `fully inside a sky blue rectangular panel`.
  Стоит seed 1152583923 (`out/korovka_rect_*`) → `Fog/Kitchen/candy_korovka/candy_korovka_1.png` (в
  игре и на сайте); `OLD_9` — с двумя глазами, но кривой формой. `OLD_5/6` — подробная корова целиком, `OLD_7/8` — голова с одним глазом (отвергнуты).
- Пакет молока 18.10, финал (Илья: «на пакет молока добавь тоже корову голову абстрактно синим»):
  промпт высокого пакета + `the front panel bright white and printed with a simple flat blue cow
  head icon made of a few bold flat shapes, like a minimal sticker`, seed 1152583913 →
  `milk_carton_4.png` (877 из 924 px — вровень с водой 879).
- Кофе молотый 18.10 (Илья: «переделай кофе молотый, тень убираем, 1x1 форма»): клетка 1×2 → 1×1
  (`Items.CoffeePack`), компактный пакет `a small compact brown foil stand-up bag of ground coffee,
  about as wide as it is tall, with a folded top and a cream label … simple flat coffee bean icon …,
  no drop shadows anywhere, no shadow under the item or on the label`, seed 1152583912 →
  `Fog/Kitchen/coffee_pack/coffee_pack_2.png`. Илья: «иконку по центру внутри этикетки» → в промпт
  `a simple flat coffee bean icon placed exactly in the center of the label with equal empty space
  around it on all sides`; стоит `out/coffee_ctr_1152583912`.
- Банан 18.10 (Илья: «банан переделай 1x1 и форму»): клетка 2×1 → 1×1 (`Items.Banana`), промпт
  `a single ripe yellow banana with a classic strongly curved crescent shape, smooth plump body with
  a short dark brown stem and dark tip, compact so it fits a square` на розовом фоне, seed 1152583912
  → `Fog/Kitchen/banana/banana_2.png`. Прежняя игровая — scratchpad c43ce975 `banana.game.orig.png`. Прежняя игровая — scratchpad c43ce975
  `coffee_pack.game.orig.png`.
  ⚠ Зёрна …909 и …911 оставили под конфетой зелёное пятно тени — вырезка его не берёт, такие
  варианты отбрасывать (смотреть вырезанное на ТЁМНОЙ подложке).
  ⚠ На сайте у старых иконок лежит миниатюра (13 КБ), которую эта сессия не читала: публикация
  отказывает — передавать путь в `overwrite_unread` (замену просил Илья).
- ⭐ **Этикетку модель ставит НИЖЕ центра пачки** (19.10, Илья: «этикетка не по центру — надо по
  центру пачки»): во всех вариантах кофе на 47–80 px из 1024, слова «exact middle» не помогают.
  Чиним на готовой картинке: находим этикетку по её цвету (кремовая, связная область вокруг
  точки на этикетке, `binary_closing` склеивает её через значок), вырезаем с контуром (+10 px),
  ставим центром в центр силуэта пачки, освободившееся место заливаем медианным цветом пачки
  из полосы под этикеткой. Так сделаны `coffee_pack_2` и `filter_pack_2` (скрипт — в истории
  сессии c43ce975; в scratchpad `coffee_fixed.png`, `filterpack_fixed.png`).
- ⭐ **Зелёный след тени под предметом** после вырезки (бывает часто): если в предмете нет
  зелёного — альфа 0 всем пикселям с `g > r+8 и g > b+8`, затем оставить только самую большую
  связную часть. Светлая крафт-бумага на пастельном фоне — вырезка выедает дыры в середине
  (раскрытый фильтр 19.10): брать вариант без дыр или рисовать силуэт сбоку закрытым.
- Кофейная серия 19.10, все 1×1. Правило: **форма и цвет — как у модели в игре** (Илья: «фильтр
  белый, и форма почти как треугольник», «коробка фильтров — надо как в игре форма»). Перед
  иконкой смотреть модель: `BlenderWork/<сцена>.py` (для кофе — `coffee_scene.py`: `filter_pack`
  — плоская коробка 22×36×8 см, картон BDA07A, белый веер на лицевой, красная полоса сверху;
  `coffee_filter` — лист-сектор с гофрами).
  - `coffee_pack_2` — пакет, этикетка поднята в центр пачки.
  - `coffee_filter_2` — белый сектор: острый низ, ОКРУГЛЫЙ верх (Илья: «верхняя часть — она округлая
    должна быть»), гофра по обеим сторонам. Форма фильтра (держать дословно, и для значка на коробке):
    `a fan-shaped circular sector like a slice of pie pointing down, the top edge is a smooth rounded
    convex arc, two straight sides meeting at a narrow bottom point`. Промпт: `a single flat white
    paper coffee filter seen straight from the side, <форма>, crimped zigzag seams along both slanted
    sides, solid opaque white paper with soft light grey shading, closed with no openings`, зелёный
    фон, seed 1152583912 (`out/filter_arc_*`). `OLD_2` — крафтовая трапеция, `OLD_3` — треугольник
    с прямым верхом. 19.10 Илья: «оч резкие по бокам квадратики» — зубцы гофры по контуру убрали: контур гладкий,
    гофра — полоской внутри: `the outline perfectly smooth, along both slanted sides a narrow pressed seam
    band drawn inside the shape as a thin parallel line with fine light grey ribbed texture` вместо `crimped
    zigzag seams`, seed 1152583912 (`out/filter_seam_*`) → `coffee_filter_2`; `OLD_4` — с зубцами. Потом Илья: «не таким вытянутым, чуть боком» — модель
    на «wide»/«tilted» рисует срезанный стаканчик, поэтому правка на картинке: обрезка по контуру, высота × 0,8,
    поворот −15° (`Image.rotate(-15, expand=True)`), `fit()`; `OLD_5` — прямой вытянутый.
  - `sausage_pack_1` 19.10 (Илья: «переделываем пачку сосисок, 1x1»; клетка 2×1 → 1×1 в `Items.SausagePack`):
    как в игре (`sausage_pack_scene.py`: белый лоток, прозрачная плёнка, красная этикетка поперёк), камера
    молока: `a compact chunky package of pink sausages, a short block-shaped pack about as wide as it is tall,
    two neat stacked rows of short plump pink sausages lying side by side, in a white plastic tray wrapped in
    clear plastic film with soft highlights, a bright red paper label band wrapped around the middle of the
    pack, the label printed with a simple flat white sausage icon …`, seed 1152583914 (`out/sausage_sq_*`);
    `OLD_sausage_pack_1` — широкая 2×1. Потом Илья: «этикетку на всю длину сбоку и сверху, красная лента, белым по центру сверху
    картинку» → этикетка вместо поперечной: `a wide bright red paper label strip running along the full length of
    the pack, parallel to the sausages, from end to end, covering the middle of the top and continuing down over
    the end side, a single simple flat white sausage icon printed exactly in the center of the red strip on the
    top`, seed 1152583914 (`out/sausage_band_*`) → `sausage_pack_1`; `OLD_2` — с поперечной этикеткой. ⚠️ Илья: «откати, мы потеряли форму внутри
    сосисок, на предыдущем варианте только с этикеткой надо было поработать» — новая генерация меняет весь
    предмет. Правка детали — ТОЛЬКО режимом правки по образцу (ниже, `edit.py`). Финал: `out/sausage_edit_3`
    (из `sausage_sq_1152583914`) → `sausage_pack_1`; `OLD_2` — поперечная узкая этикетка (исходник правки),
    `OLD_3` — новая генерация с лентой (отвергнута).
  - `filter_pack_2` — коробка как в игре, но НЕВЫСОКАЯ (Илья: «не такая длинная»; «форма рисунка — как
    сам фильтр»): `a closed flat cardboard box of coffee filters, tan brown cardboard, only slightly
    taller than wide, almost square front, a few centimeters thick, rounded beveled edges, a bright red
    horizontal band across the top of the front face, below it centered a large simple flat white icon
    of a paper coffee filter: <форма>` (без «bright red horizontal band across the top of the front
    face» полосу теряет). Финал 19.10 — вид спереди как у кофе и тонкая коробка (правило 1):
    `out/filterbox_thin_1152583911`, значок `shaped like a slice of pie pointing straight down, with a
    smooth rounded arc along the top and two straight sides meeting in a sharp pointed tip at the
    bottom, like a V with a rounded top` (иначе низ срезан). `OLD_2` — крафтовый пакет, `OLD_3` —
    высокая коробка с «ракушкой», `OLD_4` — коробка в три четверти, толстая, `OLD_5` — тонкая в лоб «как кофе» (отменено). Клетка 1×1. Кофе: `OLD_4` — пакет в лоб.
  Прежние игровые — scratchpad c43ce975 `*.game.orig.png`.
- История поля до 18.10. Предмет **целиком**, ничего не режется краем, и **заполняет клетку**: поле
  7 % с каждой стороны по длинной стороне (было 3 %; 05.10 после «ягоды слишком
  крупные получились» поставили 10 %, 06.10 Илья: «с отступом 7 % мы хотели»). Это
  делает не промпт, а `fit()` в `gen.py` после вырезки фона: обрезка по контуру
  (альфа > 8) → вписать в 1024×1024 с полем `MARGIN = 0.07` → по центру.
  `packs/items_to_game.py` при переносе прогоняет картинку через тот же `fit()`,
  поэтому старые выходы с 3 % в игру ложатся уже с 7 %. 06.10 все 34 иконки
  пайплайна в `Resources/Icons` пересобраны на 7 % из исходников: еда — из
  `out/it_*_cut.png` (заодно копия в `Fog`), одежда — из `Fog/Clothes/<id>/`
  (там поле 3 %, больше пикселей), `matches` и `cloth_strip_*` — на месте.
  Растягивать уже ужатую иконку — потеря резкости, брать исходник. В промпте поле вокруг
  просим («generous empty margin») — чтобы модель не резала вещь краем кадра.
- Вид **три четверти спереди-слева и чуть сверху (~30°)** — так смотрит
  камера игры на мир.
- Одежда на тело (верх, штаны) — **объёмная, как на невидимом манекене**, а
  не плоско разложенная. Обувь — парой. Сумки — стоя.
- Фраза в промпт (держать дословно):
  `the whole item fully visible and centered with generous empty margin around it, three-quarter view from the front-left and slightly from above (about 30 degrees)`
  + для одежды на тело `shown in 3D as if worn by an invisible mannequin`.

⚠️ **Память общая с редактором Unity (06.10, OOM).** ComfyUI при загрузке модели
берёт ~7 ГБ ОЗУ. 06.10 в 16:04 генерация шла, пока редактор «Таверны» грузил
уровень в play, — ядро убило Unity (`Out of memory: Killed process … (Unity)` в
`journalctl -k`), у всех сессий пропал мост. Перед `ig` при запущенном редакторе:
`free -g` — нужно ≥ 10 ГБ доступных; play не запускать, пока идёт генерация;
после — сразу `ig --stop`.

⚠️ **14.10: модель уровня в play (`llama-server` qwen3-4b, порт 11435, ~3,7 ГБ VRAM).** При ней на
карту влезает только ~0,3 ГБ модели, остальное уходит в RAM: картинка шла ~2 мин вместо 40 с, а
свободная RAM упала с 9 до 0 ГБ на третьем варианте (Unity выжил, серию оборвали `ig --stop`).
При живом `llama-server` — не больше 2 вариантов (`-n 2`) и `free -g` между ними.

## Команды

```
ig "промпт" [-o имя] [-n 3] [-W 1024 -H 1024] [-s 4] [--seed N]
ig --stop          # выгрузить ComfyUI: освобождает ~7 ГБ RAM и видеопамять
ig "…" --cut       # ещё и вырезать фон: рядом <имя>_<seed>_cut.png с прозрачностью
ig --cut-only a.png b.png   # только вырезать фон у готовых
ig --fit-only a_cut.png [--cell 1x2]  # только вписать вырезанную в холст клетки с полем 9,8 % (на месте)
```

- Результат — `$ROOT/out/<имя>_<seed>.png`. Повторить вариант — тот же `--seed`.
- `-n 3` — три варианта подряд (seed, seed+1, seed+2).
- `-s` — шаги; модель дистиллирована под 4, больше не нужно.
- Первая картинка после старта ~90 с (грузится модель), дальше 30–45 с на
  1024×1024.
- Вырезка фона (`cut()` в `gen.py`): фон = цвет по медиане рамки кадра;
  убирается заливкой от краёв (`BG_TOLERANCE` 36) + замкнутые дырки точно
  цвета фона (`HOLE_TOLERANCE` 10, от 400 px, только на светлом фоне) + то,
  что `rembg` (`isnet-general-use`, `.models`) считает фоном И что близко к
  цвету фона. Вещь — полностью непрозрачная, край размыт на 0,8 px.
  ⚠️ Голый `rembg` делал середину однотонных вещей ПОЛУПРОЗРАЧНОЙ (05.10:
  синяя толстовка на сером выглядела белёсой, зелёная — почти белой) —
  его альфу напрямую не брать. Иконки одежды в игре — PNG с прозрачностью, значит `--cut`
  для них обязателен.
- Паки — скрипты в `$ROOT/packs/` (первый — `clothes.sh`: вся одежда, по одной картинке с seed эталона; `to_fog.py` раскладывает в `Fog/Clothes/<id>/<id>.png`), гонять
  в фоне: `bash packs/clothes.sh`, в конце он сам делает `ig --stop`.
- Показать Илье — открыть папку: `xdg-open /media/ilya/T714/image-gen/out`.
  Картинки он смотрит сам; в чат PNG не слать (правило «Таверны»), результат
  описывать словами.

## ⚠️ Память — всегда `ig --stop` после серии

Пока сервер ComfyUI жив, он держит ~7 ГБ RAM (модель + текстовый энкодер;
было 10 ГБ — сервер стартует с `--disable-pinned-memory`). Вместе с редактором
Unity и соседями память и своп кончаются: 05.10 занято 30 из 31 ГБ, своп 8/8,
и системный OOM убил ComfyUI посреди картинки. Поэтому: сделал серию →
`ig --stop`. Сервер `ig` поднимает сам при следующем вызове; умер посреди
задания — `ig` выходит с ошибкой «ComfyUI умер…», а не ждёт вечно.

⚠️ **На видеокарте с 05.10 живёт Ollama** (qwen3:8b, ~5,5 ГБ VRAM, сервер
127.0.0.1:11434, модели в `/media/ilya/T714/llm`; завела сессия ilya-de).
Вместе с ней генерация упадёт по памяти. Перед серией: проверить
`curl -s 127.0.0.1:11434/api/ps` — если модель загружена, попросить её
хозяйку (SendMessage соседней сессии) выгрузить, а не выгружать самому.

Видеокарту делим с редактором Unity (он держит ~2–4 ГБ) — ComfyUI сам
выгружает часть модели в RAM (DynamicVRAM), это нормально.

## Куда класть: раскладка `/home/ilya/Documents/Fog` (с 05.10)

Верхние папки — темы (`Clothes`, `Equipment`, `Kitchen` — еда, `Dishes` —
посуда и кухонная техника, `Craft`, `Menu`, `System`, `Photos` — фото для
телефона, `Scripts` — слайды и звук катсцен, `YouTube`, `Ideas`, `Blender`).
Внутри темы — **папка на вещь** (`Clothes/jeans/`, `Kitchen/egg/`,
`Dishes/mug/`), в ней все её состояния и варианты. Этикетки продуктов —
`Kitchen/labels/`, рецепты — `Kitchen/recipes/`.

- Новые варианты: `<папка>/<id>_1.png`, `_2`, `_3` (вырезанные, `_cut`).
- Устаревшее: префикс `OLD_` в той же папке; Илья выбирает из новых, потом
  `OLD_*` удаляем («удалим потом старое»).
- Имя папки = id предмета в игре (`Items.cs`), где он есть.

## Стили «Таверны» и промпты

Эталоны лежат в `/home/ilya/Documents/Fog/<тема>/<вещь>/`. Перед генерацией
открыть эталон своей темы и держать его стиль (кроме камеры — она по
правилу 1). Каркас, проверенный 05.10:

| Тема | Эталон | Промпт-каркас |
|---|---|---|
| Предметы (Equipment) | `Equipment/phone/phone.png` — изометрия, гладкий вектор без контуров, мягкие тени, белый фон | `isometric illustration of <предмет>, clean smooth vector style, soft subtle shading, no outlines, centered, plain pure white background, game inventory icon` |
| Одежда (Clothes) | `Clothes/sneakers_grey/OLD_gray sneakers(man).png` — жирный чёрный контур, плоская заливка; фон прозрачный | `<вещь>[, shown in 3D as if worn by an invisible mannequin], <камера>, clean cartoon line art with bold black outlines and flat soft shading, game inventory icon, plain solid <dark charcoal \| light grey> background` + `--cut` |
| Рецепты (Kitchen) | `Kitchen/recipes/Recipe – Fried eggs…jpg` — мультяшно, тонкий тёмно-коричневый контур, плоский цвет с бликами | `cartoon illustration of <блюдо>, thin dark brown outlines, flat colors with soft highlights, three-quarter top view, plain solid light grey background` |

## ⭐ Значки эффектов и UI — контурные пиктограммы (Илья 06.10: «иконки так делаем»)

Значки в строках карточки, справочника, статусов («+40ед» еды, жажда, заряд, места в
инвентаре) — НЕ картинки предметов, а белая контурная линия на прозрачном фоне 256×256, в стиле
набора Lucide (ровная толстая линия, скруглённые концы, без заливки). Цветную плашку под значком
рисует сам UI. 06.10 так сделаны `effect-water` (капля), `effect-slots` (рюкзак),
`effect-charge` (молния).

⭐ **Внутри контура — ничего** (Илья 06.10: «убери по центру волнистую линию — вообще у иконок внутри не
рисуй ничего, проверь другие»): значок = только внешний силуэт, без волн, карманов, полосок и прочих
деталей внутри. В промпт добавлять `only the outer silhouette outline, nothing drawn inside the shape`,
а после выбора прогонять `packs/outline_only.py <png…>` — стирает все линии, не касающиеся внешнего
фона (заливка от края по прозрачному, связные компоненты линии; печатает «erased px»). Так 06.10
почищены `effect-water` (волна) и `effect-slots` (карман).

- 06.10 «Мокрый» (Илья: «замени иконку мокрый — перегенери»): 4 идеи × 2 (`fx_wet_{drops,shirt,hair,splash}`, seed 7301/7302), выбрана `shirt_7302` — футболка с каплями снизу (капли отдельно путаются с `effect-water`) → `Icons/effect-wet.png`; код: `PlayerExposure` (эффект «Мокрый») и дебаг `SkinBlockHeader` — `effect-wet` вместо `cloud-rain`.

1. Пак `packs/effect_icons.sh`: модель рисует ЧЁРНЫЙ контур на белом, по 4 идеи на значок × 2 зерна
   (`--seed 7301`, `-n 2`), без `--cut`. Каркас промпта (держать дословно):
   `<что>, simple flat outline icon, single thick black line of uniform width with rounded ends,
   minimal pictogram in the style of lucide icons, no fill, no shading, no gradient, no text,
   centered with generous empty margin around it, plain pure white background`.
2. `packs/effect_icons_to_fog.py`: альфа = темнота пикселя (линия → белая линия, края сглажены),
   обрезка по контуру, вписать в 256×256 с полем 6 %, раскладка
   `Fog/System/effects/<значок>/<идея>_<seed>.png`. Показать Илье папку, он выбирает.
3. В игру — `Assets/Game/Resources/Icons/effect-<значок>.png` + `.meta` с импортом как у
   `droplet.png` (Sprite, без мипов, свой guid). ⚠️ Имя ТОЛЬКО с префиксом `effect-`: в той же
   папке лежат картинки предметов по их id, и 05–06.10 иконка предмета «рюкзак» затёрла значок
   `backpack` — в строке «Места в инвентаре» стоял цветной рюкзак.
4. Код зовёт значок по имени (`new ItemEffect("effect-water", …)`, `WikiEffect.icon`, `StateBadge`).

Модель не считает: «сетка 3×3» вышла 3×4. Мелкая деталь внутри контура (молния в батарейке)
в карточке не читается — брать крупные простые формы.

Правила промпта:
- ⭐ Фон — `floating isolated with no ground shadow, plain solid pastel green
  background` для ВСЕГО, кроме зелёных вещей (им — `pastel pink`). Цвет фона
  обязан отсутствовать в вещи. Сверено 05.10 на одежде: на тёмно-угольном фоне
  вырезка съела тёмную внутренность кроссовок, на светло-сером — серые тени
  белой подошвы; без «no ground shadow» под рюкзаком, портфелем и тапками
  оставалась тень пола.
- Одежда на манекене — добавлять `hollow garment with no mannequin, no head,
  no body, no hands, no feet visible, empty hood and empty openings`: иначе
  в капюшоне серая голова манекена, из джинсов торчат ботинки.
- Одна вещь — одна картинка с зерном эталона `--seed 1152583909` (им снят
  `tshirt_red_2`): общий seed держит похожую композицию. Брак — другой seed.
- Логотипы: `plain unbranded …, no logos`.
  Шахматку «прозрачности» не просить: модель её рисует картинкой (так испорчен
  нынешний рецепт яичницы).
- Писать по-английски, предмет первым, стиль потом.
- Цвет и материал называть явно («grey mesh with white laces»).

## ⭐ Правка по образцу — `edit.py` (19.10)

Поменять ДЕТАЛЬ на готовой картинке (этикетку, значок, цвет), не трогая остальное — не новой генерацией,
а правкой: FLUX.2 klein + `ReferenceLatent` (узел ядра ComfyUI, `comfy_extras/nodes_edit_model.py`) —
исходник через `VAEEncode` вешается на positive и negative, латент пустой 1024², 4 шага.
```
cd /media/ilya/T714/image-gen; export TMPDIR=$PWD/.tmp HF_HOME=$PWD/.tmp/hf
.venv/bin/python -I edit.py out/<исходник>.png <имя> <seed> "Edit this image. Change only <что>. Keep everything else exactly the same: <перечислить>, the same camera angle, the same cartoon style with bold black outlines, the same plain pastel green background."
./ig --stop
```
Исходник — СЫРОЙ кадр с зелёным фоном (`out/<имя>_<seed>.png`, не `_cut`); выход — `out/<имя>_<seed>_cut.png`
(вырезка та же). 3 seed по ~45 с; первый 19.10 — этикетка сосисок, сосиски и лоток остались те же.
⚠️ Правка держит композицию исходника очень крепко: ЦВЕТ/ЗНАЧОК/ЭТИКЕТКУ меняет, а ЧИСЛО предметов и
геометрию — нет (19.10 «8 сосисок» и «лента до края верхней грани» — 8 попыток, без изменений). Такое —
новой генерацией с тем же seed и промптом, поменяв в промпте только нужное.
- 19.10 Илья: «сосисок 8 и красную ленточку до конца на верхней грани» → новая генерация `out/sausage8_gen_1152583914`
  (промпт `sausage_sq` + `eight … in two neat stacked layers of four` + `the band covers the top face fully from
  its front edge to its back edge`) → `Fog/Kitchen/sausage_pack/sausage_pack_2.png`, только на сайте (Илья:
  «пока иконки в канвасе на сайте, потом перенесём в игру»). Видно 6 торцов (3+3), не ровно 8. Илья: «лан, оставь 6». Дальше правкой (`edit.py`): лента до заднего
  бортика (`sausage_fix_3`), пятно на плёнке (`sausage_fix2_3`), значок на этикетке крупнее — `one plump gently
  curved sausage lying horizontally, with rounded ends and a small tied twist knot at each tip, a thin dark red
  outline and one short white highlight line, flat sticker style, filling about two thirds of the band width`
  (`sausage_icon_1`) → `sausage_pack_2`. ⚠️ Двойной лоток (лоток под лотком) правка НЕ убирает — 8 попыток. Потом Илья: «коровку на сосисках, где картинка» →
  значок — `simple flat white symmetrical front-facing cow head icon with two round eyes, two ears, two small horns
  and a wide muzzle, made of a few bold flat shapes with a thin dark red outline` (`sausage_cow_2`) → `sausage_pack_2`;
  `OLD_6` — со значком сосиски. Потом «более абстрактно и поверни боком, по направлению этикетки» → правкой
  силуэт без деталей (`sausage_cow2_1`); ПОВОРОТ модель не делает — значок «напечатан» на ленту в её перспективе
  скриптом `packs/label_affine.py <src> <dst> <ось X> <ось Y> <масштаб>` (стирает белый значок заливкой цвета
  ленты и кладёт его аффинно по осям ленты; оси снимать с краёв ленты на картинке; для сосисок
  `0.78,0.6 -0.94,0.34 1.0`) → `sausage_cowaff_1` → `sausage_pack_2`; `OLD_7` — корова анфас с деталями.
  Простой поворот головы анфас читается как заяц — только аффинно по плоскости. Илья: «не похоже» → «просто прямоугольник белый на
  красной этикетке сверху, с отступом»: значок стёрт заливкой цвета ленты (`out/sausage_noicon.png`), белый
  четырёхугольник нарисован по 4 углам верхней грани ленты (билинейно, поле 20 % по обеим осям, сглаживание ×4) →
  `sausage_rect_0` → `sausage_pack_2`; `OLD_8` — корова в перспективе.
  - `egg_carton_1` 19.10 (Илья: «пачку яиц переделать, 1x1»; в игре 2×1, серая коробка с крышкой, 10 яиц):
    `a short compact open grey cardboard egg carton, about as wide as it is deep, holding light brown chicken eggs
    in two neat rows, the lid hinged at the back and opened upright behind the eggs, the carton clearly shaded with
    a darker side so the edges are sharp` + камера молока, seed 1152583912 (`out/egg_sq_*`) — 4 яйца 2×2; только
    на сайте; `OLD_egg_carton_1` — широкая 2×1. Потом Илья: «6 штук», затем «яйца 1x2 и 8 яиц» → холст
    512×1024 (`-W 512 -H 1024`), вид сверху круто, коробка длинной стороной снизу вверх: `a long narrow open grey
    cardboard egg carton for eight eggs, holding exactly eight light brown chicken eggs in two neat rows of four
    eggs each, the carton seen from above at a steep angle with its long side running from the bottom of the
    picture to the top, … the lid hinged at the far end and opened upright` — из 8 seed ровно 8 яиц у двух,
    взят 1152583912 (`out/egg8_*`), `--fit-only --cell 1x2`. `Items.EggCarton` 2×1 → 1×2 — при переносе в игру;
    `OLD_egg_carton_2` — 1×1 с 4 яйцами. Илья: «плохо, изометрия не правильная» (вид сверху — не камера молока) →
    камера молока на холсте 512×1024: `a tall narrow open grey cardboard egg carton standing upright on its short end
    like a box on a shop shelf, tilted back slightly, its open front shows exactly eight light brown eggs in two
    columns of four eggs each sitting in the cups, the lid open and hanging to the side, the carton about two and a
    half times taller than wide` + `$CAM`, seed 1152583912 (`out/egg8a_*`) → `egg_carton_1`; `OLD_3` — вид сверху.
    Закрытая коробка торцом (`egg8b`) — вылитый пакет молока, не брать. Потом Илья: «2x1 делаем» (клетка как в игре, `Items.cs` не
    менять) → холст 1024×512: `a long low open grey cardboard egg carton lying flat, about two and a half times longer
    than deep, holding exactly eight light brown chicken eggs in two neat rows of four eggs each, the lid hinged at
    the back and opened upright behind the eggs` + `$CAM`; из 8 seed ровно 8 яиц у 914 и 919, взят 1152583914
    (`out/egg21_*`), `--fit-only --cell 2x1` → `egg_carton_1`; `OLD_4` — 1×2 стоймя. Потом «разверни в другую сторону» → зеркально
    (`ImageOps.mirror`, бок слева; `OLD_5` — до), затем «умести в 1x1, уменьшаем» → та же картинка `--fit-only --cell
    1x1`; `OLD_6` — 2×1. Итог: клетка 1×1, `Items.EggCarton` 2×1 → 1×1 — при переносе в игру. Потом «6 яиц и крупнее» →
    `a compact open grey cardboard egg carton for six eggs, holding exactly six light brown chicken eggs in two neat
    rows of three eggs each, the lid hinged at the back and opened upright behind the eggs` + `$CAM`, ровно 6 — у 5
    из 8 seed; взят 1152583916 (`out/egg6_*`, яйца крупные), отражён зеркально → `egg_carton_1`; `OLD_7` — 8 яиц. Илья: «крышка плохо вышла» → правкой (`edit.py` по сырому
    `egg6_1152583916.png`): `redraw it as a clean simple lid, a shallow grey cardboard tray shape exactly as wide as the
    carton, attached by a straight hinge along the whole back edge … no clips, no extra flaps`, взят `egg_lid_2`,
    отражён → `egg_carton_1`; `OLD_8` — со старой крышкой. Илья: «ширина крышки не такая как ширина основы» — правка
    геометрию крышки не чинит → новая генерация: `the lid is exactly the same width and the same length as the carton
    base, a mirror copy of the base outline, joined to the base along the whole back edge` (+ `six large … eggs`),
    seed 1152583916 (`out/egg6w_*`), отражён → `egg_carton_1`; `OLD_9` — крышка уже основания. ИТОГ 19.10: Илья «яйца делаем 2x1 — 8 штук» → вернули
    `OLD_egg_carton_6` (2×1, 8 яиц, отражённый) в `egg_carton_1`; клетка 2×1 как в игре (`Items.cs` не менять);
    `OLD_10` — 1×1 с 6 яйцами и крышкой по ширине. Потом «надо шире, а крышку уберём» → правка «remove the open
    lid completely» по `egg21_1152583914.png` (`egg21_nolid_3`), отражён, растянут по ширине ×1,25 (яйца ещё не плющатся),
    `--fit-only --cell 2x1` → 870 из 924 px; `OLD_11` — с крышкой. Запас без крышки —
    `egg_carton_2` (правка «remove the lid completely» сработала: УДАЛИТЬ отдельную деталь правка может).
  - `ketchup_1`, `oil_bottle_1` 19.10 (Илья: «бутылку кетчупа и масла переделываем, 1x2»), цвета по
    `ketchup_scene.py` / `oil_bottle_scene.py`, холст 512×1024 + `$CAM`, seed 1152583914 у обоих (пропорция 2,4 / 2,33 —
    ближе всех к стандарту 1×2; seed 912/913/915 дают 3,3–4,2, узкие). Кетчуп: `a tall slim dark tomato red glass
    ketchup bottle, three times taller than it is wide, … a small white screw cap, a thin green band around the neck,
    a cream paper label … simple flat red tomato icon with a green leaf top`; масло: `a tall slim clear plastic bottle
    of golden yellow sunflower oil … a small yellow screw cap, a cream paper label … simple flat yellow sunflower
    icon`. `OLD_*_1` — прежние в лоб с пустой этикеткой.
- ⭐ **Зелёная тень у вещи с зелёным** (19.10: стёрлись полоска на горлышке кетчупа и листик помидора) — НЕ общий
  фильтр «g > r+8», а `packs/clean_green_shadow.py <src> <dst>`: стирает только зелёные пятна, касающиеся
  прозрачного фона снаружи. Брать его всегда вместо общего фильтра. Флаги `--pink` (вещь на розовом фоне) и `--blue` (на голубом).
  - `vodka_1`, `water_soda_1` 19.10 («под новые правила»): как кетчуп, seed 1152583914, 512×1024; водка — прозрачная, красная
    крышка, белая этикетка с колоском; газировка — на РОЗОВОМ фоне (в ней зелёное), зелёная этикетка; Илья: «убери иконку
    воды, круг просто на этикетке» → капля стёрта заливкой цвета этикетки, белый круг нарисован (`OLD_water_soda_2` — с каплей).
- ⭐ **Серия одного предмета разных цветов/вкусов = ОДНА форма** (Илья 19.10, чипсы: «проверь чтобы все формы одинаковые были,
  только цвета и картинки менялись + пустые тоже»). Правка (`edit.py`) «смени цвет и значок» чуть меняет ширину пачки — не годится.
  Делать так (`packs/chips_recolor.py`): один эталон (закрытая `chips12b_1152583914` — коралловая с креветкой, голубой фон, 512×1024 +
  `$CAM`; пустая — правкой эталона «top seam torn off along a jagged ragged edge … silver foil inside … deflated», `chips_open_3`),
  остальные цвета — ПЕРЕКРАСКОЙ эталона (цвет пачки × яркость пикселя, цвета `chips_scene.py`: мятный, жёлтый), значок эталона
  стирается, новый значок вырезается из правки и ставится в центр с площадью как у старого; все 6 кадрируются ОДНОЙ общей рамкой
  и одним масштабом (без растяжки). Клетка чипсов 2×2 → 1×2 — `Items.Chips*` при переносе в игру. Потом Илья: «мясо не оч — сделай красным с белым» (значок
  мяса перекрашен: коричневое → красный, светлые прожилки → белые, ×1,5) и «закрытые сделай шире» (закрытый эталон без значка
  растянут по ширине ×1,3, значки ставятся ПОСЛЕ растяжки — не искажаются).
- Грибы 19.10 («улучши все грибы 1x1»): `seen from the front-left and slightly from above (about 30 degrees) so the top of the cap is
  visible`; боровик `mush_boletus_1152583914`, мухомор `mush_agaric_1152583914`, опята `mush_honey_1152583913`, бледная поганка —
  оливковая шляпка на РОЗОВОМ фоне `mush_toad_1152583915`. ⚠️ Белые ножки вырезка проедает тёмными дырами →
  `packs/fill_holes.py <png>` (закрывает внутренние дыры до 1500 px цветом кольца; крупнее — настоящие просветы, как между
  ножками опят, не трогает). `OLD_mushroom_*_1` — прежние в лоб.

## Что модель делает плохо

- **Считать.** «Exactly two fried eggs» — дважды вышло одно яйцо. Количество
  и точную раскладку сцены не обещать; такое — Leonardo или правка по образцу
  (ещё не поставлена, см. «Дальше»).
- **Логотипы.** На обуви и технике рисует мелкие псевдологотипы — смотреть и
  перегенерировать другим seed.
- Шнурки бантом и мелкие детали проще, чем в эталонах Leonardo.

## Устройство

- `ComfyUI/` — сервер (клон github comfyanonymous/ComfyUI), узел
  `custom_nodes/ComfyUI-GGUF` (city96).
- Модели (`ComfyUI/models/`): `unet/flux-2-klein-4b-Q8_0.gguf` (4,3 ГБ,
  unsloth/FLUX.2-klein-4B-GGUF), `text_encoders/Qwen3-4B-Q8_0.gguf` (4,3 ГБ,
  unsloth/Qwen3-4B-GGUF), `vae/flux2-vae.safetensors` (0,3 ГБ, Comfy-Org).
- `gen.py` — API-клиент: граф UnetLoaderGGUF → CLIPLoaderGGUF(type flux2) →
  EmptyFlux2LatentImage + Flux2Scheduler → CFGGuider(cfg 1) →
  SamplerCustomAdvanced(euler) → VAEDecode → SaveImage. Сервер на
  127.0.0.1:8188, лог `.tmp/comfy.log`, сырые кадры `.tmp/comfy-out`.
- `ig` — обёртка: TMPDIR и HF_HOME внутри корня, python из `.venv`.
- Сервер стартует, только если порт 8188 свободен (05.10 из-за долгого ответа
  под нехваткой памяти поднимался второй экземпляр — исправлено проверкой
  порта, таймауты 120 с, опрос истории переживает таймаут).

### exFAT — грабли установки

- Симлинков нет: `uv venv` и `python -m venv` падают. Рабочий рецепт:
  `mkdir -p .venv/lib64 && python3 -m venv --copies .venv`.
- Кэш uv на exFAT ломается (rename/hardlink) — ставить через
  `.venv/bin/python -m pip install --no-cache-dir`, TMPDIR в `.tmp`.
- torch: `--index-url https://download.pytorch.org/whl/cu128` (драйвер 580,
  CUDA 13 — совместимо), стоит 2.11.0+cu128.

## Удалить

`ig --stop; rm -rf /media/ilya/T714/image-gen; rm ~/.local/bin/ig` (~17 ГБ)
и этот скил.

## Дальше (не сделано, предложено 05.10)

- Правка по образцу: тот же klein в режиме edit (шаблон ComfyUI «Image Edit
  (Flux.2 Klein 4B)», узлы ReferenceLatent + VAEEncode) — «эта картинка, только
  без шахматки / два яйца».
- Вырезка фона в PNG с прозрачностью (rembg или BiRefNet) для иконок.
- Свой стиль: LoRA на 20–40 картинках из `Fog` (ostris/ai-toolkit).

3D-модель по готовой картинке (`*_cut.png` → `.glb`) — отдельный скил **img3d**
(TRELLIS.2, с 06.10); звуки — скил **sfx-gen**.
