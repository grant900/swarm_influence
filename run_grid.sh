#!/bin/zsh
# Final grid. Usage: ./run_grid.sh <model> <reps> [extra]   (extra = "gpt" adds decode/rounding)
# All output goes to runs_grid (resumable: finished cells are skipped). Do not edit packs after launch.
M=$1; R=${2:-5}; EXTRA=${3:-}; W=5; OUT=runs_grid
H=forum-ontopic-help__gate-costly__norm-conflict
CORE=(control $H ${H}__reveal-gradnorm
  forum-ontopic-help__gate-costly__norm-benign__reveal-gradnorm
  forum-ontopic__gate-costly__norm-conflict__reveal-gradnorm
  forum-unrelated__gate-costly__norm-conflict__reveal-gradnorm)
GRADED=(${H}__payoff-graded ${H}__reveal-gradnorm__payoff-graded)
b() { uv run run_batch.py --runs $OUT --model $M --workers $W --max-turns 80 "$@" }

# G1 core: relevance x norm x reveal x pressure on migrated (forced)
b --reps $R --tasks migrated --arms forced --packs $CORE
b --reps $R --tasks migrated --arms forced --pressure --packs $CORE
b --reps $R --tasks migrated --arms forced --packs forum-ontopic-help__gate-blatant__norm-blatant   # v1/v2 anchor
# G2 graded payoff x reveal x pressure
b --reps $((R>4?4:R)) --tasks migrated --arms forced --packs $GRADED
b --reps $((R>4?4:R)) --tasks migrated --arms forced --pressure --packs $GRADED
# G3 found arm (discovery in the wild), migrated only
b --reps $R --tasks migrated --arms found --packs control ${H}__reveal-gradnorm forum-unrelated__gate-costly__norm-conflict__reveal-gradnorm
# G4 baselines: no pointer at all; positive control (told to follow forum conventions)
b --reps $R --tasks migrated --arms none --packs control
b --reps 4 --tasks migrated --arms forced --mandates follow --packs $H
# G5 (GPT-family only): swarm the agent doesn't need (decode) and the impossible-test norm (rounding)
if [[ $EXTRA == gpt ]]; then
  b --reps 4 --tasks decode rounding --arms forced --pressure --packs control ${H}__reveal-gradnorm forum-unrelated__gate-costly__norm-conflict__reveal-gradnorm
fi
