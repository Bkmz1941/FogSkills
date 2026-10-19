# Каталог: всё, что существует по персонажам (сверено 16.10)

Пометки: **игра** — в `Assets/Game/Resources`; **Blender** — только в `BlenderWork`, ждёт слова «переноси».

## 1. Люди и их модели

| Кто | Модель | Где | Статус |
|---|---|---|---|
| Герой-парень (Илья) | тело `HumanCharacterDummy_M_Skin` + бельё + вещи по слотам | `Models/`, `Clothes/*M` | игра; источник формы — `Library/humanSkin.blend`, вещи — `Library/humanClothes.blend` |
| Героиня-девушка (Анна) | `HumanCharacterDummy_F_Skin` + `UnderwearF` + вещи `*F`, волосы `HairF` | `Models/`, `Clothes/*F` | игра; сборка `human_girl_build.py` → `Library/humanGirl.blend` |
| Сектант (брат Тихон / Степан Гуляев) | тело героя + балахон `RobeM` | `Library/sectant.blend`, `Library/sectantRobes.blend` | игра (фигура, клипы, стычка); скил `tavern-sectant` |
| Зомби (новый монстр, 17.10) | тело героя М, `TShirtM` грязно-серая, `JeansM` выцветшие, `SneakersGreyM` грязные, короткие тёмные волосы | `zombie_build.py` + `zombie_params.json` → `Library/zombie.blend` | Blender: Т-поза, стойка `Zombie_Idle` (Idle01 ×1,4, 113 кадров: голова вниз 24°, плечи опущены, руки висят) и ходьба `Zombie_Walk` (Walk_Calm 2 цикла ×2,0, 216 кадров: голова вниз 20°, мах рук 0,15, бесцельное покачивание головы, дрожь как у сектанта) — слой `sectant_build.creep_action` со своими числами; лупы на месте |
| Тень | тело героя + `RobeM`, шейдер-силуэт на стене | `ShadowMonster` | игра; `tavern-monsters` |
| Андрей Соколов, 29 (пропал 02.08.2026) | тело М ×1,06, `TShirtM` оливковая, `JeansM` тёмные, `SneakersGreyM`, короткие волосы, борода | `missing_people_build.py` → `Library/missingPeople.blend` | Blender (16.10) |
| Ирина Соколова, 27 | тело F, `TShirtF`, `JeansF`, `SneakersF`, каре блонд, круглые очки | там же | Blender (16.10) |
| Остальные пропавшие (Лиза Котова, Миша Ершов, Артём Гусев 12, Ковалёва, Гуляев…) | — | приметы и одежда — `BlenderWork/missing_tex/missing_posters.html` (`PEOPLE`) | нет; новый — запись в `missing_people_params.json`; детского тела нет |
| Полицейский и полицейская (форма, без имени) | тела М и Ж игровые; рубашка голубая (стойка с отложным листом, планка, 7 пуговиц, нагрудные карманы с клапанами, погоны), галстук чёрный (узел + лопасть по рубашке), брюки тёмно-синие со стрелками и чёрным ремнём с пряжкой, куртка тёмная нараспашку (подол на бёдрах, манжеты, клапаны карманов, отложной воротник, жёлтый значок слева на груди, «ПОЛИЦИЯ» на спине), `SneakersM/F` в чёрном, волосы генератором | `police_build.py` + `police_params.json` → `Library/police.blend` | Blender (17.10): на каждый пол Т-поза, стойка, походка (у Ж слой `girl_motion`), стойка без куртки; вещи вырезаны из тела полями `human_girl_build.shell/garment`; у Ж таз тела закрыт `SportBriefs` (у игрового тела F там дыра 0,81–0,99 м); меши тяжёлые в сцене (рубашка ~47 тыс. вершин, `fine=1`), в игру уходят прорежёнными. ⭐ 17.10 ПЕРЕНЕСЕНО в игру (`-- export`): 8 предметов `police_*`, ботинки вместо кроссовок, сложенные вещи и пары, иконки `-- icons` — `tavern-clothes/CLOTHES.md`, каталог |
| Аня, Дима, Морин, родители | ⭐ 17.10 есть фигуры (см. строку ниже); родителей нет | `tavern-level1`, `tavern-roleplay` | — |
| ⭐ ВСЕ 25 из `People.Roster` (герои, Морин, Сазоновы, стражи, Савва, Степан, пропавшие, полиция 911) | тело М/Ж + игровые вещи с перекраской + причёска генератором + борода/очки | `missing_people_params.json` → `Library/missingPeople.blend`; в игре статуи `Resources/People/person<Tag>.fbx`, деф `person_<Tag>` (`FurnitureCatalog.Person`), F6 → Строительство → Персонажи → «Поставить» | игра (17.10), статуя в позе покоя, без анимации |

