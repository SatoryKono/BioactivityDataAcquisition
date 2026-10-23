import re

with open("docs/04-reference/environment-variables.md") as f:
    docs_content = f.read()

# I see what the issue is. The variables are under BIOETL_PIPELINE__CONTROL_PLANE__...
# Let's ensure the variables in docs have the exact names used by Pydantic.
# Let's check the schema for ControlPlaneSettings.

print(docs_content)
