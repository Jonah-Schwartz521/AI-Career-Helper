import os 
import hashlib

def read_file(path: str) -> str:
    """
    Read a UTF-8 text file and return its content.
    Raises FileNotFoundError with a clear message if missing.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found {path}")
    with open(path, 'r', encoding = 'utf-8')  as f:
        return f.read()
    
def ensure_dir(path: str) -> None:
    """
    Ensure that a directory exists. Create if necesary.
    """
    os.makedirs(path, exist_ok=True)

def sha256_text(text: str) -> str:
    """
    Return a short SHA256 hex digest for logging/reproducibility.
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()