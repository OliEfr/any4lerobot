from lerobot.datasets.lerobot_dataset import LeRobotDataset

for name, repo_id in [
    ("libero_object_additionalCams_lerobot", "OliverHausdoerfer/libero_object"),
    ("libero_goal_additionalCams_lerobot", "OliverHausdoerfer/libero_goal"),
    ("libero_10_additionalCams_lerobot", "OliverHausdoerfer/libero_10"),
]:
    ds = LeRobotDataset(
        repo_id=repo_id,
        root=f"/home/admin_07/project_repos/any4lerobot/lerobot_datasets/{name}",
    )
    ds.push_to_hub(
        tags=["LeRobot", "libero", "franka"],
        private=False,
        push_videos=True,
        license="apache-2.0",
        upload_large_folder=False,
    )