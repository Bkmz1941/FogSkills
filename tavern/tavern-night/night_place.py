"""Мебель на ночном уровне через НАСТОЯЩИЙ пайплайн постановки (в play): для каждой записи плана
камера доворачивается так, чтобы луч через реальный курсор прошёл в нужную точку (сдвиги курсора сквозь стену,
дверь или окно пропускаются — 27.09: раковина «переезжала» в коридор), зовётся
`GridCursor.ComputeObjectPose` → при «ок и не блок» — `SpawnPlaced` + `SpawnCompanions` +
`FitWidthToWallLike`, как по клику. Что вышло — строкой: id|метка|ok|блок|поза|yaw|bounds|носитель.

python3 night_place.py plan                 показать план (этажи, записи)
python3 night_place.py floor <N> [--dry]    поставить мебель этажа N (игрок телепортируется на этаж)
python3 night_place.py all [--dry]          все этажи подряд и сохранить уровень
python3 night_place.py save                 LevelIO.Save(текущий уровень)
python3 night_place.py clear <N>            снести объекты этажа N (кроме маркера спавна)
--plan b                                   план дома B (night_level.py --layout b); save/all сохраняют ТОЛЬКО night_build*

Запись плана: (id, x, z, yaw, вид, метка), вид ∈ floor | wall:<h> | surf:<h> | shelf:<h> | ceil (shelf — крутой луч спереди на верх полки стеллажа, h = верх полки + 2 см). Луч для floor/surf/ceil
идёт почти отвесно через (x, z); для wall — от комнаты к стене на высоте h (yaw = куда смотрит СПИНА:
0 → +Z, 90 → +X, 180 → −Z, 270 → −X; для стены луч летит в сторону спины).
"""
import json, pathlib, subprocess, sys, time

MCP = str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
CS = 3.0


def run(code):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})],
                         capture_output=True, text=True, timeout=600, cwd=PROJECT)
    text = out.stdout.strip()
    line = text.splitlines()[-1] if text else '{}'
    try:
        d = json.loads(line)
        r = (d.get('data') or {}).get('result')
        return r if r is not None else json.dumps(d, ensure_ascii=False)[:2000]
    except Exception:
        return text[-2000:]


# ---------------------------------------------------------------- план: дом 4×3, клетки x −6/−3/0/3, z −6/−3/0
X = [-6.0, -3.0, 0.0, 3.0]
Z = [-6.0, -3.0, 0.0]
W, E, S, N = -7.5, 4.5, -7.5, 1.5   # наружные плоскости стен

