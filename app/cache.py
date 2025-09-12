import hashlib
import pickle
from pathlib import Path
from typing import Optional

CACHE_DIR = Path(__file__).resolve().parent.parent / '.cache'
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _meta_for(path: Path) -> str:
    try:
        st = path.stat()
        return f"{int(st.st_mtime)}-{st.st_size}"
    except Exception:
        return "no-meta"


def _cache_path_for(path: Path) -> Path:
    key = str(path.resolve()).encode('utf-8') + b'|' + _meta_for(path).encode('utf-8')
    h = hashlib.sha256(key).hexdigest()
    return CACHE_DIR / f"{h}.pkl"


def load_df(path: Path):
    """Load DataFrame from cache if available. Returns None if not cached."""
    cache_file = _cache_path_for(path)
    if cache_file.exists():
        try:
            with open(cache_file, 'rb') as fh:
                return pickle.load(fh)
        except Exception:
            try:
                cache_file.unlink()
            except Exception:
                pass
    return None


def save_df(path: Path, df) -> None:
    cache_file = _cache_path_for(path)
    try:
        with open(cache_file, 'wb') as fh:
            pickle.dump(df, fh)
    except Exception:
        try:
            cache_file.unlink()
        except Exception:
            pass
