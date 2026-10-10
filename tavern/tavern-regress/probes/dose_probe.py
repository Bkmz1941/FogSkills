#!/usr/bin/env python3
"""Проба механики доз (отравление, головная боль, боль) — в play, уровень любой с игроком.

python3 dose_probe.py            прогон; код 1 — красное
Характеризующий замер перед рефакторингом PlayerExposure (T-PLAN-0510 №10, DoseTrack):
дозы, степени, очередь с задержкой, Ease/Cure, спад по таймеру (таймеры на время пробы
укорачиваются до 2 с и возвращаются в finally, DebugTune.Save не зовётся — P415).
Игроку по-настоящему даётся яд (анимация рвоты, «на четвереньках» при 2 дозах — руки
опускаются), всё снимается в конце.
"""
import json, pathlib, subprocess, sys, time

MCP = pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py'
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
PE = 'Cozy.Effects.PlayerExposure'


def run(code):
    out = subprocess.run(['python3', str(MCP), 'execute_code', json.dumps({'action': 'execute', 'code': code})],
                         capture_output=True, text=True, timeout=120, cwd=PROJECT)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    try:
        d = json.loads(line)
    except Exception:
        raise SystemExit('мост не ответил: ' + out.stdout[-500:])
    if not d.get('success'):
        raise SystemExit('ОШИБКА моста: ' + json.dumps(d, ensure_ascii=False)[:1200])
    return (d.get('data') or {}).get('result')


def state():
    r = run('var p = typeof(%s); return %s.PoisonDoses + "|" + %s.Poisoned + "|" + %s.PoisonStage + "|" + %s.PoisonLeft.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture)'
            ' + "|" + %s.IncomingDoses + "|" + %s.IncomingIn.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture)'
            ' + "|" + %s.HeadacheDoses + "|" + %s.Aching + "|" + %s.HeadacheStage + "|" + %s.HeadacheLeft.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture)'
            ' + "|" + %s.IncomingHeadache + "|" + %s.IncomingHeadacheIn.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture)'
            ' + "|" + %s.PainDoses + "|" + %s.Hurting + "|" + %s.PainStage + "|" + %s.PainLeft.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture);'
            % tuple([PE] * 17))
    f = r.split('|')
    keys = ['pDoses', 'poisoned', 'pStage', 'pLeft', 'pIn', 'pInAt', 'hDoses', 'aching', 'hStage', 'hLeft', 'hIn', 'hInAt', 'nDoses', 'hurting', 'nStage', 'nLeft']
    return dict(zip(keys, f))


def call(expr):
    run('%s; return "ok";' % expr)