PLAN = {
    0: [
        # прихожая (x −7.5..−1.5, z −4.5..1.5)
        ('hallway_rack', -6.8, 0.5, 270, 'floor', 'спиной к западной стене'),
        ('home_hall_mirror', W, -2.5, 270, 'wall:1.45', 'зеркало на западной стене'),
        ('pipe_valve', -6.9, 1.1, 0, 'floor', 'стояк в СЗ углу'),
        ('cardboard_box', -3.6, -1.0, 30, 'floor', 'коробка свободно'),
        ('cardboard_box', -2.9, -0.2, 15, 'floor', 'вторая коробка'),
        ('sneakers_pair_grey', -6.3, -0.6, 0, 'floor', 'кроссовки у вешалки'),
        ('meter_electric', -1.5, 0.3, 90, 'wall:1.6', 'счётчик на внутренней стене'),
        ('wall_switch', -1.5, -1.7, 90, 'wall:1.35', 'выключатель у двери'),
        ('home_painting_1', -1.5, -0.6, 90, 'wall:1.85', 'картина над выключателем'),
        ('lamp_ceiling_modern', -4.5, -1.5, 90, 'ceil', 'лампа прихожей'),
        # кухня-гостиная (x −1.5..4.5, z −7.5..1.5)
        ('home_sink_cabinet_corner', 3.2, -0.5, 90, 'floor', 'угловая тумба в СВ углу'),
        ('home_fridge', 3.8, -3.3, 90, 'floor', 'холодильник в линию'),
        ('home_stove', 3.8, -4.8, 90, 'floor', 'плита в линию'),
        ('home_wall_cabinet_corner_wide', E, -0.5, 90, 'wall:1.8', 'навесной угловой над тумбой'),
        ('home_under_light_corner_wide', 4.2, -0.5, 90, 'wall:1.85', 'подсветка под шкаф'),
        ('home_sink', 3.9, -0.5, 90, 'surf:1.15', 'мойка на тумбу'),
        ('table_round', 0.0, -3.0, 90, 'floor', 'стол в центре'),
        ('home_kitchen_chair', 0.0, -4.4, 180, 'floor', 'стул с юга'),
        ('home_kitchen_chair', 0.0, -1.6, 0, 'floor', 'стул с севера'),
        ('home_kitchen_chair', 1.4, -3.0, 90, 'floor', 'стул с востока'),
        ('home_rug_1', -0.2, -3.0, 90, 'floor', 'ковёр под столом'),
        ('fruit_bowl', 0.0, -3.0, 0, 'surf:0.75', 'миска на столе'),
        ('apple', 0.0, -3.0, 0, 'surf:0.95', 'яблоко в миску'),
        ('apple_green', 0.05, -2.95, 0, 'surf:0.95', 'зелёное в миску'),
        ('apple_green', -0.05, -3.05, 0, 'surf:0.95', 'второе в миску'),
        ('plate', 0.55, -3.45, 0, 'surf:0.75', 'тарелка на столе'),
        ('coffee_cup_red', -0.5, -2.55, 30, 'surf:0.75', 'кружка на столе'),
        ('coffee_cup_blue', 2.5, 1.0, 90, 'surf:1.15', 'кружка на столешнице'),
        ('coffee_cup_yellow', 2.8, 1.1, 75, 'surf:1.15', 'вторая кружка'),
        ('cooking_pot', 3.9, 0.6, 210, 'surf:1.15', 'кастрюля на столешнице'),
        ('frying_pan', 3.48, -4.55, 270, 'surf:1.16', 'сковорода на конфорку 1'),
        ('home_coffee_machine', 3.7, -1.7, 345, 'surf:1.15', 'кофемашина на столешнице'),
        ('coffee_tank', 3.7, -1.5, 345, 'surf:1.2', 'бак к кофемашине'),
        ('coffee_carafe', 3.7, -1.9, 345, 'surf:1.2', 'кувшин к кофемашине'),
        ('coffee_pack', 3.9, -1.2, 135, 'surf:1.9', 'кофе в навесной'),
        ('water_bottle', 2.6, -6.5, 0, 'floor', 'бутылка на полу'),
        ('water_bottle', 2.9, -6.2, 0, 'floor', 'вторая бутылка'),
        ('home_radiator', 3.0, -7.0, 180, 'floor', 'батарея под южным окном'),
        ('wall_switch_toggle', -1.5, -1.7, 270, 'wall:1.35', 'тумблер с кухонной стороны'),
        ('home_painting_2', -1.5, 0.5, 270, 'wall:1.85', 'картина на внутренней стене'),
        ('lamp_ceiling_modern', 1.5, -4.5, 90, 'ceil', 'лампа кухни'),
        ('lamp_ceiling_modern', 1.5, 0.0, 90, 'ceil', 'лампа над столешницей'),
        ('ketchup', 2.2, 1.1, 210, 'surf:1.15', 'кетчуп на столешнице'),
        ('oil_bottle', 2.0, 1.2, 210, 'surf:1.15', 'масло на столешнице'),
        ('sponge', 4.05, 0.55, 210, 'surf:1.15', 'губка у мойки'),
    ],
    1: [
        # ванная (x −7.5..−1.5, z −1.5..1.5), дверь на z=−1.5 при x=−3 (клетка i=1)
        ('home_bath', -5.3, 0.6, 0, 'floor', 'ванна вдоль северной стены (4,1 м)'),
        ('home_toilet', -7.0, -0.7, 270, 'floor', 'унитаз у западной стены'),
        ('home_bathroom_sink', -2.0, 0.3, 90, 'floor', 'раковина спиной к восточной стене ванной'),
        ('home_bathroom_mirror', -1.5, 0.3, 90, 'wall:1.57', 'зеркало над раковиной'),
        ('home_washer', -5.2, -0.8, 180, 'floor', 'стиралка у южной стены (глухой сегмент i=0)'),
        ('bath_shelf', W, -0.7, 270, 'wall:1.7', 'полка над унитазом'),
        ('bath_paper_holder', -6.9, S + 6.0, 180, 'wall:0.95', 'держатель у унитаза на южной стене'),
        ('sponge', -2.0, 0.3, 90, 'surf:1.1', 'губка на раковину'),
        ('wall_switch', -1.5, -1.2, 90, 'wall:1.35', 'выключатель ванной на восточной стене'),
        ('lamp_ceiling_modern', -4.5, 0.0, 90, 'ceil', 'лампа ванной'),
        # спальня (x −1.5..4.5, z −7.5..−1.5) + лестница в (2..3, 2)
        ('home_bed', 1.5, -6.4, 180, 'floor', 'кровать спиной к южной стене (plinthStop)'),
        ('home_wardrobe_room', 4.0, -6.0, 90, 'floor', 'шкаф спиной к восточной стене (plinthStop)'),
        ('home_shelving', -1.1, -6.0, 270, 'floor', 'стеллаж спиной к внутренней стене'),
        ('home_desk_clock_1', -1.1, -6.0, 270, 'surf:1.3', 'будильник на стеллаж'),
        ('home_painting_1', 1.5, S, 180, 'wall:1.85', 'картина над кроватью'),
        ('home_rug_6', -0.3, -5.3, 0, 'floor', 'ковёр у кровати'),
        ('home_radiator', 4.1, -3.0, 90, 'floor', 'батарея под восточным окном'),
        ('tshirt_folded', 1.0, -6.0, 0, 'surf:0.75', 'футболка на кровать'),
        ('jeans_folded', 2.0, -6.0, 0, 'surf:0.75', 'джинсы на кровать'),
        ('sneakers_pair_grey', 3.0, -4.6, 90, 'floor', 'кроссовки у шкафа'),
        ('wall_switch', -1.5, -1.9, 270, 'wall:1.35', 'выключатель спальни'),
        ('lamp_ceiling_modern', 1.5, -4.5, 90, 'ceil', 'лампа спальни'),
        ('cardboard_box', -4.5, -2.6, 20, 'floor', 'коробка в прихожей'),
        ('home_plant_9', -1.1, -6.0, 0, 'surf:0.9', 'папоротник на стеллаж'),
    ],
    2: [
        # гостиная: запад (x −7.5..−1.5, z −4.5..1.5), восток (x −1.5..4.5, z −7.5..−1.5)
        ('sofa_corner_left', -6.4, -2.2, 270, 'floor', 'угловой диван спиной к западу'),
        ('home_tv_stand', -1.9, 0.0, 90, 'floor', 'столик под ТВ у стены-ограждения'),
        ('home_tv', -1.5, 0.0, 90, 'wall:1.5', 'телевизор над столиком (луч на центр, низ ≈ 0,9)'),
        ('home_tv_remote', -1.9, 0.3, 75, 'surf:0.55', 'пульт на столик'),
        ('home_desk_clock_1', -1.9, -0.5, 75, 'surf:0.55', 'будильник на столик'),
        ('home_fireplace', -4.5, 1.0, 0, 'floor', 'камин спиной к северу'),
        ('firewood_log', -4.5, 0.9, 180, 'surf:0.15', 'полено в топку'),
        ('firewood_log', -4.3, 0.9, 180, 'surf:0.15', 'второе полено'),
        ('firewood_split', -4.7, 0.9, 180, 'surf:0.15', 'колотое в топку'),
        ('matches', -4.5, 1.2, 135, 'surf:1.65', 'спички на полку камина'),
        ('home_rug_6', -4.3, -1.2, 90, 'floor', 'ковёр перед диваном'),
        ('home_plant_8', -2.4, -2.2, 180, 'floor', 'фикус у столика'),
        ('home_plant_3', -2.0, 0.9, 165, 'surf:0.55', 'герань на столик'),
        ('shelf_plank', E, -5.5, 90, 'wall:1.6', 'полка-планка на восточной стене'),
        ('shelf_plant', 4.2, -5.5, 75, 'surf:1.65', 'свисающий цветок на полку'),
        ('home_radiator', 4.1, -3.0, 90, 'floor', 'батарея под восточным окном'),
        ('home_shelving', 1.0, -7.1, 180, 'floor', 'стеллаж у южной стены'),
        ('home_painting_1', -0.5, S, 180, 'wall:1.85', 'картина на южной стене'),
        ('home_painting_2', 3.0, -1.5, 0, 'wall:1.85', 'картина на стене-ограждении'),
        ('cardboard_box', 2.5, -6.0, 40, 'floor', 'коробка'),
        ('wall_switch', 2.0, -1.5, 0, 'wall:1.35', 'выключатель на ограждении'),
        ('lamp_ceiling_modern', -4.5, -1.5, 90, 'ceil', 'лампа гостиной'),
        ('lamp_ceiling_modern', 1.5, -4.5, 90, 'ceil', 'лампа восточной половины'),
        ('coffee_cup_red', 2.0, -7.0, 30, 'surf:1.2', 'кружка на стеллаж'),
        ('water_bottle', 0.6, -6.9, 0, 'surf:0.45', 'бутылка на стеллаж'),
    ],
    3: [
        # спальня 2 (восток и центр), кладовка (0..1, 2) с дверью на z=−1.5 при x=−6
        ('home_bed', 0.5, -6.4, 180, 'floor', 'кровать к южной стене'),
        ('home_wardrobe_room', 4.0, -6.0, 90, 'floor', 'шкаф спиной к восточной стене (plinthStop)'),
        ('hallway_rack', -4.0, -2.0, 0, 'floor', 'вешалка спиной к стене кладовки'),
        ('home_hall_mirror', -1.5, -6.5, 270, 'wall:1.45', 'зеркало на стене-ограждении'),
        ('home_radiator', 4.1, -3.0, 90, 'floor', 'батарея под восточным окном'),
        ('home_rug_1', -4.5, -3.2, 0, 'floor', 'ковёр в прихожей'),
        ('cardboard_box', -6.5, 0.5, 10, 'floor', 'коробка в кладовке'),
        ('cardboard_box', -5.0, 0.8, 35, 'floor', 'вторая коробка'),
        ('cardboard_box', -6.5, 0.5, 5, 'surf:0.7', 'коробка на коробку'),
        ('home_shelving', -3.0, 1.1, 0, 'floor', 'стеллаж в кладовке'),
        ('jeans_folded', -3.0, 1.1, 0, 'shelf:0.72', 'джинсы на вторую полку'),
        ('tshirt_folded', -3.0, 1.1, 0, 'shelf:1.24', 'футболка на третью полку'),
        ('home_plant_9', -3.0, 1.1, 0, 'shelf:1.75', 'папоротник на четвёртую полку'),
        ('home_plant_8', 3.9, -1.9, 90, 'floor', 'фикус под восточным окном'),
        ('home_painting_2', -3.0, -1.5, 0, 'wall:1.85', 'картина на стене кладовки'),
        ('wall_switch', -5.0, -1.5, 0, 'wall:1.35', 'выключатель у двери кладовки'),
        ('lamp_ceiling_modern', -4.5, -3.0, 90, 'ceil', 'лампа прихожей'),
        ('lamp_ceiling_modern', 1.5, -4.5, 90, 'ceil', 'лампа спальни'),
        ('water_bottle', 2.5, -5.5, 0, 'floor', 'бутылка у кровати'),
        ('sneakers_pair_grey', -0.2, -4.5, 180, 'floor', 'кроссовки у кровати'),
    ],
    4: [
        # чердак: всё открыто, дырка лестницы в (2..3, 2) ограждена
        ('home_shelving', -7.0, -5.5, 270, 'floor', 'стеллаж у западной стены'),
        ('firewood_log', -5.0, -6.5, 20, 'floor', 'полено на полу'),
        ('firewood_log', -4.6, -6.2, 110, 'floor', 'второе полено'),
        ('firewood_split', -4.2, -6.6, 60, 'floor', 'колотое'),
        ('cardboard_box', -2.5, -6.5, 25, 'floor', 'коробка'),
        ('cardboard_box', 2.0, -6.0, 70, 'floor', 'коробка у окна'),
        ('home_plant_8', -7.0, 1.0, 0, 'floor', 'фикус в углу'),
        ('home_rug_6', -3.0, -1.0, 0, 'floor', 'ковёр'),
        ('home_kitchen_chair', 0.5, -4.5, 0, 'floor', 'стул'),
        ('home_tv_remote', -7.0, -5.5, 270, 'surf:0.9', 'пульт на стеллаж'),
        ('home_painting_1', N, -3.0, 0, 'wall:1.85', 'картина на северной стене'),
        ('lamp_ceiling_modern', -4.5, -1.5, 90, 'ceil', 'лампа чердака'),
        ('water_bottle', -2.0, 0.5, 0, 'floor', 'бутылка'),
    ],
}

