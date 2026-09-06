# Видео и девлог — пайплайн монтажа

Ролики для YouTube на английском; первый — приготовление рецепта как
вертикальный срез кухни (Илья 2026-09-02: «сам подход рабочий, запиши его
в скил»). Идея и вопросы к сценарию — `tavern-ideas/INBOX.md`.

## Что где

| Файл | Что |
|---|---|
| `/home/ilya/Documents/Fog/Videos/<номер>/` | ⭐ с 06.09 Илья кладёт дубли сюда, папкой на ролик, файлы `1.mp4`, `2.mp4`…; результат — `joined.mp4` там же. Раньше было `/home/ilya/Videos/` |
| `vokoscreenNG` | чем Илья пишет экран (имена `vokoscreenNG-<дата>_<время>.mp4`) |
| `ffmpeg 6.1.1`, `ffprobe` | `/usr/bin`, есть xfade, acrossfade, fade, subtitles, drawtext, zoompan, libx264, aac |
| OBS | установлен, пока не использовался |
| шрифт для титров | `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf` |

## Что даёт запись сейчас и что просить

vokoscreenNG пишет 1920×1080, 25 fps, h264 Constrained Baseline yuv420p,
mp3 44.1 кГц, около 0,5 Мбит — картинка мягкая. Голос и звук игры в одной
дорожке, пики голоса упирались в 0 дБ.

Для настоящих дублей: 60 fps, битрейт 20–30 Мбит или CRF 18, aac, микрофон
на 6–10 дБ тише (громкость поднимается на монтаже), голос и игра раздельно,
если рекордер умеет. Интерфейс игры на английском (`Loc.Set(En)`), в кадре
должно что-то происходить: голос проще писать отдельно поверх смонтированного
видео, чем играть и говорить одновременно.

## Порядок работы

1. Илья кладёт дубли в `/home/ilya/Documents/Fog/Videos/<номер>` — папка на
   ролик, файлы пронумерованы по порядку съёмки.
2. Claude снимает паспорт (`ffprobe`), раскадровку, спектрограмму звука и
   меру движения — так видно, что в дубле: речь или тишина, действие или
   статичный план. Кадры смотреть через Read по PNG.
3. Черновая склейка одной командой (ниже), проверка `pix_fmt`/профиля и
   кадров перехода, файл в ту же папку.
4. Правки по кругу: переход, тайминг, титры, субтитры, музыка.

## Рецепты ffmpeg

Паспорт файла:

```bash
ffprobe -v error -show_entries format=duration,size:stream=codec_name,profile,pix_fmt,width,height,r_frame_rate,sample_rate,channels -of csv=p=0 in.mp4
```

Раскадровка 12 кадров плиткой 4×3 (длительность подставить):

```bash
ffmpeg -y -i in.mp4 -vf "fps=12/DUR,scale=480:-1,tile=4x3" -frames:v 1 sheet.png
```

Спектрограмма (речь — полосы ниже 4 кГц с паузами) и мера движения
(средняя разность кадров; ~0,005 значит статичный план):

```bash
ffmpeg -y -i in.mp4 -lavfi "showspectrumpic=s=1200x300:legend=1" spec.png
ffmpeg -i in.mp4 -vf "tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG" -f null - 2>&1 | grep -o 'YAVG=[0-9.]*'
```

Склейка двух дублей с секундным переходом. `OFF` = длина A минус длительность
перехода. `fadeblack` — затухание в чёрное и появление (Илья выбрал его);
`fade` — растворение одного плана в другой. Звук перетекает через
`acrossfade` за ту же секунду. Оба входа приводятся к одному fps и одному
формату звука, иначе фильтры не стыкуются.

```bash
ffmpeg -y -i A.mp4 -i B.mp4 -filter_complex \
 "[0:v]fps=25,setpts=PTS-STARTPTS[v0];[1:v]fps=25,setpts=PTS-STARTPTS[v1];\
  [v0][v1]xfade=transition=fadeblack:duration=1:offset=OFF,format=yuv420p[v];\
  [0:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[a0];\
  [1:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[a1];\
  [a0][a1]acrossfade=d=1:c1=tri:c2=tri[a]" \
 -map "[v]" -map "[a]" -c:v libx264 -pix_fmt yuv420p -profile:v high -level 4.0 \
 -preset medium -crf 18 -c:a aac -b:a 192k -movflags +faststart joined.mp4
```

