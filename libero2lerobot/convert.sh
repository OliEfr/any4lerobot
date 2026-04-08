export SVT_LOG=1
export HF_DATASETS_DISABLE_PROGRESS_BARS=TRUE
export HDF5_USE_FILE_LOCKING=FALSE

python libero_h5.py \
    --src-paths /home/admin_07/project_repos/any4lerobot/libero_datasets_regenerated/libero_spatial_additionalCams \
    --output-path /home/admin_07/project_repos/any4lerobot/lerobot_datasets \
    --executor local \
    --tasks-per-job 3 \
    --workers 30 