# План дома B (night_level.py --layout b, 27.09): лестницы (3,2)→(2,2) на чётных, (0,0)→(1,0) на нечётных.
PLAN_B = {
    0: [
        ('home_sink_cabinet_corner', -6.8, -6.8, 180, 'floor', 'угловая тумба в ЮЗ углу'),
        ('home_kitchen_counter', -4.6, -6.9, 180, 'floor', 'столешница в линию под окном'),
        ('home_stove', -3.5, -6.9, 180, 'floor', 'плита в линию под окном'),
        ('home_fridge', -2.1, -6.8, 180, 'floor', 'холодильник в линию под окном (OPEN)'),
        ('home_wall_cabinet', W, -5.8, 270, 'wall:1.9', 'навесной на западной стене'),
        ('home_sink', -7.0, -7.0, 180, 'surf:1.15', 'мойка на угловую тумбу'),
        ('cooking_pot', -4.6, -6.9, 180, 'surf:1.15', 'кастрюля на столешницу'),
        ('table_round', -3.0, -3.0, 0, 'floor', 'стол в центре кухни'),
        ('home_kitchen_chair', -3.0, -4.4, 180, 'floor', 'стул с юга'),
        ('home_kitchen_chair', -3.0, -1.6, 0, 'floor', 'стул с севера'),
        ('home_kitchen_chair', -4.4, -3.0, 270, 'floor', 'стул с запада'),
        ('plate', -2.6, -3.3, 0, 'surf:0.75', 'тарелка на стол'),
        ('coffee_cup_blue', -3.3, -2.7, 0, 'surf:0.75', 'кружка на стол'),
        ('sofa_modern', 3.0, -6.9, 180, 'floor', 'диван спиной к южной стене под окном'),
        ('table_coffee', 3.0, -5.3, 0, 'floor', 'журнальный столик'),
        ('armchair_modern', 1.0, -4.5, 270, 'floor', 'кресло'),
        ('home_tv_stand', 4.1, -3.0, 90, 'floor', 'ТВ-столик под восточным окном'),
        ('lamp_floor_modern', 4.0, -7.0, 0, 'floor', 'торшер в ЮВ углу'),
        ('home_rug_1', 2.5, -4.5, 0, 'floor', 'ковёр в гостиной'),
        ('home_plant_8', 4.0, -1.9, 0, 'floor', 'фикус у лестницы'),
        ('hallway_rack', -6.9, 0.0, 270, 'floor', 'вешалка у западной стены за дверью'),
        ('wall_switch', W, -1.7, 270, 'wall:1.35', 'выключатель у входной двери'),
        ('lamp_ceiling_modern', -3.0, -3.0, 90, 'ceil', 'лампа кухни'),
        ('lamp_ceiling_modern', 1.5, -4.5, 90, 'ceil', 'лампа гостиной'),
    ],
    1: [
        ('home_bath', 2.4, -6.9, 180, 'floor', 'ванна вдоль южной стены под окном'),
        ('home_washer', -1.1, -5.2, 270, 'floor', 'стиралка спиной к западной стене ванной'),
        ('home_toilet', 4.1, -5.1, 90, 'floor', 'унитаз у восточной стены'),
        ('home_bathroom_sink', 2.5, -4.9, 0, 'floor', 'раковина спиной к северной стене ванной'),
        ('home_bathroom_mirror', 2.5, -4.5, 0, 'wall:1.57', 'зеркало над раковиной'),
        ('bath_shelf', E, -6.5, 90, 'wall:1.7', 'полка на восточной стене ванной'),
        ('lamp_ceiling_modern', 1.5, -6.0, 90, 'ceil', 'лампа ванной'),
        ('home_bed', -3.0, 0.4, 0, 'floor', 'кровать спиной к северной стене под окном'),
        ('home_wardrobe_slide', -7.0, 0.0, 270, 'floor', 'шкаф-купе у западной стены'),
        ('home_nightstand', -4.6, 1.0, 0, 'floor', 'тумбочка у кровати'),
        ('lamp_bedside', -4.6, 1.0, 0, 'surf:0.6', 'ночник на тумбочку'),
        ('home_rug_6', -3.0, -1.3, 0, 'floor', 'ковёр у кровати'),
        ('wall_switch', -1.5, -2.2, 90, 'wall:1.35', 'выключатель спальни у двери'),
        ('lamp_ceiling_modern', -4.5, -1.5, 90, 'ceil', 'лампа спальни'),
        ('home_radiator', 4.1, -3.0, 90, 'floor', 'батарея под восточным окном коридора'),
    ],
    2: [
        ('home_sink_cabinet', 0.4, -6.9, 180, 'floor', 'тумба-мойка в линию под окном без угла'),
        ('home_kitchen_counter', 1.5, -6.9, 180, 'floor', 'столешница в линию'),
        ('home_stove', 2.6, -6.9, 180, 'floor', 'плита в линию под окном'),
        ('home_work_desk', 4.0, -3.0, 90, 'floor', 'стол письменный под восточным окном'),
        ('home_desk_chair', 3.2, -3.0, 270, 'floor', 'стул к столу'),
        ('sofa_modern', -6.9, -3.0, 270, 'floor', 'диван спиной к западу под окном'),
        ('home_wardrobe_slide', -5.6, 1.0, 0, 'floor', 'шкаф-купе у северной стены'),
        ('table_coffee', -5.3, -3.0, 0, 'floor', 'столик у дивана'),
        ('home_plant_8', -2.0, -4.0, 0, 'floor', 'фикус у стены кабинета'),
        ('lamp_floor_modern', -7.0, 1.0, 0, 'floor', 'торшер в СЗ углу'),
        ('lamp_ceiling_modern', -4.5, -1.5, 90, 'ceil', 'лампа гостиной'),
        ('lamp_ceiling_modern', 1.5, -4.5, 90, 'ceil', 'лампа кабинета'),
    ],
    3: [
        ('home_bed', 3.0, -6.4, 180, 'floor', 'кровать под южным окном'),
        ('home_nightstand', 1.3, -7.0, 180, 'floor', 'тумбочка у кровати'),
        ('home_rug_6', 2.5, -4.0, 0, 'floor', 'ковёр'),
        ('home_radiator', 4.1, -3.0, 90, 'floor', 'батарея под восточным окном'),
        ('lamp_ceiling_modern', 1.5, -4.5, 90, 'ceil', 'лампа спальни'),
        ('home_shelving', -4.5, 1.1, 0, 'floor', 'стеллаж у северной стены'),
        ('home_desk', -6.9, -5.5, 270, 'floor', 'стол у западной стены'),
        ('home_desk_chair', -6.0, -5.5, 90, 'floor', 'стул к столу'),
        ('cardboard_box', -3.0, -3.0, 30, 'floor', 'коробка'),
        ('lamp_ceiling_modern', -4.5, -3.0, 90, 'ceil', 'лампа кабинета'),
    ],
}
# План дома C (night_level.py --layout c, 28.09): марши (1,2)→(2,2) на этаже 0 и (2,0)→(1,0) на этаже 1.
PLAN_C = {
    0: [
        ('home_sink_cabinet', -3.9, -6.9, 180, 'floor', 'тумба-мойка у глухой южной стены'),
        ('home_kitchen_counter', -2.4, -6.9, 180, 'floor', 'столешница в линию'),
        ('home_stove', -0.9, -6.9, 180, 'floor', 'плита в линию'),
        ('home_fridge', 0.6, -6.8, 180, 'floor', 'холодильник в конце линии'),
        ('home_wall_cabinet', -3.9, S, 180, 'wall:1.9', 'навесной над мойкой'),
        ('home_wall_cabinet', -2.4, S, 180, 'wall:1.9', 'навесной над столешницей'),
        ('home_under_light', -3.9, S, 180, 'wall:1.45', 'подсветка под навесной над мойкой'),
        ('home_under_light', -2.4, S, 180, 'wall:1.45', 'подсветка под навесной над столешницей'),
        ('home_sink', -3.9, -6.9, 180, 'surf:1.15', 'мойка на тумбу'),
        ('home_microwave', -2.4, -7.0, 180, 'surf:1.15', 'микроволновка на столешницу'),
        ('frying_pan', -1.2, -6.8, 180, 'surf:1.16', 'сковорода на плиту'),
        ('table_round', -3.0, -3.0, 0, 'floor', 'стол'),
        ('home_kitchen_chair', -3.0, -4.4, 180, 'floor', 'стул с юга'),
        ('home_kitchen_chair', -4.4, -3.0, 270, 'floor', 'стул с запада'),
        ('plate', -3.0, -3.0, 0, 'surf:0.75', 'тарелка на стол'),
        ('sofa_modern', 4.0, 0.0, 90, 'floor', 'диван спиной к восточной стене'),
        ('table_coffee', 2.6, 0.0, 0, 'floor', 'журнальный столик'),
        ('home_tv_stand', -7.0, -6.0, 270, 'floor', 'ТВ-столик у западной стены'),
        ('home_plant_8', 4.0, -7.0, 0, 'floor', 'фикус в ЮВ углу'),
        ('wall_switch', E, -1.7, 90, 'wall:1.35', 'выключатель у входной двери'),
        ('lamp_ceiling_modern', -3.0, -4.5, 90, 'ceil', 'лампа кухни'),
        ('lamp_ceiling_modern', 3.0, -1.5, 90, 'ceil', 'лампа гостиной'),
    ],
    1: [
        ('home_bed', -6.4, -3.0, 270, 'floor', 'кровать спиной к западу под окном'),
        ('home_nightstand', -7.0, -1.2, 270, 'floor', 'тумбочка у кровати'),
        ('home_wardrobe_room', 4.0, -3.0, 90, 'floor', 'шкаф спиной к восточной стене'),
        ('home_work_desk', -6.0, 0.9, 0, 'floor', 'стол письменный у северной стены'),
        ('home_desk_chair', -6.0, 0.0, 180, 'floor', 'стул к столу'),
        ('home_rug_6', -3.8, -3.0, 0, 'floor', 'ковёр'),
        ('home_radiator', 4.1, -6.0, 90, 'floor', 'батарея под восточным окном'),
        ('lamp_ceiling_modern', -4.5, -3.0, 90, 'ceil', 'лампа спальни'),
    ],
    2: [
        ('home_shelving', -7.0, 0.3, 270, 'floor', 'стеллаж у западной стены'),
        ('cardboard_box', -3.0, -2.5, 20, 'floor', 'коробка'),
        ('cardboard_box', -2.5, -3.2, 50, 'floor', 'вторая коробка'),
        ('lamp_floor_modern', 4.0, 1.0, 0, 'floor', 'торшер в СВ углу'),
        ('armchair_modern', 3.0, -1.0, 90, 'floor', 'кресло'),
        ('home_rug_1', 0.0, -2.0, 0, 'floor', 'ковёр'),
        ('lamp_ceiling_modern', -1.5, -1.5, 90, 'ceil', 'лампа мансарды'),
    ],
}
SPOTS = {'a': {0: (-3.0, 0.0, -3.0), 1: (0.0, 3.0, -3.0), 2: (0.0, 6.0, -3.0), 3: (0.0, 9.0, -3.0), 4: (-4.5, 12.0, -1.5)},
         'b': {0: (0.5, 0.0, -2.5), 1: (1.5, 3.0, -3.0), 2: (-4.0, 6.0, -1.0), 3: (-3.0, 9.0, -1.0)},
         'c': {0: (0.0, 0.0, -3.0), 1: (2.5, 3.0, -2.5), 2: (-3.0, 6.0, -1.0)}}