Выбор модели героя в игре — `PlayerModelCatalog` (`dummy_skin`, `girl_skin`), свои клипы — override-контроллеры
`Assets/Game/Data/Player/Resources/`: `PlayerAvatar.controller` (база), `PlayerAvatarGirl.overrideController`,
`SectantAvatar.overrideController`.

## 2. Тела и скелет

| | |
|---|---|
| скелет | KI, 56 костей `B-*` (`B-hips`, `B-chest`, `B-neck`, `B-head`, `B-jaw`, руки `B-upperArm/forearm/hand.L/R`, пальцы, ноги `B-thigh/shin/foot/toe`), Humanoid в Unity |
| игровые тела | `Models/HumanCharacterDummy_M_Skin.fbx` (10 002 в., макушка 1,831), `…_F_Skin.fbx` (10 124 в., макушка 1,776), `…_M_Low.fbx`; центр головы М (0, −0,028, 1,725), F (0, −0,034, 1,675) |
| рабочие тела Blender | `Library/humanSkin.blend` (парень, источник — НЕ трогать), `Library/humanGirl.blend` (девушка, собирается скриптом) |
| кожа под одеждой | в файлах сектанта и пропавших не маскируется по-игровому; у сектанта маска `SkinVisible` (`tavern-sectant`) |

## 3. Одежда

**В игре** (`Resources/Clothes`, носится по слотам, `tavern-clothes/CLOTHES.md`):
- полицейская форма (17.10, М и Ж): `PoliceShirt{M,F}` (с галстуком), `PoliceTrousers{M,F}`, `PoliceJacket{M,F}` (Outer), `PoliceShoes{M,F}` (ботинки);
- парень: `TShirtM` (белая), `TShirtBeigeM`, `TShirtRedM`, `TurtleneckM`, `HoodieM`, `JacketM`, `JeansM` (с ремнём),
  `HomePantsM`, `SneakersM`, `SneakersGreyM`, `SlippersM`, `UnderwearM`, `RobeM` (балахон), `HairM`;
- девушка: `TShirtF`, `HoodieF`, `JeansF`, `SneakersF`, `UnderwearF`, `HairF`;
- носимое: `BackpackM/F`, `BackpackHoodieM/F`, `BackpackJacketM`, `BriefcaseM/F` (+Hoodie/Jacket), `SportBagM/F`
  (+Hoodie/Jacket/Shirt) — посадка под верх;
- вещи «как лежит» (мир): `Furniture/jeansFolded`, `homeFolded`, `tshirt*Folded`, `sneakersPair*`, `slippersPair`,
  `jeansGirlFolded`, `tshirtGirlFolded`; очки Ирины — предмет `glasses_sokolova` (не носится).

**Только Blender** (ночь 01.10, ждут слова, `tavern-game/BLENDER.md` «Ночь 01.10»): `Library/humanBoots`, `humanCargo`,
`humanFlannel`, `humanLongsleeve`, `humanRaincoat`, `humanShorts`, `humanSweater`, `humanSweatpants`, `humanTank`, `humanVest`,
`humanJacket` (показ куртки), `humanBag`, `humanSportBackpackM`; очки носимые `GlassesM_*` в `Library/glasses.blend`.

## 4. Волосы и лицо

| | |
|---|---|
| генератор | `BlenderWork/hair_scene.py` → `Library/humanHair.blend` (мастерская: `Hair01` герой, `HairS04` пробор набок, `HairS09` растрёпанные, `HairF01` девушка); функции берутся exec'ом с `build: False` |
| в игре | `Clothes/HairM`, `Clothes/HairF` |
| пропавшие | Андрей — короткие (форма героя, scale 0,95), Ирина — каре (стиль девушки, низ 1,585–1,625), цвета `HAIR_HEX` |
| борода | `missing_people_build.beard` — сетка лучами по плавным границам, тоньше к краю |
| очки | `GlassesM_*` с героя, пересадка на голову фигуры (`missing_people_build.glasses`) |
| ⚠️ | генератор не собирает девушку одиночным лучом — P1094, повтор луча со сдвигом |

## 5. Клипы — в игре (`Resources/*.fbx`, Humanoid)

