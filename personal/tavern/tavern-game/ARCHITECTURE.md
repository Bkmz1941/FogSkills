# Карта кодовой базы (на 2026-10-11, ~142k строк C#; раздел «Глобальные модули» — главный)

Читать, когда нужно понять **где что лежит** и **какой общий примитив уже
есть**, чтобы не написать восьмую копию того же самого. Правила домена — в
BUILD/VIEW/CHARACTER/UI, грабли — в PITFALLS, история — в DESIGN_LOG.

## Что где в этом файле

| Раздел | О чём |
|---|---|
| **⭐ Глобальные модули** | четыре слоя, 14 подмодулей Мира, правила направления, очередь выделения |
| **Где что лежит** | папки и модули |
| **Общие примитивы** | луч, сетка, габариты, силуэт — брать, не писать заново |
| **Разложение больших классов** | партиалы GridCursor, InteractiveObject, HudUI |
| **Пайплайн постановки объекта** | единственный путь `ComputeObjectPose` |
| **Правила наведения** | `Interactor` |
| **Тесты** | EditMode-набор и что он ловит |
| **Характеризующий замер** | как править опасное место безопасно |
| **Ритм работы с редактором** | play, компиляция, MCP |
| **Конструктор** | что добавляется данными, что кодом |
| **Производительность, Замеры и бюджеты, Замеры кадра** | цифры кухни, бюджеты, кадр в play |
| **Сеть целостности контента** | тесты каталога, узлов, ссылок |
| **Сохранение состояния** | что уже едет в сейв |

## ⭐ ГЛОБАЛЬНЫЕ МОДУЛИ — карта на 11.10 (ilya-63; Илья: «разобраться и написать список глобальных модулей, и рефакторить»)

