"""End-to-end: subject -> scenes (sentence + search terms) -> voice -> subtitles -> footage -> video."""
import json
import random
import re
import time
from pathlib import Path

from . import assets, llm, materials, subtitles, tts, video
from .config import MUSIC_DIR, STORAGE

AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}


def list_music() -> list[Path]:
    return sorted(p for p in MUSIC_DIR.glob("*") if p.suffix.lower() in AUDIO_EXT)


def _pick_bgm(choice: str) -> Path | None:
    if not choice or choice == "none":
        return None
    tracks = list_music()
    if choice == "random":
        return random.choice(tracks) if tracks else None
    p = MUSIC_DIR / choice
    return p if p.exists() else None


def split_scenes(script: str, terms: list[str]) -> list[dict]:
    """Cut the script into sentences (very short ones are merged) and hand out the
    search terms in order, so the footage follows what is being said."""
    parts = [s.strip() for s in re.split(r"(?<=[.!?؟])\s+|\n+", script) if s.strip()]
    sentences = []
    for p in parts:
        if sentences and len(sentences[-1].split()) < 5:
            sentences[-1] += " " + p
        else:
            sentences.append(p)
    n, m = len(sentences), max(len(terms), 1)
    scenes = []
    for i, s in enumerate(sentences):
        a, b = i * m // n, max((i + 1) * m // n, i * m // n + 1)
        own = terms[a:b] if terms else []
        scenes.append({"text": s, "terms": own + [t for t in terms if t not in own]})
    return scenes


def run(cfg: dict, subject: str, script: str = "", terms: list[str] | None = None, log=print) -> dict:
    task = STORAGE / "tasks" / time.strftime("%Y%m%d-%H%M%S")
    task.mkdir(parents=True, exist_ok=True)
    log(f"📁 task folder: {task}")

    # 1) scenes: one per sentence of the AI's or the user's script
    title = ""
    if not script.strip():
        log("✍️ writing the script with AI…")
        res = llm.generate_script(cfg, subject)
        title = res["title"]
        script = "\n".join(sc["text"] for sc in res["scenes"])
    scenes = split_scenes(script, terms or [])
    sentences = [s["text"] for s in scenes]

    # 2) understand each sentence: footage search terms + which of the user's own pictures fits it
    images = [i for i in assets.list_images() if i["enabled"]] if cfg.get("use_my_images", True) else []
    picks: list = [None] * len(scenes)
    if (not terms and cfg.get("video_source") != "local") or images:
        log("🧠 understanding the script to choose matching footage…")
        try:
            per_scene, picks = llm.terms_for_scenes(cfg, subject, sentences,
                                                    [i["desc"] or Path(i["name"]).stem for i in images])
            if not terms:
                pool = [t for ts in per_scene for t in ts]
                for sc, ts in zip(scenes, per_scene):
                    sc["terms"] = ts + [t for t in pool if t not in ts]
        except RuntimeError as e:
            if not terms and cfg.get("video_source") != "local":
                raise RuntimeError("لم أستطع فهم السكربت لاختيار المقاطع، لأن الذكاء الاصطناعي لا يعمل:\n" + str(e)
                                   + "\n\nأصلح إعدادات الذكاء الاصطناعي، أو اكتب كلمات البحث يدوياً في «خيارات متقدمة».") from e
            log("⚠️ AI unavailable: placing your pictures by matching their descriptions")
            picks = assets.match_by_words(sentences, images)
        # every picture the user added should appear: unplaced ones fill scenes that have none
        placed = {p for p in picks if p is not None}
        unplaced = [k for k in range(len(images)) if k not in placed]
        free = [i for i, p in enumerate(picks) if p is None]
        if unplaced and free:
            extra = assets.match_by_words([sentences[i] for i in free], [images[k] for k in unplaced])
            for slot, j in zip(free, extra):
                if j is not None:
                    picks[slot] = unplaced[j]
    for sc, k in zip(scenes, picks):
        sc["terms"] = sc["terms"] or [subject]
        if k is not None:
            sc["image"], sc["image_desc"] = str(images[k]["path"]), images[k]["desc"]
            log(f"🖼️ your picture «{images[k]['desc'] or images[k]['name']}» → «{sc['text'][:40]}»")

    for i, sc in enumerate(scenes, 1):
        log(f"🎬 scene {i}: {sc['text'][:60]}  →  {'🖼️' if sc.get('image') else sc['terms'][0]}")

    # 3) voice-over, one sentence at a time (exact timing for each scene)
    log("🎙️ generating voice-over…")
    words, wavs, t = [], [], 0.0
    for i, sc in enumerate(scenes):
        mp3, wav = task / f"voice_{i:02d}.mp3", task / f"voice_{i:02d}.wav"
        ws = tts.synthesize(sc["text"], cfg["voice"], int(cfg.get("voice_rate", 0)), str(mp3))
        video.to_wav(mp3, wav)
        d = video.duration(wav)
        words += [{"text": w["text"], "start": w["start"] + t, "end": w["end"] + t} for w in ws]
        sc["duration"] = d
        wavs.append(wav)
        t += d
    voice = task / "voice.wav"
    video.concat_audio(wavs, voice)
    scenes[-1]["duration"] += 0.6          # a short tail after the last word
    total = t + 0.6
    log(f"⏱️ length: {total:.1f}s, {len(scenes)} scenes")
    (task / "scenes.json").write_text(json.dumps({"subject": subject, "title": title, "scenes": scenes},
                                                 ensure_ascii=False, indent=2), encoding="utf-8")

    # 4) subtitles
    ass = None
    if cfg.get("subtitles", True) and words:
        w, h = video.SIZES[cfg["aspect"]]
        ass = task / "subtitles.ass"
        captions, t0 = [], 0.0
        for sc in scenes:
            if sc.get("image") and sc.get("image_desc") and cfg.get("image_captions", False):
                captions.append((t0, t0 + sc["duration"], sc["image_desc"]))
            t0 += sc["duration"]
        subtitles.write_ass(words, str(ass), w, h, cfg, captions)
        log("💬 subtitles ready")

    # 5) footage, scene by scene
    log("🔎 collecting footage…")
    scene_clips = materials.clips_for_scenes(cfg, scenes, STORAGE / "cache", log=log)

    # 6) assemble
    log("🛠️ assembling…")
    track = video.build_track(scene_clips, [s["duration"] for s in scenes], cfg["aspect"],
                              float(cfg.get("clip_duration", 3)), task, log=log)
    bgm = _pick_bgm(cfg.get("bgm", "random"))
    if bgm:
        log(f"🎵 music: {bgm.name}")
    log("🔥 rendering final video…")
    logos = assets.list_logos()[:2] if cfg.get("use_logos", True) else []
    if logos:
        log(f"🏷️ logos: {', '.join(p.name for p in logos)}")
    out = video.final_mix(track, voice, ass, bgm, task / "final.mp4", total,
                          float(cfg.get("voice_volume", 1.0)), float(cfg.get("bgm_volume", 0.15)),
                          logos=logos, logo_size=float(cfg.get("logo_size", 0.14)),
                          logo_corner=cfg.get("logo_corner", "right"))
    log(f"✅ done: {out}")
    return {"video": out, "script": script, "title": title, "terms": terms, "task": task}


