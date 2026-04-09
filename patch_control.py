import re
with open("tests/unit/infrastructure/control_plane/test_control_plane_observability_metrics.py", "r") as f:
    text = f.read()

text = text.replace("occurred_at=datetime.utcnow(),", "occurred_at=datetime.now(timezone.utc),")
with open("tests/unit/infrastructure/control_plane/test_control_plane_observability_metrics.py", "w") as f:
    f.write(text)
