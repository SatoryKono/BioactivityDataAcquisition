import hashlib

from bioetl.application.composite._preflight_types import ProfileInfo


def get_expected_normalization_profile_hash(source_profiles: dict[str, ProfileInfo]) -> str:
    """Compute the deterministic runtime normalization profile hash for the composite DAG."""
    if not source_profiles:
        return "empty_dag"
    components = [f"{source}:{profile.profile_hash}" for source, profile in sorted(source_profiles.items())]
    return hashlib.sha256("|".join(components).encode("utf-8")).hexdigest()