LAYOUT = sys.argv[sys.argv.index('--plan') + 1] if '--plan' in sys.argv else 'a'
if LAYOUT == 'b': PLAN = PLAN_B
if LAYOUT == 'c': PLAN = PLAN_C

SAVE_NIGHT = 'if (!Cozy.Grid.LevelIO.CurrentLevelName.StartsWith("night_build")) return "НЕ СОХРАНЯЮ: открыт " + Cozy.Grid.LevelIO.CurrentLevelName; Cozy.Grid.LevelIO.Save(Cozy.Grid.LevelIO.CurrentLevelName); return "сохранён " + Cozy.Grid.LevelIO.CurrentLevelName;'


CODE = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I; if (gc == null) return "нет GridCursor";
var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var mPose = T.GetMethod("ComputeObjectPose", B);
var mSpawn = T.GetMethod("SpawnPlaced", B);
var mComp = T.GetMethod("SpawnCompanions", B);
var mFit = T.GetMethod("FitWidthToWallLike", B);
var fOrient = T.GetField("_orient", B); var fSide = T.GetField("_sideStop", B); var fLift = T.GetField("_liftStop", B);
var fFreeYaw = T.GetField("_freeYaw", B); var fTilt = T.GetField("_freeTilt", B);
if (mPose == null || mSpawn == null || mComp == null || mFit == null || fOrient == null) return "нет методов";
var cam = UnityEngine.Camera.main; var mouse = UnityEngine.InputSystem.Mouse.current;
var cursor = mouse.position.ReadValue();
var savedCamPos = cam.transform.position; var savedCamRot = cam.transform.rotation;
float L = LEVEL_Y; bool DRY = DRYFLAG;
var lines = new System.Collections.Generic.List<string>();
System.Func<UnityEngine.Vector3, UnityEngine.Vector3, float, bool> CrossesWall = (from, to, lvl) => {
  var a0 = new UnityEngine.Vector3(from.x, lvl + 1.0f, from.z); var a1 = new UnityEngine.Vector3(to.x, lvl + 1.0f, to.z);
  foreach (var hit in UnityEngine.Physics.RaycastAll(a0, a1 - a0, (a1 - a0).magnitude, ~0, UnityEngine.QueryTriggerInteraction.Ignore)) {
    var gb = hit.collider.GetComponentInParent<Cozy.Grid.GridBlock>(); if (gb != null && gb.role == Cozy.Grid.GridRole.Wall) return true;
    if (hit.collider.GetComponentInParent<Cozy.Grid.DoorPiece>() != null || hit.collider.GetComponentInParent<Cozy.Grid.WindowPiece>() != null) return true; }
  return false; };
