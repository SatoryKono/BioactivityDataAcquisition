from tests.unit.repo_backed.scripts.ai.mcp.test_repo_env_loaders import (
    _clean_env,
    _run_bash,
)

r = _run_bash(
    "normalize_repo_env_aliases; "
    "printf '%s\\n%s\\n' \"${OPENAI_API_KEY-unset}\" "
    '"${OPENROUTER_API_KEY-unset}"',
    env=_clean_env(
        OPENAI_API_KEY="synthetic-openai-key",
        OPENROUTER_API_KEY=None,
    ),
)
print("rc", r.returncode)
print("stdout", repr(r.stdout))
print("stderr", repr(r.stderr))

r2 = _run_bash(
    "normalize_repo_env_aliases; "
    "printf '%s\\n%s\\n' \"$NEO4J_USERNAME\" \"$NEO4J_PASSWORD\"",
    env=_clean_env(NEO4J_AUTH="fixture-user/fixture-password"),
)
print("rc2", r2.returncode)
print("stdout2", repr(r2.stdout))
print("stderr2", repr(r2.stderr))

r3 = _run_bash(
    "echo BEFORE=$OPENAI_API_KEY; normalize_repo_env_aliases; echo AFTER=$OPENAI_API_KEY; env | grep -E 'OPEN|NEO4J' || true",
    env=_clean_env(
        OPENAI_API_KEY="synthetic-openai-key",
        OPENROUTER_API_KEY=None,
        NEO4J_AUTH="fixture-user/fixture-password",
    ),
)
print("rc3", r3.returncode)
print("stdout3", r3.stdout)
print("stderr3", r3.stderr)
