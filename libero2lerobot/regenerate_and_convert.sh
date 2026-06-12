#!/bin/bash

conda activate any4lerobot

# flags for libero_h5.py
export SVT_LOG=1
export HF_DATASETS_DISABLE_PROGRESS_BARS=TRUE
export HDF5_USE_FILE_LOCKING=FALSE

# spatial
# python libero_utils/regenerate_libero_dataset.py \
#     --resolution 256 \
#     --libero_task_suite libero_spatial \
#     --libero_raw_data_dir /home/admin_07/project_repos/any4lerobot/libero_datasets/libero_spatial \
#     --libero_target_dir /home/admin_07/project_repos/any4lerobot/libero_datasets_regenerated/libero_spatial_additionalCams

# python libero_h5.py \
#     --src-paths /home/admin_07/project_repos/any4lerobot/libero_datasets_regenerated/libero_spatial_additionalCams \
#     --output-path /home/admin_07/project_repos/any4lerobot/lerobot_datasets \
#     --executor local \
#     --tasks-per-job 3 \
#     --workers 40 \
#     --push-to-hub \
#     --repo-id OliverHausdoerfer/libero_spatial_additionalCams

# # object
# python libero_utils/regenerate_libero_dataset.py \
#     --resolution 256 \
#     --libero_task_suite libero_object \
#     --libero_raw_data_dir /home/admin_07/project_repos/any4lerobot/libero_datasets/libero_object \
#     --libero_target_dir /home/admin_07/project_repos/any4lerobot/libero_datasets_regenerated/libero_object_additionalCams

# python libero_h5.py \
#     --src-paths /home/admin_07/project_repos/any4lerobot/libero_datasets_regenerated/libero_object_additionalCams \
#     --output-path /home/admin_07/project_repos/any4lerobot/lerobot_datasets \
#     --executor local \
#     --tasks-per-job 3 \
#     --workers 40 \
#     --push-to-hub \
#     --repo-id OliverHausdoerfer/libero_object_additionalCams

# # goal
# python libero_utils/regenerate_libero_dataset.py \
#     --resolution 256 \
#     --libero_task_suite libero_goal \
#     --libero_raw_data_dir /home/admin_07/project_repos/any4lerobot/libero_datasets/libero_goal \
#     --libero_target_dir /home/admin_07/project_repos/any4lerobot/libero_datasets_regenerated/libero_goal_additionalCams

# python libero_h5.py \
#     --src-paths /home/admin_07/project_repos/any4lerobot/libero_datasets_regenerated/libero_goal_additionalCams \
#     --output-path /home/admin_07/project_repos/any4lerobot/lerobot_datasets \
#     --executor local \
#     --tasks-per-job 3 \
#     --workers 30 \
#     --push-to-hub \
#     --repo-id OliverHausdoerfer/libero_goal_additionalCams

# # 10
# python libero_utils/regenerate_libero_dataset.py \
#     --resolution 256 \
#     --libero_task_suite libero_10 \
#     --libero_raw_data_dir /home/admin_07/project_repos/any4lerobot/libero_datasets/libero_10 \
#     --libero_target_dir /home/admin_07/project_repos/any4lerobot/libero_datasets_regenerated/libero_10_additionalCams

# python libero_h5.py \
#     --src-paths /home/admin_07/project_repos/any4lerobot/libero_datasets_regenerated/libero_10_additionalCams \
#     --output-path /home/admin_07/project_repos/any4lerobot/lerobot_datasets \
#     --executor local \
#     --tasks-per-job 3 \
#     --workers 40 \
#     --push-to-hub \
#     --repo-id OliverHausdoerfer/libero_10_additionalCams

# 90
# python libero_utils/regenerate_libero_dataset.py \
#     --resolution 256 \
#     --libero_task_suite libero_90 \
#     --libero_raw_data_dir /home/admin_07/project_repos/any4lerobot/libero_datasets/libero_90 \
#     --libero_target_dir /home/admin_07/project_repos/any4lerobot/libero_datasets_regenerated/libero_90_additionalCams

# python libero_h5.py \
#     --src-paths /home/admin_07/project_repos/any4lerobot/libero_datasets_regenerated/libero_90_additionalCams \
#     --output-path /home/admin_07/project_repos/any4lerobot/lerobot_datasets \
#     --executor local \
#     --tasks-per-job 3 \
#     --workers 40 \
#     --push-to-hub \
#     --repo-id OliverHausdoerfer/libero_90_additionalCams

# object — UR5e embodiment (delta replay; switch to --replay_mode absolute if the success rate is too low)
python libero_utils/regenerate_libero_dataset.py \
    --resolution 256 \
    --libero_task_suite libero_object \
    --robot UR5e \
    --replay_mode delta \
    --libero_raw_data_dir /home/admin_07/project_repos/any4lerobot/libero_datasets/libero_object \
    --libero_target_dir /home/admin_07/project_repos/any4lerobot/libero_datasets_regenerated/libero_object_ur5e_additionalCams

# enable once the regeneration success rate looks good
# python libero_h5.py \
#     --src-paths /home/admin_07/project_repos/any4lerobot/libero_datasets_regenerated/libero_object_ur5e_additionalCams \
#     --output-path /home/admin_07/project_repos/any4lerobot/lerobot_datasets \
#     --robot-type ur5e \
#     --executor local \
#     --tasks-per-job 3 \
#     --workers 30 \
#     --push-to-hub \
#     --repo-id OliverHausdoerfer/libero_object_ur5e_additionalCams