UnityEngine.GameObject body = null;
System.Func<UnityEngine.GameObject, string> bounds = go => {
  var rs = go.GetComponentsInChildren<UnityEngine.Renderer>(); UnityEngine.Bounds b = default(UnityEngine.Bounds); bool any = false;
  foreach (var r in rs) { if (!r.enabled) continue; if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds); }
  return any ? b.min.ToString("F2") + ".." + b.max.ToString("F2") : "-"; };
try {
  foreach (var rec in new object[][] { RECORDS }) {
    string id = (string)rec[0]; float tx = (float)rec[1]; float tz = (float)rec[2]; float yaw = (float)rec[3]; string kind = (string)rec[4]; string tag = (string)rec[5];
    var def = Cozy.Grid.FurnitureCatalog.ById(id);
    if (def == null) { lines.Add(id + "|" + tag + "|НЕТ В КАТАЛОГЕ"); continue; }
    fSide.SetValue(gc, 0); fLift.SetValue(gc, 0); fTilt.SetValue(gc, 0f);
    fOrient.SetValue(gc, ((int)UnityEngine.Mathf.Round(yaw / 90f)) & 3);
    fFreeYaw.SetValue(gc, yaw);
    UnityEngine.Vector3 target; UnityEngine.Vector3 dir; float dist;
    float h = 0f; if (kind.Contains(":")) h = float.Parse(kind.Substring(kind.IndexOf(':') + 1), System.Globalization.CultureInfo.InvariantCulture);
    if (kind.StartsWith("shelf")) {
      var back = new UnityEngine.Vector3(UnityEngine.Mathf.Sin(yaw * UnityEngine.Mathf.Deg2Rad), 0f, UnityEngine.Mathf.Cos(yaw * UnityEngine.Mathf.Deg2Rad));
      target = new UnityEngine.Vector3(tx, L + h, tz);
      dir = (back + UnityEngine.Vector3.down * 1.0f).normalized; dist = 1.0f;
    } else if (kind.StartsWith("wall")) {
      var back = new UnityEngine.Vector3(UnityEngine.Mathf.Sin(yaw * UnityEngine.Mathf.Deg2Rad), 0f, UnityEngine.Mathf.Cos(yaw * UnityEngine.Mathf.Deg2Rad));
      target = new UnityEngine.Vector3(tx, L + h, tz) - back * 0.02f;
      dir = (back + UnityEngine.Vector3.down * 0.35f).normalized; dist = 1.6f;
    } else if (kind.StartsWith("surf")) {
      target = new UnityEngine.Vector3(tx, L + h, tz); dir = new UnityEngine.Vector3(0.12f, -1f, 0.08f).normalized; dist = 1.4f;
    } else {
      target = new UnityEngine.Vector3(tx, L, tz); dir = new UnityEngine.Vector3(0.3f, -1f, 0.2f).normalized; dist = 2.1f;
    }
    var offsets = kind.StartsWith("wall") || kind.StartsWith("shelf")
      ? new float[][] { new[]{0f,0f}, new[]{-0.3f,0f}, new[]{0.3f,0f}, new[]{-0.6f,0f}, new[]{0.6f,0f} }
      : new float[][] { new[]{0f,0f}, new[]{-0.3f,0f}, new[]{0.3f,0f}, new[]{0f,-0.3f}, new[]{0f,0.3f}, new[]{-0.6f,0f}, new[]{0.6f,0f}, new[]{0f,-0.6f}, new[]{0f,0.6f}, new[]{-0.3f,-0.3f}, new[]{0.3f,0.3f}, new[]{-0.3f,0.3f}, new[]{0.3f,-0.3f} };
    bool ok = false, blocked = true; UnityEngine.Vector3 pos = default(UnityEngine.Vector3); float outYaw = 0f; string wiggle = "";
    foreach (var off in offsets) {
      UnityEngine.Vector3 t = target;
      if (kind.StartsWith("wall") || kind.StartsWith("shelf")) { var alongWall = new UnityEngine.Vector3(dir.z, 0f, -dir.x).normalized; t += alongWall * off[0]; }
      else t += new UnityEngine.Vector3(off[0], 0f, off[1]);
      if ((off[0] != 0f || off[1] != 0f) && CrossesWall(target, t, L)) continue;
      cam.transform.SetPositionAndRotation(t - dir * dist, UnityEngine.Quaternion.identity);
      var localDir = cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction;
      cam.transform.rotation = UnityEngine.Quaternion.FromToRotation(localDir, dir);
      cam.transform.position = t - cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction * dist;
      body = new UnityEngine.GameObject("NightProbe");
      body.transform.position = new UnityEngine.Vector3(tx, L - 50f, tz);
      body.AddComponent<Cozy.Grid.InteractiveObject>().Build(def);
      var args = new object[] { def, cam, mouse, body, body.transform, L, null, null, null };
      ok = (bool)mPose.Invoke(gc, args);
      pos = ok ? (UnityEngine.Vector3)args[6] : default(UnityEngine.Vector3); outYaw = ok ? (float)args[7] : 0f; blocked = ok ? (bool)args[8] : true;
      UnityEngine.Object.DestroyImmediate(body); body = null;
      if (ok && !blocked) { if (off[0] != 0f || off[1] != 0f) wiggle = " сдвиг " + off[0].ToString("0.0") + "," + off[1].ToString("0.0"); break; }
    }
    string res = id + "|" + tag + "|" + (ok ? "ok" : "НЕТ ПОЗЫ") + "|" + (blocked ? "БЛОК" : "свободно") + "|"
      + pos.x.ToString("0.000") + "," + pos.y.ToString("0.000") + "," + pos.z.ToString("0.000") + "|" + outYaw.ToString("0") + "|цель " + tx.ToString("0.00") + "," + tz.ToString("0.00") + wiggle;
    if (ok && !blocked && !DRY) {
      var io = (Cozy.Grid.InteractiveObject)mSpawn.Invoke(gc, new object[] { def, pos, outYaw });
      mComp.Invoke(gc, new object[] { io, null }); mFit.Invoke(gc, new object[] { io }); UnityEngine.Physics.SyncTransforms();
      res += "|" + bounds(io.gameObject) + "|под=" + (io.transform.parent != null ? io.transform.parent.name : "-");
    }
    lines.Add(res);
  }
} finally {
  if (body != null) UnityEngine.Object.DestroyImmediate(body);
  cam.transform.SetPositionAndRotation(savedCamPos, savedCamRot);
}
return string.Join("\n", lines);
'''

TELEPORT = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
Cozy.Grid.GridCursor.I.TeleportPlayerTo(new UnityEngine.Vector3(PX, PY, PZ));
UnityEngine.Physics.SyncTransforms();
return "игрок " + Cozy.Grid.PlayerRef.GameObject.transform.position.ToString("F2");
'''


