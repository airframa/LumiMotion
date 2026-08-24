#!/usr/bin/env bash
# Experiment 1 -- Stage 2 measurement.
#   brief sec 6, amendment 2 sec 4, addendum 2 sec B (exposure instrumentation).
#
# Runs the two scenes in parallel on GPUs 0 and 1. ~45 min wall clock.
# Launch in tmux; do not background this with nohup alongside another copy.
#
#   tmux new -s exp1stage2
#   bash scripts_local/exp1/run_stage2.sh
#
set -euo pipefail

REPO=/home/fmb/projects/LumiMotion-observability
OUTDIR=$REPO/docs/exp1_assets
MODELS=/data/fmb/lumimotion/outputs_test1/chapelday_goldenbay
ITER=55000

cd "$REPO"
source /home/fmb/miniconda3/etc/profile.d/conda.sh
conda activate lumimotion
LOGDIR=/data/fmb/lumimotion/logs_exp1
mkdir -p "$OUTDIR" "$LOGDIR"

run () {          # $1 = scene stem, $2 = gpu
  local S=$1 G=$2
  CUDA_VISIBLE_DEVICES=$G python scripts_local/exp1/coverage_seq.py \
    --model_path  "$MODELS/${S}150_v5_spec32_r2_mlp" \
    --source_path "$REPO/data/d-nerf-relight-spec32/${S}150_v5_spec32" \
    --deform_type mlp \
    --iteration   $ITER \
    --out         "$OUTDIR/coverage_${S}150_v5_spec32_r2_mlp.npz" \
    2>&1 | tee "$LOGDIR/stage2_${S}.log"
}

echo "=== Stage 2 start $(date -Is) ==="
run jumpingjacks 0 &
P1=$!
run standup      1 &
P2=$!
wait $P1; wait $P2
echo "=== Stage 2 done  $(date -Is) ==="
ls -lh "$OUTDIR"/coverage_*.npz
