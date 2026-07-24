from config import LORE_DIR


def load_lore(filenames: list[str] | None = None) -> str:
    if filenames is None:
        files = sorted(LORE_DIR.glob("*.md"))
    else:
        files = [LORE_DIR / name for name in filenames]

    return "\n\n---\n\n".join(f.read_text() for f in files)
