from lerobot.datasets.lerobot_dataset import LeRobotDataset
ds = LeRobotDataset(
    repo_id='OliverHausdoerfer/libero_spatial',
    root='/home/admin_07/project_repos/any4lerobot/lerobot_datasets/libero_spatial_additionalCams_lerobot',
)
ds.push_to_hub(
    tags=['LeRobot', 'libero', 'franka', 'libero_spatial', 'default'],
    private=False,
    push_videos=True,
    license='apache-2.0',
    upload_large_folder=False,
)