| Группа | Клипы |
|---|---|
| движение героя | `Idle_Calm`, `Walk_Calm`, `Jog_Calm`, `Run_Winded`, `Run_Winded_F`, `Walk_Limp`, `Walk_Drunk`, `Crouch_Down/Idle/Walk`; девушка — `Girl_Idle/Walk/Run` |
| позы | `Sit_Idle`, `Sit_Idle_Lap`, `Sit_Rocking`, `Sit_Sofa`, `Lie_Idle`, `Lie_Sofa`, `Bath_Lie`, `Kneel_Down/Pray/Pray_Shake/Up` |
| перелазы | `Window_Climb/Fall`, `Rail_Climb/Fall`, `Ladder_Climb` |
| трупы (17.10) | `Corpse_back_spread/back_chest/prone_head_side/prone_crawl/side_curled/side_sprawl/back_twisted/sit_wall/sit_tree/hanged` — объект уровня «Труп мужчины/женщины» (`corpse_<поза>_<m|f>`), редактор → Модели → «Смерти», муж/жен, поза листается кнопкой «Поза»; тело героя/героини в трусах, клип одной позой (`CorpsePose`, `NpcDummy.cs`), у повешенного верёвка с петлёй по `corpseHanged.json`; сцена `corpse_poses.py` |
| состояния | `Sit_Fallen`, `Stand_Up`, `Prone_Fallen`, `Prone_Up`, `Poison_Retch/Fours/Death`, `Bleed_Death`, `Trap_Hit/Pain/Open`, `Throw_Right` |
| стычка с вороной | `Crow_Brace/Guard/Dodge/Hit/Fall/Melee/Punch/Slip`, сзади `Crow_Back/BackDodge/BackHit/BackSlip` |
| стычка с сектантом | герой `Hero_SectantBrace/Hit/Dodge/Kill/Guard/Melee/Punch`; сектант `Sectant_Attack/Strike/Miss/Kill/Grapple/Struck/Punched` |
| сектант | `Sectant_Walk`, `Sectant_PointRise/PointHold`, `Sectant_CandleWalk/CandleStand` |
| пистолет (двумя руками, 17.10) | `Hero_PistolAim` (целится, оглядывается ±40°, 10,1 с), `Hero_PistolIdle` (держит опущенным), `Hero_PistolWalk` (идёт наготове, темп Walk_Calm) — луп, сцена `Animations/Pistol_Hold.blend`, `pistol_hold_scene.py [-- export]`; пистолета-предмета в игре нет, клипы — в превью F1 «Анимации» |
| прочие существа | `Shadow_Idle`, `Monster_Hammer/Pound/Ram` (от удалённого безумца) |

Сцены клипов — `BlenderWork/Animations/<клип>.blend`, сборка — `anim_kit.py`, `crow_fight.py`, `sectant_*.py`.

## 6. Клипы — только Blender (`BlenderWork/Animations/`, ждут слова)

`Sectant_Death` (смерть + `Sectant_Dead`, форма ткани «лёжа», 16.10), `Axe_Hold` (топор в двух руках стоя и на ходу — `Hero_AxeIdle`/`Hero_AxeWalk`, эталон хвата, `axe_hold_scene.py`, 16.10), `Drunk_Fall`, `Drunk_Sleep`, `Car_Enter`, `Car_Exit`,
`Phone_Raise`, `Idle_Live`, `Model_Poses`, `Base_Poses`, `Bend_Poses` (эталоны сгибов), `Stun_Stars` (эффект),
`Sectant_Head_Icons` (значки над головой), `Crow_Fight/Window/WindowDrop` (ворона). Файлы `Sectant_Hit/Dodge/Guard/Melee/
Punch/Point/Candle/Back` — сцены, из которых выгружены игровые клипы сектанта (имена клипов другие, см. §5).

## 7. Файлы и сборки (быстрый ответ)

| Что | Команда |
|---|---|
| полицейские | `blender -b --factory-startup --python BlenderWork/police_build.py` (~4 мин); окно `bash BlenderWork/blender_mcp_up.sh Library/police.blend` |
| пропавшие | `blender -b --factory-startup --python BlenderWork/missing_people_build.py`; окно `bash BlenderWork/blender_mcp_up.sh Library/missingPeople.blend` |
| девушка | `blender -b --factory-startup -P BlenderWork/human_girl_build.py [-- casual|body|export]` |
| волосы | `blender -b --python BlenderWork/hair_scene.py [-- export]` |
| сектант | `sectant_build.py`, `sectant_robes_build.py`, сцены `sectant_*.py` (скил `tavern-sectant`) |
| вещь героя в игру | `human_skin_garment_export.py -- <Имя>` (скил `tavern-clothes`) |
| клип в игру | `-- export` своей сцены; мета — копия соседней (Humanoid, `CopyFromOther`), длина = `frame_end` (P769) |
