"""Fetch stock footage from Pixabay / Pexels (one set of clips per scene), or use a local folder."""
import random
from pathlib import Path

import requests

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
_ORIENT = {"9:16": "portrait", "16:9": "landscape", "1:1": "square"}
_search_cache: dict = {}


def _fits(w, h, aspect):
    if aspect == "9:16":
        return h > w
    if aspect == "16:9":
        return w > h
    return True


def _pexels(term, key, aspect):
    r = requests.get("https://api.pexels.com/videos/search",
                     params={"query": term, "per_page": 20, "orientation": _ORIENT[aspect]},
                     headers={"Authorization": key}, timeout=30)
    r.raise_for_status()
    out = []
    for v in r.json().get("videos", []):
        files = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width")]
        if not files:
            continue
        hd = sorted([f for f in files if min(f["width"], f["height"]) >= 1000], key=lambda f: f["width"])
        best = hd[0] if hd else max(files, key=lambda f: f["width"])
        out.append({"id": f"pexels_{v['id']}", "url": best["link"], "duration": v.get("duration", 0),
                    "fits": _fits(best["width"], best["height"], aspect)})
    return out


def _pixabay(term, key, aspect):
    r = requests.get("https://pixabay.com/api/videos/",
                     params={"key": key, "q": term, "per_page": 40, "safesearch": "true"}, timeout=30)
    r.raise_for_status()
    out = []
    for h in r.json().get("hits", []):
        vids = h.get("videos", {})
        best = next((vids[k] for k in ("large", "medium") if vids.get(k, {}).get("url")), None)
        if best:
            out.append({"id": f"pixabay_{h['id']}", "url": best["url"], "duration": h.get("duration", 0),
                        "fits": _fits(best.get("width", 16), best.get("height", 9), aspect)})
    return out


def _search(cfg, term):
    source = cfg.get("video_source", "pixabay")
    aspect = cfg.get("aspect", "9:16")
    ck = (source, term, aspect)
    if ck not in _search_cache:
        key = cfg.get(f"{source}_api_key", "")
        if not key:
            raise RuntimeError(f"Add your {source.title()} API key in Settings (it's free).")
        fn = _pexels if source == "pexels" else _pixabay
        items = fn(term, key, aspect)
        # clips already in the right orientation first (no heavy cropping), then the rest
        _search_cache[ck] = [i for i in items if i["fits"]] + [i for i in items if not i["fits"]]
    return _search_cache[ck]


def _download(item, cache: Path):
    dst = cache / f"{item['id']}.mp4"
    if dst.exists() and dst.stat().st_size > 0:
        return dst
    try:
        with requests.get(item["url"], stream=True, timeout=90) as r:
            r.raise_for_status()
            tmp = dst.with_suffix(".part")
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(1 << 16):
                    f.write(chunk)
            tmp.replace(dst)
        return dst
    except requests.RequestException:
        return None


def clips_for_scenes(cfg, scenes, cache: Path, log=print):
    """scenes: [{"text", "terms", "duration"}] -> list of clip lists, one per scene."""
    clip_len = float(cfg.get("clip_duration", 3))

    if cfg.get("video_source") == "local":
        folder = Path(cfg.get("local_clips_dir") or "")
        clips = [p for p in folder.glob("**/*") if p.suffix.lower() in VIDEO_EXT] if folder.is_dir() else []
        if not clips and not all(sc.get("image") for sc in scenes):
            raise RuntimeError(f"No video files found in folder: {folder}")
        random.shuffle(clips)
        return [[Path(sc["image"])] if sc.get("image") else (clips[i::len(scenes)] or clips)
                for i, sc in enumerate(scenes)]

    cache.mkdir(parents=True, exist_ok=True)
    used, result = set(), []
    for n, sc in enumerate(scenes, 1):
        if sc.get("image"):  # the user's own picture fills this scene
            result.append([Path(sc["image"])])
            continue
        need = max(1, round(sc["duration"] / clip_len))
        picked = []
        for term in sc["terms"]:
            try:
                items = _search(cfg, term)
            except requests.RequestException as e:
                log(f"⚠️ search failed for '{term}': {e}")
                continue
            for it in items:
                if len(picked) >= need:
                    break
                if it["id"] in used or it["duration"] < min(clip_len, sc["duration"]):
                    continue
                p = _download(it, cache)
                if p:
                    used.add(it["id"])
                    picked.append(p)
            if len(picked) >= need:
                break
        log(f"⬇️ scene {n}: {len(picked)} clip(s)")
        result.append(picked)

    # a scene with no matches borrows clips from its neighbours
    pool = [p for clips in result for p in clips if p.suffix.lower() in VIDEO_EXT]
    if not pool and not all(result):
        raise RuntimeError("No matching clips were found. Try different English search terms.")
    for i, clips in enumerate(result):
        if not clips:
            result[i] = [pool[i % len(pool)]]
    return result