Снято скриптом по типам (142,5k строк C#, 509 файлов, 14 сборок): для каждого
файла — какие типы каких сборок он трогает; внутри `Cozy.Grid` — то же по
подмодулям. Четыре слоя, стрелки только ВНИЗ. Сборку и папку не переименовываем
(на имена завязаны пробы, `DebugTune`, журналы); честность достигается тем, что
каждый класс лежит в своём модуле, а не тем, что модуль красиво назван.

### Слой 0 — Основа (видят все, сама не знает никого)

| Модуль | Сборка | Что внутри | Строк |
|---|---|---|---|
| Локализация | `Cozy.Loc` | `Loc.T/F`, `LocText`, `en.json` | 0,2k |
| Вид и реестры | `Cozy.View` | `ViewState` (режим, этаж, комната, единственный писатель `Time.timeScale`), `SceneSingleton`/`SceneFind`, `ScenePostFx`, `PeepLensFx`, `LookFade`; с 11.10 — `DebugActions` (кнопки F1 без обратной ссылки на UI) и `GameEvents` (журнал событий, часы — хуком из `GameClock`) | 0,6k |

### Слой 1 — Мир: `Cozy.Grid`, 72k строк, 249 файлов — ОДИН модуль из 14 подмодулей

Почему один, а не четырнадцать сборок: `GridCursor` (36 партиалов), `InteractiveObject`
(10) и `LevelIO` сшивают стройку, объекты, постановку и сейв в один узел, а partial
class по сборкам не делится. Граф 11.10 по подмодулям — ВСЕ четырнадцать в одной
компоненте сильной связности. Резать на сборки можно только подмодуль целиком, через
швы-хуки (приём `Cozy.Cooking`: верх знает Grid, Grid верх — нет, навеска через
`InteractiveObject.FeatureFactories`), с живой пробой до и после. Очередь — ниже.
Пока же подмодуль = папка внутри `Assets/Modules/Grid` (раскладка 11.10) и раздел
ответственности в этой таблице.

| Подмодуль (папка) | Ядро | Строк | Кто снаружи Grid его трогает |
|---|---|---|---|
| `Core/` — примитивы | `RayPick`, `GridSnap`, `GridManager`, `GridBlock`, `PartMath`, `PlaceMath`, `Ease`, `ShaderLib`, `OwnedAssets`, `PlayerRef`, `UiPointer`, `Targeting`, `Categories`, `DisposeKinds`, `Weather` (конфиг стихий и часы `Weather.Hour/Clock`), `CellWalls`, `FurnitureDims`, `GcProbe` | 1,4k | все |
| `Build/` — сетка и стройка | `GridCursor` (ядро + стройка: Blocks, Paint*, Dig, Ground, Terrain, Stairs, Roof, WallRuns, DoorsWindows, Plinth, Zones, Markers, Water, GrassBrush, Textures, Snap, Commit), `GridMesh*`, `GridView`, `DoorPiece*`, `DoorKit`, `WindowPiece`, `WindowLook`, `StairPiece`, `RoofPiece`/`RoofMesh`, `PlinthView`/`PlinthPiece`, `PlankRelief`/`PlankSkin`/`PlankStamp`, `TerrainHeights`, `KitMaterials`, `KenneyStyle`, `PaintLibrary`, `GroundTextureLibrary`, `JambPaint`, `WallCorner`, `BevelView`, `CladCuts`, `Overhang`, `AtticHatch`, `ElevatorCab`/`ElevatorView`, `DebugGrid`, `DugRoofView`, `PlacedFloorView`, `FlowerBedView`, `BugBrush`, `EdgeGuard`, `Peephole`, `FurniturePiece`, `SeatFaceView` | 17k | UI (стройка), Character (EdgeGuard, лазание), Monsters (двери, окна) |
| `Objects/` — объекты мира | `InteractiveObject.*`, `ObjectDef`, `ObjectAttributes`, `ObjectSheet`, `ObjectGroup`, `ObjectFeature` + `Features/*`, `FurnitureCatalog.*`, `ProceduralModels.*`, `FurnitureModel`, `ContainerSlot`, `MountStretch`, `WorldLabel`, `FridgeLight`, `LampDaylight`, `CurtainDrape`, `PlaidCloth`, `WardrobePile` | 19,5k | все |
| `Place/` — постановка, перенос, наведение | `GridCursor.Objects/ObjectSnap/Support/PlaceQueries/PlaceGhost/ObjectMove/Transfer/Layout/Dish/Liquid/Containers/Seats/Place/Decor/Selection`, `Interactor`, `FallToSupport`, `GhostBox`, `BuildQuery`, `InteractHighlight`, `PartOutlines` | 9,3k | UI, Character, Monsters |
| `View/` — видимость | `ViewSensor` (+ `WorldTick`, `FarRadius`), `WallCutaway`, `FloorPieceView`, `PieceViewTicker`, `HiddenRooms`, `SeeThroughView`, `XRayView`, `CrownWindow`, `MirrorReflection`, `WallMountedCut`, `LookModeBase`, `CarryWindow`, `OpenSwapView` | 3,2k | Character (камера), Effects, UI |
| `Save/` — сейв | `LevelIO`, `GridCursor.Levels` | 1,7k | Core (HomeSync), UI, Story, Monsters (`AiRules/AiBrief`) |
| `Inventory/` | `Items`, `ItemDef`, `GridInventory`, `CraftBook`, `PowerCells`, `ItemEffects` | 1,2k | Character (Equipment), UI, Story |
| `Liquids/` | `LiquidVolume`/`LiquidState`/`LiquidSurface`, `WaterSource` (+ `Puddle`), `WaterBody`, `DrainVortex`, `BathSurface` | 3k | Cooking, UI |
| `Fire/` | `FireView` (+ `Burnable`), `FireVolume.*`, `FireArea`, `Ignition`, `CandleFire`, `TorchFire`, `FireplaceFire`, `SparkBurst`, `LanternSway` | 2,9k | Effects (ожог), Monsters (камин) |
| `Weather/` — стихии | `FogView`/`FogVolume.*`/`FogAnim`/`FogArea`, `WindGusts` (+ `TreeWind`, `ViewCull`)/`WindView`, `RainDrops`, `CellVolumeView`, `ZoneArea` | 3,3k | Core (GameClock), Effects (туман), Cozy.Weather |
| `Power/` — электросеть | `PowerLines`, `PowerGrid`, `PowerLed`, `PowerTimer`, `LightZones`, `PowerFeature`, `WallSwitchFeature`, `PhoneCharger`, `ElevatorPanelHost`, `AcIndicator` | 2,1k | Effects, Monsters (выключатели) |
| `Birds/` — живность: тела птиц и бабочки | `CrowFlight.*`, `CrowIdle`, `CrowPerch`, `ButterflyFlight` — полёт, насест, покой, голос; одни классы на ворону, сову и зарянку. ⭐ Илья 11.10: «монстры сейчас это ворона и сектант, сова и зарянка, бабочка — это не монстры»: враждебность вороны живёт в Combat (`CrowAttack`) и Monsters (красные глаза), тело — здесь, как у совы | 3,2k | Combat, Monsters, UI |
| `Zones/` | `ZonePiece`, `ZoneEvent`, `SpawnPoint`, `MarkerFeature` | 1,3k | Story, Monsters, Combat, UI |
| `Kitchen/` — физика кухни | `SinkPile`, `CookArrange`, `Sauced`, `Greased`, `Soiling`, `BoilEffect`, `SizzleEffect`, `TemperatureSim`/`TemperatureField`, `ChamberTempLabel` | 2,7k | Cooking |

### Слой 2 — Игровые модули (знают Мир и Основу; Мир про них не знает)

| Модуль | Сборка | Что внутри | Строк | Знает ещё |
|---|---|---|---|---|
| Игрок | `Cozy.Character` | `PlayerMovement`, `CameraFollow`/`CameraOrbit`, `CharacterAvatar`/`Stats`/`Profile` (+ `People`), `PlayerEffects`/`PlayerBuffs`/`PlayerTarget`, `VisionArea`/`VisionCircle`, `DarknessVeil`, `FlashlightRig*`/`FlashlightDust`, `AimFocus`, `Equipment`, `WardrobeVisuals`, `PhoneState`, `ColorSplit`, `ScreenLook`, `PhoneState`, `People` (люди уровня — здесь, потому что их читает `PhoneState`) | 8k | — |
| Существа: тела и чувства | `Cozy.Creatures` | `Creature` (ядро: этаж, тело-манекен), `MonsterNav`, `CreatureSenses` (зрение и слух), `Noise`/`SenseProfile`/`CrowSense`/`SectantSenses` (профили чувств, шум игрока), `NpcDummy`/`Sectant`/`SectantAnimation`/`SectantTwitch` (человек на модели героя), `HeadIcon` (значок над головой: думает / вопрос / тревога). Лежит НИЖЕ Combat (с 11.10; до того всё это жило в `Cozy.Character`, потому что стычки читали чувства). Животные (сова, зарянка, бабочка, тело вороны) — `Grid/Birds/` | 1k | Character |
| ИИ-жизнь | `Cozy.Life` | `CreaturePlan.*` (мозг: планы, путь, чувства, действия), `LifeRules.*` (правила уровня), `AiConsole` + `PlanStep` (пульт модели), `MonsterManager`, `ShadowMonster`/`ShadowZone` (Тень), `SectantPoint`, `CrowZoneSpawn` (спавн всех существ, имя вороньё — на него завязана `ai_plan_probe`). Лежит НАД Combat. Илья 11.10: «монстры сейчас это ворона и сектант», «ворона животное, а сектант человек» — враждебность свойство существа, не модуль | 4,4k | Creatures, Character, Combat, Effects, Net |
| Стычки | `Cozy.Combat` | `Encounter.*` (машина сцен, показ, возврат), `EncounterGraph`/`CrowEncounter`, `CrowAttack`, `CrowContactArea`, `SectantEncounter`, `RangedAttack`, `EncounterData` | 3,6k | Character |
| Статусы игрока | `Cozy.Effects` | `PlayerExposure` (+ `DoseTrack`), `FogTrap`, `StunStars`, `BathEffect`, `VoicesEffect` (с 11.10 только про игрока: `HeadIcon` ушёл к существам) | 2,1k | Character |
| Готовка | `Cozy.Cooking` | `CookBook`, `CookProgress`, `Nutrition`, `CoffeeBrewer`, `DishRule`/`DishFeature`, `EatFeature`/`EatProductFeature`/`DrinkFeature`, `CookingModule` | 1,4k | Character |
| Директор погоды | `Cozy.Weather` | `WeatherDirector` — 36 строк: смена ветра по часам; сами стихии — Мир/`Weather/` | 0,04k | — |
| Сюжет | `Cozy.Story` | `QuestBook`/`QuestRun`/`QuestDirector`, `StoryEvent`/`StoryEventBook`/`StoryEventDirector`, `ZoneEventRunner` | 1,1k | Character, Cooking (факты «съел/выпил») |

### Слой 3 — Приложение

| Модуль | Сборка | Что внутри | Строк | Знает |
|---|---|---|---|---|
| Сеть | `Tavern.Net` | `AuthClient`/`AuthSession`, `HomeClient`, `TemplateClient`, `SaveEndpoint`; с 11.10 — `LlmBridge`/`LlmHost` (сервер модели, персонажи по СМС) и `TelegramBridge` | 0,9k | Grid, Character |
| Директор игры | `Tavern.Core` | `GameClock` (сутки, солнце, луна, гроза, тик погоды), `GameMode`, `HomeSync`, `CutsceneStage`, `FrameRateConfig`, `FullscreenToggle` | 0,5k | всё ниже + Net |
| UI | `Tavern.UI` | `HudUI` (44 партиала), экраны `*ScreenUI`, F1-дебаг + `DebugTune`, `PhoneUI` (10) + `CameraUI`, `UiFactory`/`UiTheme`/`UiSkin`/Kit, `SpeechBubbles`, `EventLogUI`, `MainMenuUI`; с 11.10 — `DeathScreenUI` | 42k | всё |
| Тесты | `Tavern.Tests.EditMode` | 28 файлов, ~190 тестов | 4,4k | всё |

Удалено 11.10: `Tavern.Data` — пустая сборка (ни одного .cs), на неё ссылались Core, UI и тесты.

### Правила направления

1. **Основа ← Мир ← Игровые модули ← Приложение.** Игровой модуль НЕ знает `Tavern.Core`
   и `Tavern.UI`. До 11.10 это нарушал `Cozy.Creatures` (звал `AiConsole`, `GameEvents`,
   `SpeechBubbles`, `DebugActions`, держал `DeathScreenUI`) — закрыто шагом `monsters-flip`:
   `AiConsole` переехал в Monsters, `DeathScreenUI` в UI, `GameEvents`/`DebugActions` в View,
   `LlmBridge`/`TelegramBridge` в Net; UI теперь ссылается на Monsters, а не наоборот.
2. **Между игровыми модулями** разрешено только: все → Character; Combat → Creatures; Life →
   Creatures, Combat, Effects; Story → Cooking. Новая стрелка между игровыми модулями — запись в `DESIGN_LOG.md`.
3. **Связь снизу вверх — только хуком или событием.** Хук = статический делегат в нижнем
   модуле, присваивание в `[RuntimeInitializeOnLoadMethod]` верхнего (`BeforeSceneLoad`, если
   нижний может позвать его при загрузке сцены). Образцы: `PickupFeature.GiveToPlayer`,
   `PlayerEffects.Sources`, `LevelIO.CollectPlayer`, `GameEvents.Clock`, `MonsterManager.Attach`,
   `CreaturePlan.Bubble`, `LlmBridge.Deliver`.
4. **Мир не режется по счётчику строк.** Подмодуль выходит в свою сборку целиком, через швы,
   с живой пробой; очередь по числу швов (файлов снаружи подмодуля, которые его трогают, замер
   11.10): `Birds/` 9 → НЕ в `Cozy.Creatures` (сова и зарянка не монстры, Илья 11.10), а в свою
   сборку живности, если вообще выносить (`InteractiveObject.Build` навеска, `LevelIO` насест,
   `GridCursor.ObjectMove/Objects` перенос, `ViewSensor` тикер, `CrownWindow`, `FurnitureCatalog.Props`,
   `ZonePiece`); `Kitchen/` 16 → в `Cozy.Cooking`; `Fire/` 19; `Zones/` 19; `Weather/` 20 → в
   `Cozy.Weather`; `Liquids/` 25; `Inventory/` 26; `Power/` 30. Защита — `COVERAGE.md` по области.
5. **Папка = подмодуль.** В Grid и UI файл лежит в папке своего подмодуля; новый файл заводится
   в папке, а не в корне модуля. Партиалы одного класса — в одной папке (поэтому все 37 партиалов
   `GridCursor` — в `Grid/Cursor/`, а не по подмодулям стройки/постановки/сейва). Папки UI:
   `Hud/` (HUD и его панели, F1-дебаг — партиалы `HudUI`), `Screens/` (экраны), `Phone/`, `Kit/`
   (фабрика, тема, скин, мелкие поведения), `System/` (`DebugTune`, `SceneLoader`). Откат
   переезда 11.10 — `.git/night/grid_moves_undo.sh`, `.git/night/ui_moves_undo.sh`.
6. **Имена сборок и namespace не трогаем**: на `Cozy.Grid.X`, `Tavern.UI.HudUI` завязаны
   88 проб, `execute_code` в журналах и ключи `DebugTune` (`HolderKey` = `Type.Name`, поэтому
   переезд типа в другую сборку ключи не меняет).

### Схема сборок (после 11.10)

```
Cozy.Loc   Cozy.View                                  ← Основа
    ▲         ▲
    └────┬────┘
      Cozy.Grid (Мир: Core/Build/Objects/Place/View/Save/Inventory/Liquids/Fire/Weather/Power/Birds/Zones/Kitchen)
         ▲
   ┌─────┼──────────┬──────────┬───────────┬───────────┬──────────┐
Character  Cooking   Weather    Effects     Combat      Story     ← Игровые модули
   ▲         ▲                    ▲           ▲           ▲
   │  Creatures (тела) ◄── Combat ◄── Life (разум) ◄─────┘           │
            ▲                                             │
          Tavern.Net ──► Grid, Character                  │
            ▲                                             │
          Tavern.Core ──► Grid, Character, View, Weather, Effects, Net
            ▲                                             │
          Tavern.UI ──► всё, включая Creatures и Story ◄───┘       ← Приложение
```

Стрелка = «ссылается на». Циклов нет и заводить нельзя; `offline_build.py` падает на цикле
asmdef. Проверка карты — `depgraph.py asm` (скрипт в журнале 11.10).

## Где что лежит

| Домен | Папка / ключевые типы |
|---|---|
| Сетка, стройка, курсор | `Modules/Grid/Cursor/GridCursor.*` (37 партиалов — стройка, постановка, перенос, сейв), `Grid/Core/GridManager`, `GridSnap`, `Grid/Place/BuildQuery`; куски стен, дверей, лестниц, крыш, плинтуса, рельефа — `Grid/Build/` |
| Двери | `Modules/Grid/Build/DoorPiece.cs` 271 (состояние, звук, проходимость), `DoorPiece.Parts.cs` 93 (осмотр, замок, глазок), `DoorPiece.Build.cs` 191 (проём, навеска), `DoorPiece.Leaves.cs` 268 (створки по стилям, ручки) |
| Объекты мира | `Modules/Grid/Objects/InteractiveObject.*` (10 партиалов: ядро 210, Build 254, Model 290, Size 160, Slots 123, Parts 237 «клики и подсветка частей», MovingParts 169 «створки, тряска, нажатия», Switches 178, Puzzle 62, Power 68, Temperature 185), `ObjectDef`, `FurnitureCatalog.*`, фичи — `Grid/Objects/Features/` |
| Двери/окна/лестницы | `DoorPiece.*`, `WindowPiece`, `StairPiece` |
| Видимость | `Grid/View/ViewSensor`, `WallCutaway`, `FloorPieceView`, `HiddenRooms`, `CrownWindow`; состояние — `Modules/View/ViewState` |
| Персонаж и камера | `Modules/Character/PlayerMovement`, `CameraFollow`, `AimFocus`, `VisionArea` |
| Готовка | `Modules/Cooking/CookBook` (данные), `CookProgress`, `CookingModule`; механика и чек-лист расширения — скил tavern-cooking, «МЕХАНИКА ПЕРЕДАЧИ И ГОТОВКИ» |
| Постановка объекта | `GridCursor.Objects` (пайплайн позы), `GridCursor.ObjectSnap` (магниты и прижимы), `GridCursor.Support` (опора, слоты, пересечения), `GridCursor.PlaceQueries` (лучи к миру), `GridCursor.PlaceGhost` (призрак), `PlaceMath` (чистая арифметика) |
| Передача продуктов | `GridCursor.Transfer` (TransferOffer: Pour/Serve/Put), `GridCursor.Layout` (раскладки и призраки), `GridCursor.ObjectMove` (перенос в руках), `HudUI.ActionLabel` (подпись) |
| Вода | `Grid/Liquids/LiquidVolume`, `WaterSource`, `GridCursor.Liquid` |
| Зеркало | `MirrorReflection` (камера-двойник, матрица отражения, косая проекция; двойник включён только пока стекло в кадре главной — `GlassInView`, P573), `MirrorGlass.shader` |
| Сейв/лоад | `Grid/Save/LevelIO`, `GridCursor.Levels` |
| UI | с 11.10 пять папок: `Game/UI/Hud/` (`HudUI.*` 44 партиала; интерактив — Interact «поток выбора/ховера», InteractCard «содержимое карточки», InteractBadges «бейджи»; плюс `PlayerStatHud`, `TimeBarHud`, `EncounterBarUI`, `EventLogUI`, `SpeechBubbles`, `QuickChatUI`), `Game/UI/Screens/` (экраны `*ScreenUI`, инвентарь, справочник, меню, слайды, `DeathScreenUI`), `Game/UI/Phone/` (`PhoneUI.*`, `CameraUI`), `Game/UI/Kit/` (`UiFactory.*`, `UiTheme`, `UiSkin`, спрайты, курсоры, мелкие поведения), `Game/UI/System/` (`DebugTune`, `SceneLoader`) |
| Тесты | `Assets/Tests/EditMode` (сборка `Tavern.Tests.EditMode`); белые списки `SourceRulesTests` — по новым путям |
| Огонь, стихии, электросеть, птицы, зоны, кухня, инвентарь | `Grid/Fire/`, `Grid/Weather/`, `Grid/Power/`, `Grid/Birds/`, `Grid/Zones/`, `Grid/Kitchen/`, `Grid/Inventory/`; шейдеры — `Grid/Shaders/` |

### ⚠️ Классы, которые живут не в своём по имени файле

Мелкие данные рядом со своим хозяином — это норма (`ObjectPart`, `TempSource`,
`Recipe` и ещё три десятка). А вот эти — самостоятельные системы, и искать их
по имени файла бесполезно (13.09: `grep Burnable.cs` — «нет такого файла»):

| Класс | Живёт в | Что это |
|---|---|---|
| `Burnable` | `Grid/Fire/FireView.cs` | горение объекта: состояние, обугливание, пламя |
| `TreeWind` | `Grid/Weather/WindGusts.cs` | ветер отдельного растения: материалы, глобали, аналитический изгиб ствола |
| `ViewCull` | `Grid/Weather/WindGusts.cs` | «в кадре ли габарит» — фрустум раз в кадр |
| `WorldTick` | `Grid/View/ViewSensor.cs` | центральный тикер мира |
| `FarRadius` | `Grid/View/ViewSensor.cs` | радиус рендера и сон дальних |
| `PlayerPosture` | `Grid/Objects/Features/PostureFeature.cs` | единое состояние «объект держит игрока» |
| `SeeThroughWindow` | `Grid/View/SeeThroughView.cs` | просвет окна в стене |
| `PlayerXRay` | `Grid/View/XRayView.cs` | силуэт игрока за преградой |
| `Puddle` | `Grid/Liquids/WaterSource.cs` | лужа |

Заводить файл под класс — вопрос к Илье (правило 2 скила: новых файлов без
просьбы не создаём), поэтому пока это указатель, а не план переноса.

## ⭐ Общие примитивы — брать, а не писать заново

| Нужно | Готовое | Где |
|---|---|---|
| Ближайшая цель по лучу | `RayPick.Sorted/Down` — хиты от ближнего к дальнему, буфер свой у каждого вызывающего; первый подошедший = ответ | `Grid/Core/RayPick.cs` |
| Отсечь игрока/монстра в луче | `RayPick.IsPlayer(collider)` | там же |
| ⭐ Что это за попадание луча (05.10) | `RayPick.Classify(collider)` → `Player / Hidden / Unpickable / PassThrough / Pickable`: игрок и тела, голый триггер, невидимое (вью-гейт `FloorPieceView` вверх по иерархии, рендерер погашен или `ShadowsOnly`, у блока — видимая отделка), `noPick`, `passThrough`. Политика режима — у вызывающего: стройка берёт `PassThrough`/`Unpickable` запасной целью, игра пропускает всегда. Флаги `Def.noPick`/`Def.passThrough` в обход него не читаем (сторож `SourceRulesTests`) | `Grid/Core/RayPick.cs` |
| Видно ли попадание | `RayPick.Visible(collider)` | там же |
| ⭐ Этаж точки и «на этом ли этаже» (05.10) | `GridManager.FloorOf(p, cs)` = `LevelY(AboveRelief(p))`, `GridManager.OnFloor(p, floorY, cs)` — полоса `[пол − 0,5; следующий пол)` над рельефом; допуск у пола один — `GridManager.FloorSlack` 0,12. Полосу и сдвиги вручную не пишем (сторож `SourceRulesTests`) | `Grid/Core/GridManager.cs` |
| Луч камеры сквозь курсор | `GridCursor.CursorRay(cam, mouse)`; методы, которым нужен только луч, принимают ЛУЧ | `GridCursor.cs` |
| Мир → клетка, привязка к оси/кромке | `GridSnap.Cell/Axis/Edge`; `GridManager.WorldToCell` зовёт их же. ⭐ 05.10: формула одна — `ViewState.CellIndex` (сборка View, ниже Grid: её зовут и `GridSnap`, и `ViewState.CellAt/InMyRoom/InAccessible`, дождь, сетка дебага); на границе клетки — вверх; `Round` от начала сетки не пишем (сторож) | `Grid/Core/GridSnap.cs`, `View/ViewState.cs` |
| Растение, стоящее дерево, дерево вообще | `FurnitureCatalog.IsVegetation/IsStandingTree/IsTreeLike` — префикс `veg_` вручную не пишем (сторож) | `Grid/Objects/FurnitureCatalog.Props.cs` |
| Габариты набора рендереров | `FurnitureModel.Combined` (мир), `InteractiveObject.LocalBoundsIn` (в осях узла) | |
| Рендереры неподвижного тела (якорь карточки осмотра) | `InteractHighlight.StaticBody(корень, подвижные)` | `Grid/Place/InteractHighlight.cs` |
| «Вложенный выигрывает у своего хозяина» | `InteractiveObject.NestedBeatsHost(вложенный, хозяин)` | `InteractiveObject.cs` |
| Откуда видно содержимое | `Interactor.ThroughOpening`: сквозь деталь хозяина (`IsPart`: крышка, дверца) — нет; мебель со `slotNodes` — через проём с любого ракурса; посуда — только сверху в горловину |
| То же НА ЛЮБУЮ ГЛУБИНУ (яичница в сковороде на плите) | `InteractiveObject.NestedInside(вложенный, хозяин)` — цепочка `Container`; на нём же стоят разбор луча и «внутри осматриваемого» | `InteractiveObject.cs` |
| Порог «жидкости меньше капли» | `LiquidVolume.Drop` | `Grid/Liquids/LiquidVolume.cs` |
| Стена/стеноподобное под лучом | `BuildQuery.WallLike/WallLikeAt/CubeBlock` | `Grid/Place/BuildQuery.cs` |
| Ссылка на игрока | `PlayerRef` | `Grid/Core/PlayerRef.cs` |
| Поза игрока на объекте (спрятаться, сесть, лечь) | `PlayerPosture` — ОДНО состояние «объект держит игрока» (`Busy`, `Clip`, `Frozen`, `Holds`, `ReleaseIfHost`, `LeaveOnMove`); база `PostureFeature` — общий порядок входа и выхода, наследник даёт подписи и `OnEnter`/`OnLeave`. Новая поза не требует правок в старых | `Grid/Objects/Features/PostureFeature.cs` |
| Квантование следа по подсетке, доводка предмета внутрь площадки | `PlaceMath.SubWidth/SubSnap/SlideInside` — чистые функции без сцены, покрыты тестами | `Grid/Core/PlaceMath.cs` |
| Список всех объектов каталога | `FurnitureCatalog.All()` — рефлексия по фабрикам, кэш | `Grid/Objects/FurnitureCatalog.cs` |
| Шейдеры | `ShaderLib.Lit/Unlit/Get` — никогда `Shader.Find` в рантайме | |
| Центральный тикер | `WorldTick` — один `SceneSingleton`: в `Update` зовёт `InteractiveObject.TickAll()` и `Burnable.TickAll(dt)`, в `LateUpdate` — `TreeWind.TickAll()`; у этих классов нет своих `Update`/`LateUpdate`, есть `Tick()` и статический список `All` (регистрация в `OnEnable`/`OnDisable`, поэтому `enabled = false` = не тикает). Правило: у типа с тысячами экземпляров — тикер, а не Unity-`Update` (10.09: 5550 вызовов стоили 2 мс сами по себе) | `Grid/View/ViewSensor.cs` |
| Радиус рендера | `FarRadius` — объекты дальше 28 м от игрока не рисуются (`forceRenderingOff`) и спят (`TreeWind`/`Burnable` выключены, `InteractiveObject.Far`), ближе 24 м живут; ломтик 800 объектов в кадр; `FarRadius.IsHidden(io)`, `FarRadius.Enabled`. VIEW.md §10c | `Grid/View/ViewSensor.cs` |
| В кадре ли главной камеры | `ViewCull.InView(Bounds)` — плоскости фрустума `Camera.main` считаются раз в кадр, дальше `TestPlanesAABB`; НЕ `Renderer.isVisible` (тот в редакторе считает видимым всё, что видит Scene View и камера теней). Им гейтятся изгиб травы и деревьев (`TreeWind`), анимация клубов тумана (`FogAnim`) и частей костра (`FireVolume`), 10.09 | `Grid/Weather/WindGusts.cs` |
| Клеточный объём на сетке (туман, огонь) | `CellVolumeView<T>` — реестр клеток, версия для контура, привязка и переезд, снос клетки, заливка зоны; наследник даёт `Rebuild`, `Touch` (кого будить) и `Ready` | `Grid/Weather/CellVolumeView.cs` |
| «Какие стороны клетки закрыты стеной» | `CellWalls` | `Grid/Core/CellWalls.cs` |
| Дебаг-контур области клеточного объёма | `ZoneArea` (поле расстояний + marching squares), одиночка — `ZoneArea<T>` | `Grid/Weather/ZoneArea.cs` |
| Системный объект, живущий по одному на сцену | `SceneSingleton<T>.SpawnEachScene()` — без аргументов: найти по типу, если нет — создать объект с именем класса. Вариант с лямбдой нужен только тем, кто делает БОЛЬШЕ (помнит экземпляр, будит выключенный) | `View/SceneSingleton.cs` |
| Узел модели по имени (включая неактивные, корень тоже) | `FurnitureModel.FindNode(root, name)` — буфер, без массива на вызов; `InteractiveObject.FindChild` — ДРУГОЙ ответ (без корня, с запасным поиском по подстроке) | `Grid/Objects/FurnitureModel.cs` |
| Список id через запятую в дефе | `ObjectDef.IdList(ids)` (кэш разбора, части обрезаны) / `ObjectDef.IdListHas(ids, id)` — `Split(',')` в коде не пишем | `Grid/Objects/ObjectDef.cs` |
| Трансформ игрока лениво | `PlayerRef.Transform` — своё поле-кэш поверх него не заводим, одна строка `if (_player == null && (_player = PlayerRef.Transform) == null) return;` | `Grid/Core/PlayerRef.cs` |
| Плоское (XZ) квадрат расстояния | `PartMath.SqrPlanar(a, p)` | `Grid/Core/PartMath.cs` |
| Луч на горизонтальную плоскость; уровень пола постановки | `GridCursor.PlaneHit(ray, y, out hit)` (Plane.Raycast сам отвергает enter ≤ 0), `GridCursor.PlaceFloorY()` | `GridCursor.Place.cs`, `GridCursor.Objects.cs` |
| Прямоугольник UI-элемента в экранных координатах | `ScreenClampUI.WorldRect(rt)` (общий буфер углов) | `Game/UI/Kit/ScreenClampUI.cs` |
| Рект по центру родителя; кнопка с подсветкой и курсором; растянутый sliced-оверлей | `UiFactory.Center(rt)`, `UiFactory.HoverButton(rt, img, colors, onClick)`, `UiFactory.Kit.StretchedSliced` | `Game/UI/UiFactory*.cs` |

## Разложение больших классов по партиалам

- **`InteractiveObject`** (ядро 447): `.Model` — модель, коллайдеры, свет,
  силуэт; `.Parts` — подвижные части, переключатели, тряска/нажатие, замок,
  головоломка; `.Size` — растяжение и счётчик; `.Slots` — слоты и предметы в
  них; `.Temperature` — тепло и жидкость.
- **`GridCursor`** (ядро 608): `.Objects` — пайплайн позы (см. ниже);
  `.ObjectSnap` — магниты и прижимы; `.PlaceQueries` — лучи к миру (стена за
  спиной, верх опоры, точка курсора); `.PlaceGhost` — призрак и его покраска;
  `.Support` — опора, слоты, «влезает ли», дотягивается ли рука; `.ObjectMove`
  — перенос в руках; `.Transfer` — передача содержимого (Pour/Serve/Put);
  `.Layout` — раскладки, призраки кладки, подпись действия; `.Levels` —
  сейв/лоад; далее по темам (Paint, Dig, Stairs, Zones, Roof…).
  Чистая арифметика постановки живёт отдельно от курсора — `PlaceMath`.
- **`HudUI`** — ядро-композитор плюс партиалы панелей; вынесенные контроллеры
  (`PlayerStatHud`, `FpsHud`, `TimeBarHud`, `DebugOverlayHud`, `ViewModeHud`)
  живут отдельными файлами.
- **`AiConsole`** (08.10 вечер, с 11.10 — `Assets/Modules/Life/AiConsole.cs`, сборка Cozy.Creatures; статический класс
  без UI) — пульт модели для существ: чат, часовой тик, события чувств, разбор
  JSON-ответа, `spawn/remove/plan`, системный промпт и снимок уровня, три ленты
  (`Chat`, `Journal` «Действия монстров», `RulesLog` «Проверка правил»).
  `HudUI.Ai.cs` — только вкладка «ИИ»: виджеты и подписка `AiConsole.Shown`.
  Направление связи: `Cozy.Creatures` ссылается на `Tavern.UI` (исторически ради
  `GameEvents`), поэтому `CreaturePlan`/`LifeRules` зовут `AiConsole` напрямую,
  а обратно — хуки `AiConsole.RunPlan/DescribePlan/RulesCheck/RulesRunNow/
  RulesApplied`, выставляемые в `[RuntimeInitializeOnLoadMethod]`. Тип шага
  плана — `Tavern.UI.PlanStep` (поля = JSON модели). Общее про существ лежит
  ниже: `ZoneEvent.CreatureKind/FreeName`, `CrowZoneSpawn.Place/FailureText/
  RemoveCreature/InZone/AtMark`, `CreaturePlan.FindObject/ZoneBy`, `Weather.Clock`.
- **`CreaturePlan`** (Monsters, 08.10 вечер): ядро — стек планов, `Begin/Act`,
  `Run/Describe`; `.Nav` — путь по сетке, спрямление, ходьба, бродяжничество;
  `.Senses` — чувства и события (`Sense/ScanObjects/Emit`); `.Actions` —
  переключатели, двери, взять/положить.
- **`Creature`** (Monsters, 11.10, ilya-65) — общее ядро существ: этаж
  (`Storey/StoreyY/SameStorey/CellSize` — им считают `CreaturePlan` и
  снимок рёбер `MonsterNav`), тело-манекен (`Dummy` + `Animate` — Тень). Безумец
  (`Monster`) удалён целиком 11.10.
  Новое существо берёт этаж и тело отсюда, а не пишет свою копию. Гейт «по игроку
  не бьют» для любых атак существ — `PlayerTarget.OffLimits` (Character).
- **`LifeRules`** (Monsters, статический): `LifeRules.cs` — исполнение
  (`Tick/Hourly/Once/Applied/OnEvent/Fire*`, `Count`, `Check/Describe`);
  `.Parse` — разбор строк и групп, таблицы синонимов, словарь видов, локации.
- **`PhoneUI`** (09.10, было 4573 строки в одном файле): ядро `PhoneUI.cs` —
  поля, вид, данные контактов, `LateUpdate`, тряска/призрак; `.Screens` —
  `Rebuild`, галерея и фото, домашний экран, боковые кнопки, питание; `.Calls` —
  вкладки звонков, недавние, сюжетные звонки (`StoryTick/SeedStory/PlayStory`),
  входящий и разговор; `.Maps`; `.Contacts` — новый контакт, набор номера,
  доставка; `.Messages` — треды, пузыри, ввод, баннер; `.Alarm`; `.Shell` — звуки
  звонка, подложка, шапка, «телефон в руке»; `.Lock` — экран блокировки, код,
  лицо; `.Shade` — шторка, текстовые помощники, `RefreshLive`. Фотоаппарат —
  отдельный класс `CameraUI.cs` (раньше жил в `PhoneUI.cs`).
- **`CrowZoneSpawn`** (09.10) — свой файл `Combat/CrowZoneSpawn.cs` (раньше в
  `CrowAttack.cs`): появление существ в зоне, `Place` с откатом ветка → земля,
  `FailureText`, `RemoveCreature`, `InZone`, `AtMark`, насесты и земля.
- **`FogVolume`** (ядро 115): `.Layout` — файл раскладки и прореживание;
  `.Shape` — форма клетки (кромка, посадка у стен, коробка среза); `.Spawn` —
  постановка клубов по раскладке. Компонент анимации — `FogAnim.cs`, дебаг-слой
  области — `FogArea.cs` (2026-09-05).
- **`FireVolume`** (ядро 224): `.Parts` — из чего сложен костёр; `.Look` — свет,
  банк мешей, материалы; `.Anim` — как он живёт (2026-09-05).
- **`HudUI` — панель дебага F1** (16.09): `HudUI.Debug.cs` — каркас (слой,
  таблица вкладок `DebugTabs`, ряды, разделы, палитра, отражение `Tune*`),
  вкладки — в файлах доменов `HudUI.DebugView/Weather/Player/Effects/Monsters/Skin.cs`,
  сохранение — отдельный класс `DebugTune.cs`. Карта — `UI.md`, «Дебаг-панель F1:
  где что лежит в коде».
- **`CrowFlight`** (ядро 587, 16.09): `.Path` — маршрут и ход полёта (разгон,
  полка, торможение, позы по дорожкам); `.Wings` — профили махов пород (данные
  из `crow_scene.py`/`owl_scene.py`); `.Targets` — выбор места посадки (ветки,
  земля, крыши, погода, испуг, соседи).

## ⭐ Пайплайн постановки объекта (единственный путь)

И первоначальное размещение (тело = призрак), и перенос зажатием (тело =
сам объект) идут через `GridCursor.ComputeObjectPose`. Метод — список
шагов над общим состоянием `PoseWork`; **порядок шагов и есть правило
постановки**, поэтому новое поведение вешают в НУЖНЫЙ шаг, а не в конец.

| Шаг | Что делает |
|---|---|
| `BeginPose` | точка курсора (пол / верх опоры / плоскость стены), флаги `Kit/Free/WallMount/FreeWall`, стартовые X/Z и поворот; чтение колеса и Shift/Ctrl |
| `SnapToNeighbours` | магниты к тому, что уже стоит: соседняя накладка, подклеточный снап, хозяин по `snapToId`, стул к столу |
| `SnapToWall` | навесной садится спиной по нормали стены (`WallTuck` + `SeatBackToWall`), напольный — по `seatToWall`; потолочный вместо этого едет по боковому стопу |
| `SnapKitLine` | кухонная линия: стык в стык с соседним модулем, посадка к стене, боковая посадка углового |
| `ResolvePoseHeight` | высота крепления: пол, верх опоры, потолок или точка на стене; сразу вердикт «есть ли на чём держаться» |
| `ValidatePose` | занятость линии кухни, вытянутая рука, доводка в слот, опора под поверхностным объектом, пересечение с чужими телами |
| `ApplyLiftStop` | вертикальный стоп Shift+колесом и посадка поднятого объекта на опору |

Правила валидности, которые стоит помнить (все — из жалоб Ильи):
- **Проверка, которую игрок обязан удовлетворить точным наведением, — плохая
  проверка.** Предмет над секцией с дверцами не отвергается, а ДОВОДИТСЯ
  внутрь площадки (`ClampIntoSlot`); не влезает по размеру вовсе — встаёт по
  центру, и отказ честный.
- **Внутри секции место определяет хозяин**: стена, на которой он висит, и
  перекрытие под ним не помеха его содержимому.
- **Занятость не-напольного объекта мерится ЕГО телом на ЕГО высоте**, а не
  боксом у пола: навесной шкаф не занимает плиту и тумбу под собой.
- **Магниты кухонной линии — про напольные модули.** Настенный ни к каким
  позициям не липнет, только спиной к стене.
- `hangFixed` у настенного объекта выключает всю ветку свободного
  навешивания (посадку на стену, поворот по нормали, высоту от курсора) —
  свободному объекту его не ставить.

## ⭐ Правила наведения (Interactor)

`Raycast` идёт по отсортированным попаданиям и держит ДВЕ цели: ближайшую и
лучшую вложенную. Причины «это попадание не цель» собраны в `SkipHit`
(закрытая секция, продукт вне осмотра своей посуды, объект `builtIn`,
невидимый рендерер, хост без фич, прятки). Две вещи, на которых уже
обжигались:
- «Вложенным» считается только то, что лежит ВНУТРИ ближайшего или глубже
  (`InteractiveObject.NestedInside`, цепочка `Container`). Иначе прибор,
  сам вложенный в плиту, занимает роль вложенного и ранним выходом из цикла
  закрывает дорогу собственному содержимому.
- Продукт доступен только в осмотре ТОГО САМОГО прибора, где лежит, —
  проверка по ПРЯМОМУ хозяину (`NestedBeatsHost`), а не по цепочке.
- ⭐ 05.10: общие «это не цель» вынесены в `RayPick.Classify` (игрок, невидимое, голый триггер, `noPick`, `passThrough`) — его зовут `Interactor.SkipHit`, `GridCursor.Raycast`, `NearestVisiblePiece`, `PaintRaycast`, прицел `AimFocus` и бросок. В `SkipHit` остались только правила игры (осмотр, контейнеры, прятки, хост без фич).
- ⭐ Разборов луча ДВА: игровой `Interactor.Raycast` и строительный
  `GridCursor.NearestVisiblePiece` (через `PieceOnRay`, тоже «вложенный
  побеждает хозяина»). Любое «это не цель» — закрытая секция
  (`Targeting.Hidden`), погашенный рендерер, чужой этаж, `noPick` — стоит в
  ОБОИХ; гейт, добавленный в один, в стройке молча не работает (P569: яйца
  сквозь закрытую дверцу холодильника, 25.09).

## Тесты

`Assets/Tests/EditMode`, сборка `Tavern.Tests.EditMode` (ссылается на
Cozy.Grid / Cozy.View / Cozy.Cooking). Гоняются за секунду:

- `CatalogTests` — каждый объект каталога резолвится через `ById` по своему id
  (иначе он **молча исчезает при загрузке уровня** — так теряли растительность);
  id уникальны; материал из палитры пяти; маркеры утилизации из набора.
- `CookBookTests` — переходы ведут в существующие состояния, у состояний есть
  модель и подпись, имена не повторяются, нагрев не зациклен.
- `GridSnapTests` — центр клетки, граница клетки, привязка к оси и кромке.
- `LayoutTests` — раскладки кладки: у каждого слота свой поворот, предел не
  больше числа слотов (кроме стопки), результат есть в каталоге, слоты не
  уехали от приёмника.
- `PlaceMathTests` — арифметика постановки: округление ширины вверх с
  допуском 2 см на кромки, след встаёт на линию подсетки, соседний курсор
  даёт соседний слот, доводка предмета внутрь площадки (свес, центр,
  «не целиться ровно в границу»).

- `ModelNodesTests` — деф и модель держатся вместе: каждый узел, на который
  деф ссылается по имени (часть, слот, раскладка, лампа, таймер, индикатор,
  коллайдер, высота/крона), существует в своём FBX; у счётчика проверяется
  ПРЕФИКС — «Slice0…Slice5» на countMax делений. Ловит класс «механика молча
  не работает после переименования узла в эталоне».

Всего 31 тест, ~1 с. `CatalogTests` заодно проверяет ссылки дефов друг на
друга (spawnWith, snapToId, productId/resultId/liftOverId раскладок).

Запуск: Unity → Window → General → Test Runner → EditMode → Run All, либо
через MCP `run_tests` (mode EditMode, assembly `Tavern.Tests.EditMode`).

**Что тестами НЕ покрыто** (и почему): всё, что требует сцены, физики и
кадров, — постановка объектов, видимость, камера, готовка во времени. Для
таких правок работает другой приём — характеризующий замер, см. ниже.

## ⭐ Как править опасное место безопасно (характеризующий замер)

Приём, которым ночью 29.08 переписаны `ScanBuilding` и `LateUpdate` камеры:

1. **До правки** снять поведение замером в play через MCP `execute_code`:
   прогнать функцию по сетке входов и записать выходы в файл
   (для видимости — игрок в 450 позициях, вердикт сканера; для камеры —
   200 шагов сглаживания из фиксированного состояния, итоговая поза).
2. Отрефакторить.
3. Повторить замер и **сравнить файлы построчно**. Расхождение = регрессия.

Готовые зонды лежат в `probes/` рядом с этим файлом: `hover_probe.cs`
(что возвращает `Interactor.Raycast` по каждому объекту сцены с четырёх
ракурсов, в осмотре и вне), `pose_probe.cs` (что возвращает
`GridCursor.ComputeObjectPose` по сетке точек) и `README.md` с протоколом и
граблями. Главное правило протокола: **между замерами «до» и «после» сцену
не трогать** — если в это время кто-то играет, дифф покажет переезд вещей,
а не вашу правку.

Правила зонда: состояние сцены менять только внутри `try/finally` с возвратом
(зонд, упавший посреди цикла, однажды оставил игрока лететь в пустоту и час
выглядел как «регрессия»); после переноса игрока — `Physics.SyncTransforms()`,
иначе физика отвечает по старой позиции.

## ⭐ Сверка рендером (когда спор о КАРТИНКЕ, а не о числах)

Родственник характеризующего замера для случая «в игре выглядит не так».
Отработан на тумане 04.09; полная процедура — `BUILD.md`, «ПЕРЕНОС РИСУНКА ИЗ
BLENDER В ИГРУ». Ядро приёма:

1. Снять обе картинки ОДНИМ ракурсом на одном фоне: в блендере — ортокамера и
   `bpy.ops.render.render`, в игре — своя `Camera` + `RenderTexture` +
   `ReadPixels` → png. Анимацию погасить с обеих сторон, иначе сравниваешь фазы.
2. Сначала оставить ОДИН элемент. Одиночный элемент отделяет ошибку цвета от
   ошибки наложения: пока не сошёлся один, сравнивать кучу бессмысленно.
3. Считать числа, а не смотреть глазами: медиана и перцентили пикселей внутри
   силуэта, площадь силуэта, ширина, центр масс. Глаз не отличает 116 от 156.
4. Отклик шейдера, если подозрение на цвет, мерить СЕТКОЙ (цвет × альфа через
   рендер), а не выводить из теории про цветовое пространство — теория тут
   врёт систематически (P192).

Зонды разовые, живут в скретчпаде сессии; в репозиторий кладём только числа —
в инвариант («одиночное ядро 116 против 117») и в `DESIGN_LOG.md`.

## Ритм работы с редактором

- В play Unity **откладывает компиляцию** (ScriptCompilationDuringPlay = 1):
  правки в файлах не применяются, пока не выйдешь из play. Цикл проверки:
  stop → `refresh_unity(compile)` → play → зонд.
- Компилировать, пока Илья играет, нельзя (см. SKILL.md). Офлайн-проверка без
  редактора — `python3 compile_check.py` в корне проекта (Roslyn, ~40 с).


## Конструктор: что добавляется данными, а что требует кода

_2026-08-31._

Правило Ильи: «всё обособлено, без хардкода — это конструктор состояний и
переходов, окружений». Ниже — актуальная карта: где данные, а где ещё код.

| Что добавляем | Где это данные | Код трогать |
|---|---|---|
| Объект мира | `FurnitureCatalog.*` — деф (`ObjectDef`), + строка в баре | нет |
| Категория объекта | `Categories` (реестр строк) + деф | нет, но новую строку заводить в реестре — иначе тест `Категория_объекта_из_общего_реестра` красный |
| Атрибут поведения | `ObjectDef` (поле) + строка в `ObjectAttributes.Flags` | гейт в ОДНОМ месте (см. `ATTRIBUTES.md`) |
| Продукт и его состояния | `CookBook`: `CookState` (модель, съедобность, перенос, утилизация, сытость, грязь) | нет |
| Переход состояния | `CookBook`: `HeatStep` (из, во, минимальная температура, секунды) | нет |
| Раскладка «что в чём готовится» | `ObjectDef.cookLayouts` | нет |
| Нагрев прибора | `ObjectDef.tempSources` | нет |
| Слоты и гейты (полки, дверцы) | `ObjectDef.slotNodes`, `parts` | нет |
| Прибор варки (кофеварка, чайник) | `ObjectDef.brewer` (`BrewerSpec`: узлы кнопки/носика/гейта, id расходников, литры в секунду, температура) | нет — компонент вешается по наличию блока |
| Жидкость | `LiquidVolume` (виды и цвета) | да, пока код |
| Питание и вода | `ObjectDef.utility`, `powersZones`, `needsPower` | нет |

Остаточный хардкод, который стоит вынести следующим (на 31.08): виды
жидкостей и их цвета/температуры в `LiquidVolume`; маркеры утилизации
(`disposes`: «жидкое», «жареное», …) — строки живут и в дефах, и в
`CookBook`, реестра пока нет; категории ПРЕДМЕТОВ инвентаря (`ItemDef.category`
и `ObjectSlot.category`) — второй словарь рядом с `Categories`.


## Производительность: базовые цифры кухни

_Замер 2026-08-31, ilya-42._

Сцена «кухня + дом», 37 интерактивных объектов, 382 рендерера:

| Что | Стоимость |
|---|---|
| Вся игровая логика за кадр (37 объектов, жидкости, кипение, вырезы стен, этажный вид) | ≈ 0.08 мс |
| `Interactor.Raycast` (наведение) | 0.005 мс |
| `HudUI.LateUpdate` вне осмотра | 0.001 мс |
| `HudUI.LateUpdate` в осмотре (силуэт объекта каждый кадр) | 0.147 мс — самая дорогая покадровая строка |
| Кадр без выделения | 485 вызовов отрисовки, 818 тыс. треугольников |
| Кадр с выделенной тумбой | 553 вызова (+68), 834 тыс. треугольников |
| Первая подсветка объекта | 0.3–0.9 мс (объединение мешей), повторная — 0.5 мс |

Выводы: логика дешёвая, узкое место — отрисовка. Обводка стоит по копии
маски и 16 полос на ВЕТКУ объекта: 68 вызовов на крупную мебель, 17 на
предмет. До 31.08 копии делались на КАЖДЫЙ меш — тумба добавляла 1173 вызова
(в 3.4 раза больше, чем весь остальной кадр), сейчас +14 %. Следующий рычаг,
если понадобится: число направлений канта (16 → 8 уполовинит и вызовы, и
треугольники обводки), но Илья выбирал 16 ради гладких углов — менять только
с его согласия.

Мерить так: `UnityEditor.UnityStats.drawCalls/batches/triangles` в play,
покадровые методы — Stopwatch вокруг их вызова через рефлексию (см. записи
в PITFALLS про зонды).


## Сеть целостности контента

_2026-08-31._

Конструктор держат вместе не соглашения, а тесты. Что проверяется на каждом
прогоне EditMode (53 теста):

| Проверка | Где | Что ловит |
|---|---|---|
| Узлы дефа есть в модели (обход рефлексией: `*Node`, `*Nodes`, `led`, `heat`, `gateSlot`, `drainSwitch`, вложенные тумблеры/части/слоты/источники тепла/кофеварка) | `ModelNodesTests` | переименовали ноду в Blender — механика молча умерла |
| У каждого дефа есть модель: ресурсная или процедурная (`ProceduralModels.Has`) | `CatalogTests` | забыли сборщик — объект ставится невидимым |
| Ссылки дефов (`accept`, `spawnWith`, `snapToId`, `groundsId`, `tankId`, `greaseWithId`, `cleanWithId`) ведут в живой объект или предмет | `CatalogTests` | слот не принимает предмет, кофеварка не находит гущу |
| Точка прилипания есть у хозяина | `ModelNodesTests` | мойка не садится в вырез тумбы |
| Модели состояний готовки грузятся из папки своего дефа | `CookBookTests` | пожарили — вид не сменился |
| Рецепты ссылаются на живые продукты и приборы | `CookBookTests` | рецепт из воздуха |
| Атрибуты, категории, маркеры утилизации — из реестров | `ObjectAttributesTests`, `CatalogTests` | второй список правды |

Процедурные модели с 31.08 — таблица `ProceduralModels.Builders()`
(«папка/модель → сборщик», 57 записей) вместо лестницы из 57 «если»; два имени
с суффиксом (газон по стороне, лифт по этажности) остались правилами в `Build`.
Отсюда же растёт `ProceduralModels.Has` для теста выше.


## Замеры и бюджеты

_2026-08-31, вечер._

Сцена кухни в play, через `UnityEditor.UnityStats` и обход рендереров:

| Что | Было | Стало |
|---|---|---|
| Видимых треугольников в сцене | 115 876 | 75 400 |
| Самая тяжёлая модель проекта (`torchLight`) | 47 848 | 3 356 |
| Газировка `waterSoda` | 39 930 | 2 166 |
| Вызовов отрисовки | 535 | 531 |
| Моделей в Resources / суммарно треугольников | 212 / 214 839 | 212 / ~170 000 |

Две причины, обе теперь под тестом `ModelBudgetTests` (порог 15 000):
- `bpy.ops.mesh.subdivide(number_cuts=N)` режет КАЖДУЮ грань на (N+1)², а не
  только вдоль оси. Профиль вдоль оси кладётся кольцами (`lathe`-стиль), а не
  подразделением: у фонаря это 3 356 вместо 47 848 при той же форме.
- Устаревший FBX: модель собрана прошлым поколением генератора и с тех пор не
  пересобиралась. Лечится прогоном `build_kit.py -- <ключ>`.

### Сеть тестов на 31.08 (60 штук, все зелёные)

К прежним проверкам целостности добавились:
- «До каждой части есть чем дотянуться» — у объекта с тумблерами или рычагами
  обязан быть путь: осмотр или глобальная часть. Нашла мёртвый кондиционер.
- «Рычаг питания есть только у питаемых».
- «Ни одна модель не тяжелее бюджета» — 15 000 треугольников на модель.

### Правило видимости при переносе

`ContainerSlot.HoldsClosed` — единственный источник правды «предмет заперт в
закрытой секции». Через него теперь проходят ВСЕ входы: выделение и клик
(`Interactor`), подача и уборка (`ServeTargetUnder`), перелив
(`PourUnderCursor`), поиск раскладки (`LayoutHostUnder`), пара для блюда
(`GridCursor.Dish`) и поиск опоры при постановке (`SurfaceTopAt`).


## Сохранение состояния: что уже едет в сейв

_01.09._

Ревизия `LevelIO.ObjectData` против живых механик — чтобы не гадать, что
переживёт перезагрузку:

| Состояние | В сейве | Примечание |
|---|---|---|
| Поза, поворот, высота, ширина, крона | да | |
| Замок, доступ, питание и зоны, головоломка щитка | да | |
| Цвет, содержимое инвентаря, вложенность (`carrierId`/`carrierNode`) | да | вложенность чинилась 01.09 |
| Жидкость: вид, литры, смесь | да | |
| Готовка (состояние продукта), грязь, смазка, соус | да | прогресс ВНУТРИ состояния не пишется |
| Счётчики (`count`) | да | |
| Положение тумблеров | да | добавлено 01.09, до этого терялось |
| Цели настенного выключателя | да | |
| Связка блюда (`ObjectGroup`) | НЕТ | открыто за ilya-1c |
| Горка посуды в мойке (`SinkPile`) | НЕТ | предметы сохраняются, сама горка выводится |

Проверять прогоном `probes/level_roundtrip.py`, а не глазами: обе потери
2026-09-01 (вложенные предметы и тумблеры) нашлись именно им, при том что в
игре они выглядели как «ну исчезло и исчезло».

## Замеры кадра: кухня в play

_01.09._

Вызовов отрисовки 543, setPass 54, треугольников по статистике 840 тысяч,
из них ГЕОМЕТРИИ сцены 82 тысячи (остальное — проходы и тени). Интерактивных
объектов 52, видимых рендереров 473. Для сравнения, до чистки моделей 31.08
геометрии было 116 тысяч при 42 объектах.

## Мусор на кадр: мерить в СБОРКЕ, а не в редакторе (2026-09-06)

Редактор сам по себе даёт сотни килобайт на кадр, и год подряд это считали
мусором игры. Замер на одном и том же уровне «Test #1» при стоящем игроке:
редактор в play — 241 982 Б на кадр (пик 284 627), дев-сборка — 483 Б на 300
кадрах и 489 Б на 600 (пик ~8.5 КБ). Разница в пятьсот раз, воспроизведено
дважды.

⭐ **То же и с ВРЕМЕНЕМ кадра** (13.09, прод-сборка, `Tavern.x86_64 -gcprobe 240`,
тот же Test #1, i7-13700K): **кадр 2.19 мс среднее, p95 3.31, пик 5.10; мусор
363 Б на кадр, пик 15 274**. В редакторе на том же уровне в тот же день — 6.0 мс
и 13 700 Б. То есть редактор врёт втрое по времени и в тридцать раз по мусору,
и обе цифры растут по мере того, как редактор работает (к утру куча Mono дошла
до 850 МБ, и замеры поплыли на ±1.5 мс).

Как этим пользоваться: редакторский профайлер годится, чтобы СРАВНИВАТЬ системы
между собой и видеть, что правка помогла (маркеры — честные), а абсолютные
числа брать только из сборки. Запуск: собрать (`BuildRequests/linux.request`),
потом `./Builds/Linux/Tavern.x86_64 -gcprobe 240 -screen-fullscreen 0
-screen-width 640 -screen-height 360`, строка `[gc] avg=… ms=… p95=…` уходит в
`~/.config/unity3d/DefaultCompany/Tavern/Player.log`. ⚠️ Прод-сборка открывает
ПОСТАВОЧНЫЙ уровень (`Resources/Levels/test_1/level.json`), а не то, что стоит
дев-уровнем по умолчанию, — forest100 так не померить.

Как мерить в сборке (с 10.09 строка `[gc]` несёт и кадр: `ms=` среднее, `p95=`, `msmax=`; замер 10.09 на Test #1 — 3.76 мс, 898 Б/кадр): `GcProbe` запускается ключом — `Tavern.x86_64 -gcprobe
[кадров]` (по умолчанию 240). Первые 180 кадров идут на прогрев, чтобы в
среднее не попала загрузка уровня; результат печатается строкой `[gc] avg=…
max=… frames=…` в `Player.log`
(`~/.config/unity3d/DefaultCompany/Tavern/Player.log`), потому что MCP-моста в
сборке нет. Сборка — штатным триггером `BuildRequests/linux.request`, 17 с.
В редакторе по-прежнему `probes/gc_probe.py`, но его числа сравнивать можно
только с числами редактора же.

⚠️ Инструмент замера аллокаций проверять КОНТРОЛЕМ (P247): `GC.GetTotalMemory`
и `GC.GetAllocatedBytesForCurrentThread` в этом рантайме врут нулями даже на
контрольном цикле в 2 МБ. Годится `Profiler.GetMonoUsedSizeLong()` рядом с
контрольным циклом, для кадра — `ProfilerRecorder`.

⚠️ **Сценарии в редакторе сравнивать бесполезно: собственный шум редактора
±25 КБ на кадр.** Три прогона ОДНОГО И ТОГО ЖЕ фона (ничего не открыто, игрок
стоит) дали 201, 238 и 249 КБ. На таком фоне дельта открытой карточки, открытого
инвентаря или играющего клипа неотличима от шума — у инвентаря она вообще вышла
отрицательной. Отсюда же следует, что прежний вывод «все тикающие типы
`Cozy.Grid` дают лишь ~30 КБ» (A/B-скан 02.09) сам был в пределах шума. Мерить
сценарии можно только в СБОРКЕ, где фон 489 Б. Сейчас в сборке измерен покой;
если понадобится мерить открытые экраны, к `-gcprobe` придётся добавить ключ,
который сам открывает нужный экран, — с клавиатурой в сборке снаружи не
поговорить.

## Локализация: сборка `Cozy.Loc` (2026-09-02)

`Assets/Modules/Loc` — самая нижняя сборка игры (зависит только от TextMeshPro),
на неё ссылаются Grid, Character, Cooking, Monsters, Core, Net, UI, Tests.
`Loc.T(ru)` / `Loc.F(ru, args)` — ключ = русский текст; таблица
`Resources/Localization/en.json` (+ `en.extra.json` для склеенных подписей).
Граница — `UiFactory.Configure`/`InputText`: любой текст, прошедший фабрику,
переведён и привязан `LocText`. Правила кода: (1) текст для игрока не склеивать
из русского слова и значения через «+», только `Loc.F` с целой фразой;
(2) идентификаторы (категория, кит, материал) не переводить в месте объявления,
они переводятся при показе; (3) после правки строк — `python3 loc_extract.py`
и заполнить пустые значения в `en.json`; тест `LocalizationTests` не пропустит
дыру.

## Сборка игры под Linux и стартовый уровень (2026-09-02)

**Как собрать.** `Assets/Editor/BuildLinux.cs`: меню Build → «Linux Build» (дев,
`BuildOptions.Development`, выход `Builds/Linux/Tavern.x86_64`) и «Linux Build
(prod)» (`BuildOptions.None`, `Builds/LinuxProd/Tavern.x86_64`). Из сессии, без
рук в редакторе: положить файл-триггер `BuildRequests/linux.request` (дев) или
`BuildRequests/linux_prod.request` (прод). Вотчер `BuildLinuxWatcher` раз в 2 с
видит файл, ждёт, пока нет play, компиляции и другой сборки, делает
`AssetDatabase.Refresh` (иначе правки .cs, сделанные снаружи, в сборку не
попадут), удаляет триггер и строит. Результат: маркер
`BuildRequests/linux.done|failed` (или `linux_prod.*`) со строкой
«Succeeded: путь | размер | errors N, warnings M | секунды». Инкрементальная
сборка 15–20 с, дев ≈ 320 МБ, прод ≈ 245 МБ. Play в редакторе сборку блокирует,
сначала выйти из play. Запуск из любого места: полный путь к `Tavern.x86_64`;
переносить папку сборки целиком (`Tavern_Data`, `UnityPlayer.so`, `libdecor*`).

**Откуда берётся уровень при старте** (`GridCursor.Levels.TryAutoLoad`):
1. Редактор и ДЕВ-сборка (`Application.isEditor || Debug.isDebugBuild`): уровень
   «по умолчанию» из PlayerPrefs `DevDefaultLevel` (ставится в меню уровней,
   `HudUI.Levels`), если есть его сейв в `persistentDataPath/levels/<имя>.json`.
   На этой машине это `~/.config/unity3d/DefaultCompany/Tavern/levels/`, папка
   ОБЩАЯ для редактора и сборок (та же компания и продукт), PlayerPrefs тоже.
   Менять её умеет ТОЛЬКО тумблер: `LevelIO.DevDefaultLevel` на чтение,
   `SetDevDefaultLevel` берёт значение лишь в кадре, взведённом
   `ArmDevDefaultFromUi()` из `HudUI.Levels`, и только в play — вызов из моста
   отбивается предупреждением (инвариант 182, P422).
2. Иначе, и ВСЕГДА в прод-сборке: уровень с именем сцены (`level1`) из тех же
   сейвов; нет сейва — поставочный из `Resources/Levels/<слаг>/level.json`
   (`LevelIO.LoadBundled`, в билд попадает через Resources); нет и его — первый
   из `ListBundled()`. Сейв всегда перекрывает поставочный (`LevelIO.Load`).

⭐ Грабля 2026-09-02 (Илья: «уровень не актуальный, в редакторе вижу другой»):
редактор работал на «Test #1» (дев-уровень по умолчанию), а прод-сборка открыла
`level1.json`, лог `Player.log` это показал. Правило: чтобы сборка показывала
то же, что редактор, собирать ДЕВ-сборку (`linux.request`); прод на этой машине
откроет `level1`, пока лежит его сейв. Поставочная копия «Test #1»
(`Resources/Levels/test_1/level.json`) обновляется руками копированием сейва
(`Test #1.json` → `level.json`, `sceneName` внутри уже «Test #1»); обновлена
02.09, до того лежала от 30.08. Открытый вопрос в OPEN.md: должна ли прод-сборка
предпочитать поставочный уровень сейву по имени сцены.

## ⭐ Что ломается ТОЛЬКО в сборке — принцип и порядок разбора

Записано 13.09 после просвета кроны (P380), семья та же, что у P015. Илья:
«это критично, мы так можем терять разные штуки».

**Принцип.** Редактор достаёт шейдеры и их варианты ПО ТРЕБОВАНИЮ, сборка
кладёт их ПО СПИСКУ. Всё, что в редакторе появляется само, в сборке должно быть
заявлено заранее. Три ловушки, каждая уже стоила дня:

1. **Шейдер без материала-ассета** (`ShaderLib.Get` + `new Material`) в билд не
   попадает → Always Included Shaders (P015). Пропажу `ShaderLib` кричит в
   `Player.log` — это единственная громкая из трёх.
2. **Ключ, который включает код** (`EnableKeyword`, `ShaderLib.MakeTransparent`,
   а также ключи, скопированные `new Material(source)`) обязан быть
   `multi_compile`, не `shader_feature` (P380). `shader_feature` собирается
   только под материалы-ассеты; у рантайм-шейдера их нет — в сборке живёт один
   голый вариант, и Unity МОЛЧА подставляет его вместо нужного.
3. **Настройки** (`ProjectSettings/*`, `Assets/Settings/*`) правятся только
   через редактор в edit mode; текст под открытым редактором затирается (P015),
   а у URP-флагов по три копии, живая — managed reference (P380).

**Как узнать правду о сборке без глаз.** `~/.config/unity3d/Editor.log` после
сборки: блок `Compiling shader "<имя>"`, по каждому проходу строка «After
scriptable stripping N». Нет варианта — нет фичи, что бы ни показывал редактор.
`Player.log` сборки — только ошибки `ShaderLib`; остальное молчит.

**Порядок при «в редакторе есть, в сборке нет».** Сначала факты, потом версии:
(1) `Player.log`: ошибки, `ShaderLib`; (2) `Editor.log`: варианты нужного
шейдера по проходам; (3) `grep EnableKeyword` по коду против `#pragma` в
шейдере; (4) только теперь гипотезы про стриппер, API, порядок инициализации.
Чего НЕ делать: выключать `m_StripUnusedVariants` «на пробу» — первая сборка
уходит в 12+ минут и вешает редактор, а ключи это не лечит; ставить
самопроверки `Material.FindPass` раньше `AfterSceneLoad` — до подъёма SRP
SubShader с тегом `RenderPipeline` неподдержан, и проверка врёт «нет прохода».

## ⭐ Переписи: кто ведёт список своих (13.09)

Покадровая система НЕ перебирает уровень. Если ей нужно подмножество объектов,
у подмножества есть свой список, и он ведётся по времени жизни.

| Перепись | Кто ведёт | Кому нужна |
|---|---|---|
| `InteractiveObject.All` | сам объект, `OnEnable`/`OnDisable` | общий тикер, постановка, перенос |
| `InteractiveObject.Conducting` | `JoinDefLists` при постройке и включении | `TemperatureSim` |
| `InteractiveObject.Clad` | там же | `CladCuts.Sync` (врезка обшивки) |
| `CrowPerch.All` | `Awake`/`OnDestroy` ветки | поиск гнезда и цели у птиц |
| `CrowFlight.All` | `Awake`/`OnDestroy` рига | «занято ли место», «кто на дереве» |
| `InteractiveObject.Ticking` | `JoinDefLists` + конец `Build` | общий тикер (`WorldTick.Update`) |

⭐ **Признак, выводимый из ДЕФА, не спрашивают у каждого объекта каждый кадр.**
`Conducts` и `Seated` (врезка обшивки) считаются из полей дефа и за жизнь
объекта не меняются — значит место объекта в переписи известно при постройке.
Новая такая система заводит СВОЙ список в `InteractiveObject.JoinDefLists`, а
не новый перебор уровня. На forest100 (7760 объектов) каждый такой перебор
стоил 0.45–0.5 мс кадра при НУЛЕ подходящих объектов.

## ⭐⭐ ПОЧЕМУ перепись выигрывает: платим не за проверку, а за КАСАНИЕ

Замер 13.09, три независимых подтверждения — один и тот же множитель ×4…×10
между «тем же кодом в тесном цикле» и «тем же кодом в кадре»:

| Что | В тесном цикле | В кадре | Объектов |
|---|---|---|---|
| отбор в `InteractiveObject.TickAll` | 0.068 мс | 0.649 мс | 7760 |
| тело `CrownWindow.Wake` | 0.106 мс | 0.427 мс | 710 |
| чтение `Renderer.bounds` | 32 нс | — | — |

Разгадка простая: в тесном цикле данные уже в кэше, а в кадре каждый объект
надо ТРОНУТЬ холодным — и это десятки наносекунд на объект, что бы ты с ним
дальше ни делал. Отсюда три следствия, которые стоит помнить раньше, чем
начинать оптимизировать:

1. **Удешевлять проверку почти бесполезно.** Гейт «нечего тикать» снял только
   четверть цены `TickAll`; всё остальное ушло, когда обход стал ходить по
   переписи из нуля объектов вместо уровня из 7760 (0.649 → 0.050 мс).
2. **Данные, которые нужны каждый кадр, должны лежать ПОДРЯД.** У полосы каймы
   центр, радиус и «включена ли» переехали в саму структуру `Band`, и четыре
   прохода по 710 полосам перестали заходить в движок: 0.427 → 0.165 мс.
3. **Мерить надо в кадре, а не в цикле.** Бенчмарк в `execute_code` покажет
   красивое число и уведёт не туда; правду говорит `gc_probe.py profile`.

⚠️ **Перепись по времени жизни, а не по включённости**, если объект может быть
погашен визуально: радиус рендера (`FarRadius`) гасит рендереры через
`forceRenderingOff` и НЕ выключает GameObject, но компонент-ветка выключается
сама, когда она не нужна (`enabled = On`) — её перепись поэтому ведётся из
`Awake`/`OnDestroy`, иначе далёкие ветки пропадали бы из поиска.

## Общее для монстров, стычек и эффектов (2026-09-16, ночной рефакторинг)

Три слоя — существа, сцены стычки, эффекты игрока — тянутся к одному и тому же:
к игроку, к камере и к настройкам, которые Илья крутит в дебаге. Раньше каждый
тянулся по-своему; теперь на каждое есть одно место.

| Что | Где | Что заменило |
|---|---|---|
| «Что сейчас можно сделать с игроком» | `Cozy.Character.PlayerTarget` | пять разных наборов условий: монстр проверял смерть, полёт наблюдателя и шкаф, ворона — только смерть, повтор атаки — только занятость сценой |
| Игрок, его статы, модель, голова, стопы | там же (`Stats`, `Visual`, `Head`, `Feet`) | четыре одинаковых `GetComponentInChildren<Animator>()` и три своих кеша `CharacterStats`; ночью 16.09 — ещё восемь: панель статов, экран персонажа, всплывашки над головой, дебаг «Игрок»/«Вид», тело (`BodyTemperature`), эффекты среды (`PlayerExposure`), смерть и доводка корня в `Encounter`. Свой поиск остался только у самого игрока (`PlayerMovement`) и в `Cozy.Grid` (`CrownWindow`, `SleepFeature`) — Grid ниже Character и `PlayerTarget` не видит |
| Камера на орбите вокруг точки | `Cozy.Character.CameraOrbit` | та же тригонометрия, написанная пять раз (поза камеры сцены, подбор углов по текущей, два умолчания из данных, камера осмотра) |
| Всё про сцену стычки | граф `EncounterGraph` (`CrowEncounter.Graph`, с 17.09; до этого таблица `CrowEncounter.Scenes`) | восемь цепочек `scene == ...`, пять классов эффектов, четыре класса камер и `switch` в `CrowAttack.Tune` |
| Настройки дебага у объектов | `DebugTune` + `Tunables()` | таблица сохранения принимала только СТАТИЧЕСКИЕ классы, из-за чего копипаста классов и жила |

**Граф и актёр (ночь 17→18.09, ilya-15).** Таблица сцен стала объектом
`EncounterGraph` (строки `EncounterScene`; варианты, таймаут, цена, проверка,
`Death`/`Slip` у сцены 1 постановки, гибель по остатку, бросок, `Tunables()`),
у вороны — `CrowEncounter.Graph`, а `CrowEncounter` остался фасадом с прежними
статиками для UI, дебага и проб. Раннер `Encounter` держит граф полем и
получает его от погони явно (`Begin(graph, …)`). Воронье про показ сцены —
поза по треку узлов, крылья, карканье, поправка высоты — в `CrowActor`
(`Encounter.Show.cs`); раннер знает у актёра только `Position`, `Alive`,
`SceneStarts()`, `Drive(scene, t, рамка)`. Второй монстр заводит свой граф и
своего актёра; общий базовый тип актёров появится вместе со вторым, не раньше.
Что осталось приварено к вороне — `tavern-combat/COMBAT.md`, «Как сейчас».

**Как теперь заводится новая сцена стычки.** Одна строка `EncounterScene` в `CrowEncounter.Graph`:
идентификатор, варианты выбора, таймаут, урон (`SceneHarm`), камера
(`CrowAttack.SceneCam`) и флаги. Классов заводить не нужно, в таблицу сохранения
дебага дописывать нечего — сцена попадает туда сама через `Tunables()`. Ключ
настроек — имя сцены с большой буквы («GuardEffect», «Guard»), и это не
косметика: по этим ключам в `DebugTune.json` лежат уже настроенные Ильёй числа.

**Кто кого знает.** Бой НЕ знает про UI: он объявляет, что списал
(`CrowEncounter.Spent`), а всплывашки статов слушают. Раньше UI каждый кадр
спрашивал «какая сейчас сцена» и сам лез в правила боя за её эффектом.

**Разделение `Encounter`.** Машина сцен (`Encounter.cs`) — какая сцена идёт и
когда кончится; показ (`Encounter.Show.cs`) — поза птицы, ход камеры, перемотка
клипа; возврат игрока (`Encounter.Recovery.cs`) — поза «упал», подъём, передача
управления. Правят их обычно по отдельности, и раньше они лежали в одном файле
на 458 строк.

## Ночь 01.10 (ilya-ca): два правила к общим примитивам

- `RayPick.Sorted/Down`: полный буфер `NonAlloc` = переполнение — хиты перечитываются `RaycastAll`, в буфер идут ближайшие
  (`NearestOfAll`). Любой луч с фиксированным буфером — только через `RayPick` (P667, инвариант «луч с буфером»).
- `OwnedAssets.On(go).Track(asset)` обязателен для КАЖДОГО `new Mesh/Material/Texture2D` под экземпляр; внутри билдеров
  `ProceduralModels` — `_builtMats.Add(m)` (их подхватит `Make`). После `RestoreLevel` стоит `Resources.UnloadUnusedAssets()` —
  страховка от сирот прошлого уровня, но не замена владения (P669, P663).
- Результат `GetComponent*` не проверяют `??`/`?.` — только `TryGetComponent` (тест `SourceRulesTests`, P662).
