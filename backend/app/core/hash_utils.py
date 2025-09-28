import hashlib
import hmac
from pathlib import Path 

def verify_sha256(file_path: Path, expected_hash: str) -> bool:
    """
    Compute the SHA-256 hash of a file and compare it with an expected hash.

    Args:
        file_path (str | Path): Path to the file to hash.
        expected_hash (str): Expected SHA-256 hash in hexadecimal.

    Returns:
        bool: True if the file's SHA-256 matches the expected hash, else False.
    """
    file_path = Path(file_path)

    sha256 = hashlib.sha256() 

    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""): # We go through the file in 8KB chunks, we avoid loading the entire file into memory.
            sha256.update(chunk) # We update the hash object with the chunk.
    computed = sha256.hexdigest() # We get the hexadecimal representation of the hash.

    return hmac.compare_digest(computed.lower(), expected_hash.lower())

def compute_sha256(file_path: Path) -> str:
    """
    Compute the SHA-256 hash of a file.

    Args:
        file_path (str | Path): Path to the file to hash.

    Returns:
        str: The SHA-256 hash of the file in hexadecimal.
    """
    file_path = Path(file_path)

    sha256 = hashlib.sha256()

    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
