"""
Constants for infrastructure layer.
"""
from typing import Final

# File Operation Constants
MAX_FILE_RETRIES: Final[int] = 3
RETRY_DELAY_SEC: Final[float] = 0.5
CHECKSUM_CHUNK_SIZE: Final[int] = 8192
