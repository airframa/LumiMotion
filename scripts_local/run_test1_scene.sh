#!/bin/bash
# usage: bash scripts_local/run_test1_scene.sh <scene_dir> <gpu> <w_bin> <w_xyz>
set -e
SCENE=$1; GPU=$2; W_BIN=$3; W_XYZ=$4

SOURCE_PATH="data/d-nerf-relight-spec32/${SCENE}"
OUTPUT_PATH="outputs_test1/chapelday_goldenbay/${SCENE}_r2"
TRAIN_LIGHT="chapel_day_4k_32x16_rot0"
TEST_LIGHT="golden_bay_4k_32x16_rot330"
RESOLUTION=2
W_COLOR=0.01
DEPTH_RATIO=0.0

export CUDA_VISIBLE_DEVICES=$GPU
export CUDA_HOME=$CONDA_PREFIX
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib:$CUDA_HOME/lib64:$LD_LIBRARY_PATH

echo "[$(date)] === START $SCENE gpu=$GPU wbin=$W_BIN wxyz=$W_XYZ ==="

python -m scripts.train_stage1 --source_path="$SOURCE_PATH" --model_path="$OUTPUT_PATH" \
  --is_blender --eval --gt_alpha_mask_as_scene_mask --resolution="$RESOLUTION" --iterations 35000 \
  --train_light_folder "$TRAIN_LIGHT" --densify_until_iter 20000 \
  --lambda_separation "$W_BIN" --d_xyz_loss_weight "$W_XYZ" --binarization_warm_up 1000 \
  --depth_ratio 1.0 --d_color_reg_loss_weight "$W_COLOR"

python -m scripts.render_stage1_insights --source_path="$SOURCE_PATH" --model_path="$OUTPUT_PATH" \
  --is_blender --eval --resolution=$RESOLUTION --load_iter 35000 \
  --train_light_folder "$TRAIN_LIGHT" --depth_ratio "$DEPTH_RATIO"

python -m scripts.train_stage2 --source_path="$SOURCE_PATH" --model_path="$OUTPUT_PATH" \
  --is_blender --eval --gt_alpha_mask_as_scene_mask --resolution="$RESOLUTION" --iterations 55000 \
  --load_iter 35000 --diffuse_sample_num 512 \
  --train_light_folder "$TRAIN_LIGHT" --depth_ratio "$DEPTH_RATIO"

python -m scripts.render_materials --source_path="$SOURCE_PATH" --model_path="$OUTPUT_PATH" \
  --is_blender --eval --resolution="$RESOLUTION" --load_iter 55000 \
  --train_light_folder "$TRAIN_LIGHT" --depth_ratio "$DEPTH_RATIO"

# ---- static eval ----
python -m scripts.scale_albedo_static --source_path "$SOURCE_PATH" --model_path "$OUTPUT_PATH" \
  --eval --is_blender --load_iter 55000 --train_light_folder "$TRAIN_LIGHT" \
  --test_light_folder "$TEST_LIGHT" --resolution "$RESOLUTION" --depth_ratio "$DEPTH_RATIO"

python -m scripts.eval_material_static --source_path "$SOURCE_PATH" --model_path "$OUTPUT_PATH" \
  --eval --is_blender --load_iter 55000 --train_light_folder "$TRAIN_LIGHT" \
  --test_light_folder "$TEST_LIGHT" --resolution "$RESOLUTION" --depth_ratio "$DEPTH_RATIO"

python -m scripts.eval_relight_static --source_path "$SOURCE_PATH" --model_path "$OUTPUT_PATH" \
  --eval --is_blender --load_iter 55000 --train_light_folder "$TRAIN_LIGHT" \
  --test_light_folder "$TEST_LIGHT" --resolution "$RESOLUTION" \
  --diffuse_sample_num 2048 --depth_ratio "$DEPTH_RATIO"

python -m scripts.eval_nvs_static --source_path "$SOURCE_PATH" --model_path "$OUTPUT_PATH" \
  --eval --is_blender --load_iter 55000 --train_light_folder "$TRAIN_LIGHT" \
  --resolution "$RESOLUTION" --diffuse_sample_num 2048 --depth_ratio "$DEPTH_RATIO"

# ---- dynamic eval ----
python -m scripts.scale_albedo_dynamic --source_path "$SOURCE_PATH" --model_path "$OUTPUT_PATH" \
  --eval --is_blender --load_iter 55000 --train_light_folder "$TRAIN_LIGHT" \
  --test_light_folder "$TEST_LIGHT" --resolution "$RESOLUTION" --depth_ratio "$DEPTH_RATIO"

python -m scripts.eval_material_dynamic --source_path "$SOURCE_PATH" --model_path "$OUTPUT_PATH" \
  --eval --is_blender --load_iter 55000 --train_light_folder "$TRAIN_LIGHT" \
  --test_light_folder "$TEST_LIGHT" --resolution "$RESOLUTION" --depth_ratio "$DEPTH_RATIO"

python -m scripts.eval_relight_dynamic --source_path "$SOURCE_PATH" --model_path "$OUTPUT_PATH" \
  --eval --is_blender --load_iter 55000 --train_light_folder "$TRAIN_LIGHT" \
  --test_light_folder "$TEST_LIGHT" --resolution "$RESOLUTION" \
  --diffuse_sample_num 2048 --depth_ratio "$DEPTH_RATIO"

python -m scripts.eval_nvs_dynamic --source_path "$SOURCE_PATH" --model_path "$OUTPUT_PATH" \
  --eval --is_blender --load_iter 55000 --train_light_folder "$TRAIN_LIGHT" \
  --resolution "$RESOLUTION" --diffuse_sample_num 2048 --depth_ratio "$DEPTH_RATIO"

echo "[$(date)] === DONE $SCENE ==="nn