def cs_records(recs):
    out = []
    for (oid, x, z, yaw, kind, tag) in recs:
        out.append('new object[]{ "%s", %sf, %sf, %sf, "%s", "%s" }' % (oid, x, z, yaw, kind, tag.replace('"', "'")))
    return ', '.join(out)


def floor_center(f):
    return (-1.5, f * CS, -3.0)


def place_floor(f, dry):
    x, y, z = floor_center(f)
    # игрок на этаж: гейт видимости и PlaceFloorY считают от него; на этажах с лестничной дыркой центр
    # может попасть в дырку — берём клетку без дырки
    spot = SPOTS[LAYOUT][f]
    print('этаж %d: телепорт →' % f, run(TELEPORT.replace('PX', '%sf' % spot[0]).replace('PY', '%sf' % (spot[1] + 0.05)).replace('PZ', '%sf' % spot[2])))
    time.sleep(1.5)
    out = []
    for rec in PLAN[f]:
        code = CODE.replace('LEVEL_Y', '%sf' % (f * CS)).replace('DRYFLAG', 'true' if dry else 'false').replace('RECORDS', cs_records([rec]))
        res = run(code)
        print(res, flush=True)
        out.append(res)
        time.sleep(0.15)
    return '\n'.join(out)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'plan'
    dry = '--dry' in sys.argv
    if cmd == 'plan':
        for f, recs in PLAN.items():
            print('этаж', f, '— записей', len(recs))
            for r in recs: print('   ', r)
        return
    if cmd == 'floor':
        place_floor(int(sys.argv[2]), dry); return
    if cmd == 'all':
        for f in sorted(PLAN): place_floor(f, dry); time.sleep(1.0)
        if not dry: print(run(SAVE_NIGHT))
        return
    if cmd == 'save':
        print(run(SAVE_NIGHT)); return
    if cmd == 'clear':
        f = int(sys.argv[2]); y0 = f * CS
        print(run('''
if (!Cozy.Grid.LevelIO.CurrentLevelName.StartsWith("night_build")) return "НЕ СНОШУ: открыт " + Cozy.Grid.LevelIO.CurrentLevelName;
int n = 0; var doomed = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
foreach (var io in Cozy.Grid.InteractiveObject.All) { if (io == null || io.Def == null) continue; if (io.Def.id == "spawn_marker") continue;
  float y = io.transform.position.y; if (y < %sf - 0.5f || y > %sf + 2.9f) continue; doomed.Add(io); }
foreach (var io in doomed) { if (io != null) { n++; UnityEngine.Object.Destroy(io.gameObject); } }
return "снесено " + n;''' % (y0, y0)))
        return
    print(__doc__)


if __name__ == '__main__':
    main()