def main():
    red = []

    def expect(label, cond, got):
        print(('✓ ' if cond else '✗ ') + label + ' → ' + got)
        if not cond:
            red.append(label)

    alive = run('return (Cozy.Grid.PlayerRef.GameObject != null) + "|" + Cozy.Character.PlayerTarget.Dead;')
    if alive != 'True|False':
        print('КРАСНОЕ: нет живого игрока: ' + str(alive)); return 1
    saved = run('return string.Join("|", new string[] { %s });' % ', '.join(
        '%s.%s.ToString(System.Globalization.CultureInfo.InvariantCulture)' % (PE, k) for k in
        ['PoisonDelay1', 'PoisonDelay2', 'PoisonDelay3', 'PoisonDelayRandom', 'HeadacheDelay1', 'HeadacheDelay2', 'HeadacheDelayRandom',
         'PoisonSeconds', 'HeadacheSeconds', 'PainSeconds1', 'PainSeconds2']))
    try:
        call('%s.CurePoison(); %s.CureHeadache(); %s.CurePain(); %s.PoisonDelay1 = 0f; %s.PoisonDelay2 = 0f; %s.PoisonDelay3 = 0f; %s.PoisonDelayRandom = false; %s.HeadacheDelay1 = 0f; %s.HeadacheDelay2 = 0f; %s.HeadacheDelayRandom = false' % tuple([PE] * 10))
        time.sleep(0.3)
        s = state(); expect('чисто на старте', s['pDoses'] == '0' and s['hDoses'] == '0' and s['nDoses'] == '0', str(s))

        call('%s.Poison(1)' % PE); time.sleep(0.3); s = state()
        expect('яд: 1 доза → степень 1, таймер ~PoisonSeconds', s['pDoses'] == '1' and s['poisoned'] == 'True' and s['pStage'] == '1' and float(s['pLeft']) > 0, str(s))
        call('%s.Poison(1)' % PE); time.sleep(0.3); s = state()
        expect('яд: +1 → 2 дозы, степень 2', s['pDoses'] == '2' and s['pStage'] == '2', str(s))
        call('%s.EasePoison()' % PE); time.sleep(0.3); s = state()
        expect('яд: Ease → 1 доза', s['pDoses'] == '1' and s['pStage'] == '1', str(s))
        call('%s.PoisonDelay2 = 1f' % PE); call('%s.Poison(1)' % PE); time.sleep(0.2); s = state()
        expect('яд: с задержкой → в очереди 1, через ~1 с', s['pIn'] == '1' and 0.3 <= float(s['pInAt']) <= 1.0 and s['pDoses'] == '1', str(s))
        time.sleep(1.3); s = state()
        expect('яд: очередь впиталась → 2 дозы', s['pDoses'] == '2' and s['pIn'] == '0', str(s))
        call('%s.PoisonDelay2 = 0f' % PE)
        call('%s.CurePoison()' % PE); time.sleep(0.3); s = state()
        expect('яд: Cure → 0, не отравлен', s['pDoses'] == '0' and s['poisoned'] == 'False', str(s))

        call('%s.GiveHeadache(1)' % PE); time.sleep(0.3); s = state()
        expect('боль головы: 1 → степень 1', s['hDoses'] == '1' and s['aching'] == 'True' and s['hStage'] == '1' and float(s['hLeft']) > 0, str(s))
        call('%s.GiveHeadache(3)' % PE); time.sleep(0.3); s = state()
        expect('боль головы: +3 → потолок 2', s['hDoses'] == '2' and s['hStage'] == '2', str(s))
        call('%s.EaseHeadache()' % PE); time.sleep(0.3); s = state()
        expect('боль головы: Ease → 1', s['hDoses'] == '1', str(s))
        call('%s.HeadacheDelay2 = 1f' % PE); call('%s.GiveHeadache(1)' % PE); time.sleep(0.2); s = state()
        expect('боль головы: с задержкой → очередь 1', s['hIn'] == '1' and s['hDoses'] == '1', str(s))
        time.sleep(1.3); s = state()
        expect('боль головы: очередь впиталась → 2', s['hDoses'] == '2' and s['hIn'] == '0', str(s))
        call('%s.HeadacheDelay2 = 0f' % PE)
        call('%s.CureHeadache()' % PE); time.sleep(0.3); s = state()
        expect('боль головы: Cure → 0', s['hDoses'] == '0' and s['aching'] == 'False', str(s))

        call('%s.GivePain(1)' % PE); time.sleep(0.3); s = state()
        expect('боль: 1 → степень 1, таймер PainSeconds1', s['nDoses'] == '1' and s['hurting'] == 'True' and s['nStage'] == '1' and float(s['nLeft']) > 0, str(s))
        left1 = float(s['nLeft'])
        call('%s.GivePain(2)' % PE); time.sleep(0.3); s = state()
        expect('боль: 2 → степень 2, таймер PainSeconds2', s['nDoses'] == '2' and s['nStage'] == '2', str(s))
        call('%s.GivePain(1)' % PE); time.sleep(0.3); s = state()
        expect('боль: 1 поверх 2 → остаётся 2', s['nDoses'] == '2', str(s))
        call('%s.CurePain()' % PE); time.sleep(0.3); s = state()
        expect('боль: Cure → 0', s['nDoses'] == '0' and s['hurting'] == 'False', str(s))

        call('%s.PoisonSeconds = 2f; %s.HeadacheSeconds = 2f; %s.PainSeconds1 = 2f; %s.PainSeconds2 = 2f' % tuple([PE] * 4))
        call('%s.Poison(2); %s.GiveHeadache(2); %s.GivePain(2)' % tuple([PE] * 3)); time.sleep(0.3); s = state()
        expect('спад: старт 2/2/2', s['pDoses'] == '2' and s['hDoses'] == '2' and s['nDoses'] == '2', str(s))
        time.sleep(2.4); s = state()
        expect('спад: через 2 с → 1/1/1', s['pDoses'] == '1' and s['hDoses'] == '1' and s['nDoses'] == '1', str(s))
        time.sleep(2.4); s = state()
        expect('спад: через 4 с → 0/0/0, статусы сняты', s['pDoses'] == '0' and s['hDoses'] == '0' and s['nDoses'] == '0'
               and s['poisoned'] == 'False' and s['aching'] == 'False' and s['hurting'] == 'False', str(s))
    finally:
        v = saved.split('|')
        call('%s.PoisonDelay1 = %sf; %s.PoisonDelay2 = %sf; %s.PoisonDelay3 = %sf; %s.PoisonDelayRandom = %s; %s.HeadacheDelay1 = %sf; %s.HeadacheDelay2 = %sf; %s.HeadacheDelayRandom = %s; '
             '%s.PoisonSeconds = %sf; %s.HeadacheSeconds = %sf; %s.PainSeconds1 = %sf; %s.PainSeconds2 = %sf; %s.CurePoison(); %s.CureHeadache(); %s.CurePain()'
             % (PE, v[0], PE, v[1], PE, v[2], PE, v[3].lower(), PE, v[4], PE, v[5], PE, v[6].lower(), PE, v[7], PE, v[8], PE, v[9], PE, v[10], PE, PE, PE))
        print('восстановлено: задержки и таймеры как были, статусы сняты')
    print('КРАСНОЕ: ' + ', '.join(red) if red else 'ЗЕЛЁНОЕ: дозы, очереди, Ease/Cure и спад ведут себя как записано')
    return 1 if red else 0


if __name__ == '__main__':
    sys.exit(main())