⭐ `format=yuv420p` ПОСЛЕ xfade и `-pix_fmt yuv420p -profile:v high` — обязательны.
Без них xfade договаривается о yuv444p, libx264 пишет профиль High 4:4:4, и
плеер показывает чёрный экран или «нет видео» (P156). Проверка после каждой
склейки: `ffprobe … pix_fmt` должен вернуть `yuv420p`, профиль `High`.

Проверка перехода по кадрам (номер кадра = секунда × fps):

```bash
ffmpeg -y -i joined.mp4 -vf "select='eq(n\,730)+eq(n\,745)+eq(n\,751)+eq(n\,770)',scale=480:-1,tile=4x1" -vsync vfr -frames:v 1 check.png
```

Проверено 2026-09-02: два дубля по 30 и 41 секунде, `fadeblack` на 29,5–30,5 с,
результат 70,9 с, 6 МБ, играет у Ильи.

### Цепочка из N дублей (2026-09-06)

Для трёх и более дублей смещения считаются накоплением, руками не набирать —
сгенерировать. Смещение k-го перехода = (длина склейки до него) − D, где длина
после каждого перехода растёт на длительность нового дубля минус D. Итоговая
длина = сумма длительностей − D × (число переходов).

```python
acc = durs[0]; vprev, aprev = 'v0', 'a0'
for i in range(1, len(names)):
    parts.append('[%s][v%d]xfade=transition=fadeblack:duration=%g:offset=%.6f[vx%d]' % (vprev, i, D, acc - D, i))
    parts.append('[%s][a%d]acrossfade=d=%g:c1=tri:c2=tri[ax%d]' % (aprev, i, D, i))
    acc += durs[i] - D
    vprev, aprev = 'vx%d' % i, 'ax%d' % i
parts.append('[%s]format=yuv420p[v]' % vprev)
```

Каждый вход перед этим приводится к общему виду:
`[i:v]fps=30,setpts=PTS-STARTPTS[vi]` и
`[i:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[ai]`.

**Проверять переход не по номерам кадров, а сканом яркости.** Скан находит все
провалы разом и не зависит от арифметики:

```bash
ffmpeg -hide_banner -loglevel info -i joined.mp4 \
  -vf "fps=10,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-" -f null - 2>/dev/null \
  | paste - - | awk '{split($3,a,":"); split($4,b,"="); printf "%.1f %.1f\n", a[2], b[2]}' \
  | awk '$2 < 12'
```

Должно найтись ровно столько тёмных моментов, сколько переходов. У `fadeblack`
картинка гаснет БЫСТРЕЕ, чем разгорается, поэтому самый тёмный кадр стоит не в
середине секунды, а примерно на её трети — это норма, а не сбитое смещение.

⚠️ **`-ss` ПЕРЕД `-i` для таких замеров не годится**: это быстрый поиск по
опорным кадрам, и время в выводе поедет — «переход» найдётся не там, где он
есть. Мерить полным сканом (как выше) или `-ss` ПОСЛЕ `-i`.

⚠️ **Звук короче видео — это из записи, а не из склейки.** У дублей
vokoscreenNG звуковая дорожка на 47–67 мс короче видеодорожки; в склейке
разницы складываются (на семи дублях 0,4 с). Тишина в самом хвосте, лечить
нечего.

Проверено 2026-09-06: семь дублей (28,3 + 46,8 + 16,0 + 23,4 + 46,1 + 38,4 +
39,9 с) склеены шестью переходами по секунде, результат 232,8 с, 37 МБ,
`yuv420p`/High, скан яркости нашёл ровно шесть провалов (2,3–6,6 из 255) на
27,5 / 73,3 / 88,2 / 110,6 / 155,7 / 193,1 с. Кодирование 19 секунд.

## Что дальше по инструментам (не делалось)

Субтитры — `subtitles=file.srt` (или `.ass`), титры — `drawtext`, музыка
под голос — `amix` с `volume`, ускорение скучных мест — `setpts=PTS/2` +
`atempo`, наезд — `zoompan`. Сценарий с таймингом и английские субтитры
пишутся до записи.
