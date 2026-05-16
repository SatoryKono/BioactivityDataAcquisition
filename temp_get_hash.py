import sys
sys.path.insert(0, 'src')

from bioetl.domain.normalization.profiles.registry import resolve_normalization_profile_identity

identity = resolve_normalization_profile_identity("chembl", "target")
if identity:
    print(f"New hash: {identity.profile_hash}")
else:
    print("Profile not found")
