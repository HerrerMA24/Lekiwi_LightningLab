#!/usr/bin/env python3
"""
LeKiwi ACT Inference - Runs on Mac, connects to Pi host
"""
import numpy as np
import torch
from lerobot.policies.act.modeling_act import ACTPolicy
from lerobot.robots.lekiwi import LeKiwiClient, LeKiwiClientConfig
from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig
from lerobot.cameras.configs import Cv2Rotation

# ============================================
# CONFIGURATION
# ============================================
PI_IP = "172.20.10.3"
MODEL_PATH = "/Users/jgreeley/Downloads/act_model_3/checkpoints/050000/pretrained_model"
# ============================================

print("=" * 50)
print("LeKiwi ACT Inference (Mac → Pi)")
print("=" * 50)

# Load ACT policy
print("Loading ACT policy...")
policy = ACTPolicy.from_pretrained(MODEL_PATH)
policy = policy.to("cpu")
policy.eval()
print(f"✓ Policy loaded from {MODEL_PATH}")

# Configure robot client (connects to Pi host)
print(f"Connecting to Pi at {PI_IP}...")
robot_config = LeKiwiClientConfig(
    remote_ip=PI_IP,
    id="my_awesome_kiwi",
    cameras={
        "front": OpenCVCameraConfig(
            index_or_path="/dev/video0",
            fps=30.0,
            width=640,
            height=480,
            rotation=Cv2Rotation.ROTATE_180,
            fourcc="MJPG"
        ),
        "wrist": OpenCVCameraConfig(
            index_or_path="/dev/video4",
            fps=30.0,
            width=640,
            height=480,
            rotation=Cv2Rotation.NO_ROTATION,
            fourcc="MJPG"
        ),
    }
)

robot = LeKiwiClient(robot_config)
robot.connect()
print("✓ Connected to LeKiwi robot!")

print("" + "=" * 50)
print("Starting inference...")
print("Press Ctrl+C to stop")
print("=" * 50 + "")

try:
    step = 0
    while True:
        # Get observation from robot (cameras + state)
        observation = robot.get_observation()

        observation["observation.images.front"] = observation.pop("front")
        observation["observation.images.wrist"] = observation.pop("wrist")

        # Convert numpy arrays to tensors
        observation = {k: torch.from_numpy(v).float() if isinstance(v, np.ndarray) else v for k, v in observation.items()}

        # Run ACT policy to predict action
        with torch.no_grad():
            action = policy.select_action(observation)

        # Send action to robot
        robot.send_action(action)

        step += 1
        if step % 10 == 0:
            print(f"Step {step}: Running...")

except KeyboardInterrupt:
    print("Stopping inference...")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    robot.disconnect()
    print("✓ Robot disconnected safely")
    print("" + "=" * 50)
    print("Inference complete")
    print("=" * 50)