# ---------------- Ayah video: Quran recitation with its text on screen ----------------
QURAN_BACKGROUNDS = {
    "gradient": "خلفية هادئة متحركة (لا تحتاج مفاتيح)",
    "nature": "مناظر طبيعية من Pixabay / Pexels",
    "my_images": "صوري الخاصة",
    "local": "مقاطع من مجلد على جهازي",
}
NATURE_TERMS = ["clouds timelapse", "mountains landscape", "ocean waves", "desert dunes", "night sky stars",
                "forest aerial", "waterfall", "sunrise sky", "rain on leaves", "river valley", "snow mountains",
                "green hills", "lake reflection", "sunset clouds", "galaxy stars"]


def quran_title(surah: int, start: int, end: int, reciter: str) -> str:
    from . import quran
    rng = quran.arabic_number(start) if start == end else f"{quran.arabic_number(start)}–{quran.arabic_number(end)}"
    whole = start == 1 and end == quran.ayah_count(surah)
    return f"سورة {quran.surah_name(surah)}" + ("" if whole else f" ({rng})") + f" | {quran.RECITERS.get(reciter, reciter)}"


def run_quran(cfg: dict, surah: int, start: int, end: int, log=print) -> dict:
    """Recitation of ayahs start..end of a surah, with the Uthmani text on screen, ayah by ayah.
    No AI and no music: the text and the recitation come from their sources unchanged."""
    from . import quran

    quran.check_range(surah, start, end)
    task = STORAGE / "tasks" / time.strftime("%Y%m%d-%H%M%S")
    task.mkdir(parents=True, exist_ok=True)
    log(f"📁 task folder: {task}")
    reciter = cfg.get("quran_reciter", "Alafasy_128kbps")
    translation = cfg.get("quran_translation", "none")
    aspect = cfg.get("aspect", "9:16")

    log(f"📖 سورة {quran.surah_name(surah)}، الآيات {start}–{end}")
    ayahs = quran.get_ayahs(surah, start, end, translation)
    scenes = []
    if cfg.get("quran_basmala", True) and quran.wants_basmala(surah, start):
        scenes.append({"surah": 1, "ayah": None, "audio_ayah": 1, "text": quran.basmala(), "translation": ""})
    for a in ayahs:
        scenes.append({"surah": surah, "ayah": a["ayah"], "audio_ayah": a["ayah"], "text": a["text"],
                       "translation": a["translation"]})

    # recitation, one ayah at a time: each ayah stays on screen exactly while it is recited
    log(f"🎙️ التلاوة: {quran.RECITERS.get(reciter, reciter)}")
    wavs, t = [], 0.0
    for i, sc in enumerate(scenes):
        mp3 = quran.recitation(reciter, sc["surah"], sc["audio_ayah"])
        wav = task / f"voice_{i:03d}.wav"
        video.to_wav(mp3, wav)
        sc["start"], sc["duration"] = t, video.duration(wav)
        t += sc["duration"]
        wavs.append(wav)
        log(f"🔊 {i + 1}/{len(scenes)}  ({sc['duration']:.1f}s)")
    voice = task / "voice.wav"
    video.concat_audio(wavs, voice)
    scenes[-1]["duration"] += 1.0
    total = t + 1.0
    log(f"⏱️ length: {total:.1f}s, {len(scenes)} ayah(s)")
    (task / "scenes.json").write_text(json.dumps({"surah": surah, "start": start, "end": end, "reciter": reciter,
                                                  "scenes": scenes}, ensure_ascii=False, indent=2), encoding="utf-8")

    w, h = video.SIZES[aspect]
    ass = task / "subtitles.ass"
    subtitles.write_quran_ass(scenes, str(ass), w, h, {
        "surah": quran.surah_name(surah),
        "reciter": quran.RECITERS.get(reciter, reciter) if cfg.get("quran_show_reciter", True) else "",
        "translation_font": cfg.get("font_name", "Arial"),
        "ayah_scale": float(cfg.get("quran_text_scale", 1.0)),
    })
    log("💬 نص الآيات جاهز")

    background = cfg.get("quran_background", "gradient")
    durs = [sc["duration"] for sc in scenes]
    track = None
    if background == "my_images":
        imgs = [Path(i["path"]) for i in assets.list_images() if i["enabled"]]
        if imgs:
            track = video.build_track([[imgs[i % len(imgs)]] for i in range(len(scenes))], durs, aspect, 8.0, task, log=log)
        else:
            log("⚠️ no pictures added yet: using the calm background")
    elif background in ("nature", "local"):
        bcfg = dict(cfg, clip_duration=max(6, int(cfg.get("clip_duration", 3))))
        if background == "local":
            bcfg["video_source"] = "local"
        elif bcfg.get("video_source") == "local":
            bcfg["video_source"] = "pixabay"
        terms = NATURE_TERMS[:]
        random.shuffle(terms)
        bscenes = [{"text": "", "duration": d, "terms": terms[i % len(terms):] + terms[:i % len(terms)]}
                   for i, d in enumerate(durs)]
        try:
            log("🔎 collecting background footage…")
            clips = materials.clips_for_scenes(bcfg, bscenes, STORAGE / "cache", log=log)
            track = video.build_track(clips, durs, aspect, float(bcfg["clip_duration"]), task, log=log)
        except RuntimeError as e:
            log(f"⚠️ {e} — using the calm background")
    footage = track is not None
    if not footage:
        track = video.gradient_track(aspect, total, task)

    log("🔥 rendering final video…")
    logos = assets.list_logos()[:2] if cfg.get("use_logos", True) else []
    dim = float(cfg.get("quran_dim", 0.45)) if footage else 0.0   # darken footage so the text stays clear
    out = video.final_mix(track, voice, ass, None, task / "final.mp4", total,
                          float(cfg.get("voice_volume", 1.0)), 0.0,
                          logos=logos, logo_size=float(cfg.get("logo_size", 0.14)),
                          logo_corner=cfg.get("logo_corner", "right"), dim=dim)
    title = quran_title(surah, start, end, reciter)
    log(f"✅ done: {out}")
    return {"video": out, "title": title, "task": task, "ayahs": ayahs}
