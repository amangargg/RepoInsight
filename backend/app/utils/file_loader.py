import os

def read_file_safely(abs_path: str) -> str:
    """Read a file's content safely supporting common encodings."""
    if not os.path.exists(abs_path) or os.path.isdir(abs_path):
        return ""
    for encoding in ('utf-8', 'latin-1', 'utf-16'):
        try:
            with open(abs_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    return ""
