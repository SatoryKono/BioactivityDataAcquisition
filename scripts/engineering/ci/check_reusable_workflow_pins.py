import argparse
import sys
import os
import yaml
import re

REGISTRY_PATH = "configs/quality/reusable_action_pins.yaml"
WORKFLOW_PATHS = [".github/workflows/pr-required.yml"]

def check_pins(registry_path, workflow_paths):
    if not os.path.exists(registry_path):
        print(f"Error: Registry file not found at {registry_path}")
        return False

    with open(registry_path, "r") as f:
        registry = yaml.safe_load(f)
    if not registry:
        registry = {}

    allowed_pins = {pin["path"]: pin["sha"] for pin in registry.get("pins", [])}

    all_valid = True
    sha_pattern = re.compile(r"^[0-9a-f]{40}$")

    for w_path in workflow_paths:
        if not os.path.exists(w_path):
            print(f"Error: Workflow file not found at {w_path}")
            all_valid = False
            continue

        with open(w_path, "r") as f:
            workflow = yaml.safe_load(f)

        jobs = workflow.get("jobs", {})
        for job_name, job_details in jobs.items():
            steps = job_details.get("steps", [])
            for step in steps:
                uses = step.get("uses")
                if not uses:
                    continue

                if uses.startswith("./.github/actions/"):
                    action_yml_path = os.path.join(uses, "action.yml")
                    if not os.path.exists(action_yml_path):
                        print(f"Error: Local action {uses} does not have an action.yml")
                        all_valid = False
                else:
                    parts = uses.split("@")
                    if len(parts) != 2:
                        print(f"Error: External action {uses} is not pinned")
                        all_valid = False
                        continue

                    action_path = parts[0]
                    action_sha = parts[1]

                    if not sha_pattern.match(action_sha):
                        print(f"Error: External action {uses} is not pinned to a full 40-hex SHA")
                        all_valid = False
                        continue

                    if action_path not in allowed_pins:
                        print(f"Error: Action {action_path} is not in the allowed pins registry")
                        all_valid = False
                    elif allowed_pins[action_path] != action_sha:
                        print(f"Error: Action {action_path} is pinned to {action_sha}, but registry requires {allowed_pins[action_path]}")
                        all_valid = False

    return all_valid

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Check pins")
    args = parser.parse_args()

    if args.check:
        if not check_pins(REGISTRY_PATH, WORKFLOW_PATHS):
            sys.exit(1)
        print("Pin check passed.")

if __name__ == "__main__":
    main()
