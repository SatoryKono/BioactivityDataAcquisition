"""
Validation helpers module for common validation operations.
"""

from typing import Any


def validate_data(data: Any) -> None:
    """Validate that data is not empty.
    
    Args:
        data: Data to validate.
        
    Raises:
        ValueError: If data is empty.
    """
    if not data:
        raise ValueError("Data is empty")
