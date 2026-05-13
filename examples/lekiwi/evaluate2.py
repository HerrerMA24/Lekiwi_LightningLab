from lerobot.datasets.feature_utils import hw_to_dataset_features
from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.policies.act.modeling_act import ACTPolicy  # Changed from DiffusionPolicy
from lerobot.policies.factory import make_pre_post_processors
from lerobot.processor import make_default_processors
from lerobot.robots.lekiwi import LeKiwiClient, LeKiwiClientConfig
from lerobot.scripts.lerobot_record import record_loop
from lerobot.utils.constants import ACTION, OBS_STR
from lerobot.utils.control_utils import init_keyboard_listener
from lerobot.utils.utils import log_say
from lerobot.utils.visualization_utils import init_rerun

NUM_EPISODES = 1
FPS = 5
EPISODE_TIME_SEC = 120
TASK_DESCRIPTION = "Pick up the block and place it in the bin"
HF_MODEL_ID = "C:/Users/willi/lerobot/act_model/pretrained_model"  # Updated path
HF_DATASET_ID = "williamdgomez/lekiwi_eval"

def main():
    # Create the robot configuration & robot
    from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig
    from lerobot.cameras.configs import Cv2Rotation
    robot_config = LeKiwiClientConfig(
        remote_ip="[IP_ADDRESS]",  # Your Pi's IP
        id="my_awesome_kiwi",
        cameras={
            "front": OpenCVCameraConfig(
                index_or_path="/dev/video0",
                fps=30.0,
                width=224,  # Changed from 640
                height=224,  # Changed from 480
                rotation=Cv2Rotation.ROTATE_180,
                fourcc="MJPG"
            ),
            "wrist": OpenCVCameraConfig(
                index_or_path="/dev/video4",
                fps=30.0,
                width=224,  # Changed from 640
                height=224,  # Changed from 480
                rotation=Cv2Rotation.NO_ROTATION,
                fourcc="MJPG"
            ),
            "top": OpenCVCameraConfig(
                index_or_path="/dev/video2",
                fps=30.0,
                width=224,  # Changed from 640
                height=224,  # Changed from 480
                rotation=Cv2Rotation.NO_ROTATION,
                fourcc="MJPG"
            ),
        }
    )
    robot = LeKiwiClient(robot_config)

    # Create ACT policy (changed from DiffusionPolicy)
    policy = ACTPolicy.from_pretrained(HF_MODEL_ID)

    # Configure the dataset features
    action_features = hw_to_dataset_features(robot.action_features, ACTION)
    obs_features = hw_to_dataset_features(robot.observation_features, OBS_STR)
    dataset_features = {**action_features, **obs_features}

    # Create the dataset
    dataset = LeRobotDataset.create(
        repo_id=HF_DATASET_ID,
        fps=FPS,
        features=dataset_features,
        robot_type=robot.name,
        use_videos=True,
        image_writer_threads=4,
    )

    # Build Policy Processors
    preprocessor, postprocessor = make_pre_post_processors(
        policy_cfg=policy,
        pretrained_path=HF_MODEL_ID,
        dataset_stats=dataset.meta.stats,
        preprocessor_overrides={"device_processor": {"device": str(policy.config.device)}},
    )

    # Connect the robot
    robot.connect()

    teleop_action_processor, robot_action_processor, robot_observation_processor = make_default_processors()

    # Initialize the keyboard listener and rerun visualization
    listener, events = init_keyboard_listener()
    init_rerun(session_name="lekiwi_evaluate")

    try:
        if not robot.is_connected:
            raise ValueError("Robot is not connected!")

        print("Starting evaluate loop...")
        recorded_episodes = 0
        while recorded_episodes < NUM_EPISODES and not events["stop_recording"]:
            log_say(f"Running inference, recording eval episode {recorded_episodes} of {NUM_EPISODES}")

            # Main record loop
            record_loop(
                robot=robot,
                events=events,
                fps=FPS,
                policy=policy,
                preprocessor=preprocessor,
                postprocessor=postprocessor,
                dataset=dataset,
                control_time_s=EPISODE_TIME_SEC,
                single_task=TASK_DESCRIPTION,
                display_data=True,
                teleop_action_processor=teleop_action_processor,
                robot_action_processor=robot_action_processor,
                robot_observation_processor=robot_observation_processor,
            )

            # Reset the environment if not stopping or re-recording
            if not events["stop_recording"] and (
                (recorded_episodes < NUM_EPISODES - 1) or events["rerecord_episode"]
            ):
                log_say("Reset the environment")
                record_loop(
                    robot=robot,
                    events=events,
                    fps=FPS,
                    control_time_s=EPISODE_TIME_SEC,
                    single_task=TASK_DESCRIPTION,
                    display_data=True,
                    teleop_action_processor=teleop_action_processor,
                    robot_action_processor=robot_action_processor,
                    robot_observation_processor=robot_observation_processor,
                )

            if events["rerecord_episode"]:
                log_say("Re-record episode")
                events["rerecord_episode"] = False
                events["exit_early"] = False
                dataset.clear_episode_buffer()
                continue

            # Save episode
            dataset.save_episode()
            recorded_episodes += 1

    finally:
        # Clean up
        log_say("Stop recording")
        robot.disconnect()
        listener.stop()

        dataset.finalize()

if __name__ == "__main__":
    main()