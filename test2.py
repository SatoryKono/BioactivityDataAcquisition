import sys
import os

sys.path.insert(0, "src")
from bioetl.infrastructure.config._base import Settings

# Let's instantiate settings with some environment variables set and see what works
os.environ["BIOETL_PIPELINE__HEALTH_CHECK_MODE"] = "probe"
os.environ["BIOETL_PIPELINE__CONTROL_PLANE__REQUIRED_PERSISTENCE_PROFILE"] = "replay_ready"
os.environ["BIOETL_PIPELINE__CONTROL_PLANE__CHECKPOINT_COMPATIBILITY_POLICY"] = "observe"

s = Settings()
print("Health check mode:", s.pipeline.health_check_mode)
print("Required persistence:", s.pipeline.control_plane.required_persistence_profile)
print("Checkpoint compat:", s.pipeline.control_plane.checkpoint_compatibility_policy)
