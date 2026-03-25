"""CI script to validate contract registry consistency."""

import sys
from pathlib import Path

from bioetl.domain.control_plane.contract_registry import (
    ContractRegistry,
    RegistryValidationSeverity
)


def main() -> int:
    """Main validation entry point."""
    repo_root = Path(__file__).parent.parent.parent
    registry_path = repo_root / "configs/base/contract_registry.yaml"
    
    if not registry_path.exists():
        print("::error::Contract registry not found")
        return 1
    
    try:
        # Load registry
        registry = ContractRegistry(registry_path)
        print(f"::notice::Loaded contract registry with {len(registry.entries)} entries")
        
        # Validate all entries
        validation_result = registry.validate_all()
        
        if validation_result.valid:
            print("::notice::All registry entries are valid")
        else:
            print(f"::warning::Found {len(validation_result.issues)} validation issues")
            
            # Count by severity
            blocking = [i for i in validation_result.issues if i.severity == RegistryValidationSeverity.BLOCKING]
            warnings = [i for i in validation_result.issues if i.severity == RegistryValidationSeverity.WARNING]
            
            if blocking:
                print(f"::error::{len(blocking)} blocking issues found:")
                for issue in blocking:
                    print(f"  - {issue.contract_ref}: {issue.message} ({issue.field})")
            
            if warnings:
                print(f"::warning::{len(warnings)} non-blocking warnings:")
                for issue in warnings:
                    print(f"  - {issue.contract_ref}: {issue.message} ({issue.field})")
        
        # Validate filesystem consistency
        fs_result = registry.validate_filesystem_consistency()
        
        if fs_result.valid:
            print("::notice::Filesystem consistency validated")
        else:
            print(f"::error::Filesystem consistency issues found:")
            for issue in fs_result.issues:
                print(f"  - {issue.contract_ref}: {issue.message} ({issue.field})")
        
        # Determine overall result
        has_errors = not validation_result.valid or not fs_result.valid
        
        if has_errors:
            print("::error::Contract registry validation failed")
            return 1
        else:
            print("::notice::Contract registry validation passed")
            print(f"registry_hash={registry.registry_hash}")
            return 0
            
    except Exception as e:
        print(f"::error::Contract registry validation failed with exception: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())