from pathlib import Path


def read_text(path: Path) -> str:
    data = path.read_bytes()
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
