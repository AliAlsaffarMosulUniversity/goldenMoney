"""The user's own pictures (with descriptions) and logos, kept between sessions."""
import json
import re
from pathlib import Path

from .config import ROOT

IMAGES_DIR = ROOT / "resource" / "my_images"
LOGOS_DIR = ROOT / "resource" / "logos"
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
_INDEX = IMAGES_DIR / "images.json"


def _safe_name(name: str) -> str:
    stem, ext = Path(name).stem, Path(name).suffix.lower()
    stem = re.sub(r"[^\w\-]+", "_", stem, flags=re.UNICODE).strip("_") or "image"
    return stem[:60] + ext


def _unique(folder: Path, name: str) -> Path:
    p = folder / _safe_name(name)
    n = 1
    while p.exists():
        p = folder / f"{Path(_safe_name(name)).stem}_{n}{p.suffix}"
        n += 1
    return p


# ---------- pictures with descriptions ----------
def _read_index() -> dict:
    try:
        return json.loads(_INDEX.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_index(data: dict) -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    _INDEX.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_images() -> list[dict]:
    """[{"name", "path", "desc", "enabled"}] for pictures that still exist on disk."""
    idx = _read_index()
    out = []
    for p in sorted(IMAGES_DIR.glob("*")) if IMAGES_DIR.exists() else []:
        if p.suffix.lower() in IMAGE_EXT:
            meta = idx.get(p.name, {})
            out.append({"name": p.name, "path": p, "desc": meta.get("desc", ""), "enabled": meta.get("enabled", True)})
    return out


def add_image(filename: str, data: bytes, desc: str = "") -> str:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    p = _unique(IMAGES_DIR, filename)
    p.write_bytes(data)
    idx = _read_index()
    idx[p.name] = {"desc": desc, "enabled": True}
    _write_index(idx)
    return p.name


def update_image(name: str, desc: str | None = None, enabled: bool | None = None) -> None:
    idx = _read_index()
    meta = idx.setdefault(name, {"desc": "", "enabled": True})
    if desc is not None:
        meta["desc"] = desc
    if enabled is not None:
        meta["enabled"] = enabled
    _write_index(idx)


def delete_image(name: str) -> None:
    (IMAGES_DIR / name).unlink(missing_ok=True)
    idx = _read_index()
    idx.pop(name, None)
    _write_index(idx)


# ---------- logos ----------
def list_logos() -> list[Path]:
    return sorted(p for p in LOGOS_DIR.glob("*") if p.suffix.lower() in IMAGE_EXT) if LOGOS_DIR.exists() else []


def add_logo(filename: str, data: bytes) -> str:
    LOGOS_DIR.mkdir(parents=True, exist_ok=True)
    p = _unique(LOGOS_DIR, filename)
    p.write_bytes(data)
    return p.name


def delete_logo(name: str) -> None:
    (LOGOS_DIR / name).unlink(missing_ok=True)


# ---------- matching pictures to scenes without AI ----------
_WORD = re.compile(r"\w+", re.UNICODE)


def _words(text: str) -> set[str]:
    out = set()
    for w in _WORD.findall(text.lower()):
        w = re.sub(r"^(وال|بال|كال|فال|لل|ال|و)", "", w) if len(w) > 4 else w   # light Arabic prefix trim
        if len(w) > 2:
            out.add(w)
    return out


def match_by_words(sentences: list[str], images: list[dict]) -> list[int | None]:
    """Fallback: each picture goes to the sentence sharing the most words with its description;
    pictures with no overlap fill the remaining scenes in order, so every picture is shown."""
    result: list[int | None] = [None] * len(sentences)
    left = []
    for i, img in enumerate(images):
        dw = _words(img["desc"])
        best, score = None, 0
        for s, text in enumerate(sentences):
            sc = len(dw & _words(text))
            if result[s] is None and sc > score:
                best, score = s, sc
        if best is None:
            left.append(i)
        else:
            result[best] = i
    for i in left:
        free = [s for s in range(len(sentences)) if result[s] is None]
        if not free:
            break
        result[free[0]] = i
    return result
