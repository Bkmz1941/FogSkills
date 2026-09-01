#!/bin/sh
# Устанавливается копией: cp tavern-regress/probes/pre-commit.sh .git/hooks/pre-commit
# Красное в граблях/инвариантах останавливает коммит; здоровье доменов печатается справочно.
python3 "$HOME/.claude/skills/tavern-regress/probes/bugs.py" --lint || exit 1
python3 "$HOME/.claude/skills/tavern-regress/probes/skills_lint.py"
exit 0
