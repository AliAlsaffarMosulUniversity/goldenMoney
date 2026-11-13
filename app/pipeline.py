"""End-to-end: subject -> scenes (sentence + search terms) -> voice -> subtitles -> footage -> video."""
import json
import random
import re
import time
from pathlib import Path

from . import llm, materials, subtitles, tts, video
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

    # 1) scenes: from the AI, or from the user's own script + ordered search terms
    title, scenes = "", None
    if not script.strip():
        log("✍️ writing the script with AI…")
        res = llm.generate_script(cfg, subject)
        title, script = res["title"], res["script"]
        scenes = res.get("scenes") or split_scenes(script, res.get("search_terms") or [subject])
    if scenes is None:
        scenes = split_scenes(script, terms or [])
        if not terms and cfg.get("video_source") != "local":
            log("🧠 understanding the script to choose matching footage…")
            try:
                per_scene = llm.terms_for_scenes(cfg, subject, [s["text"] for s in scenes])
            except RuntimeError as e:
                raise RuntimeError("لم أستطع فهم السكربت لاختيار المقاطع، لأن الذكاء الاصطناعي لا يعمل:\n" + str(e)
                                   + "\n\nأصلح إعدادات الذكاء الاصطناعي، أو اكتب كلمات البحث يدوياً في «خيارات متقدمة».") from e
            pool = [t for ts in per_scene for t in ts]
            for sc, ts in zip(scenes, per_scene):
                sc["terms"] = ts + [t for t in pool if t not in ts]
        for sc in scenes:
            sc["terms"] = sc["terms"] or [subject]
    for i, sc in enumerate(scenes, 1):
        log(f"🎬 scene {i}: {sc['text'][:60]}  →  {sc['terms'][0]}")

    # 2) voice-over, one sentence at a time (exact timing for each scene)
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

    # 3) subtitles
    ass = None
    if cfg.get("subtitles", True) and words:
        w, h = video.SIZES[cfg["aspect"]]
        ass = task / "subtitles.ass"
        subtitles.write_ass(words, str(ass), w, h, cfg)
        log("💬 subtitles ready")

    # 4) footage, scene by scene
    log("🔎 collecting footage…")
    scene_clips = materials.clips_for_scenes(cfg, scenes, STORAGE / "cache", log=log)

    # 5) assemble
    log("🛠️ assembling…")
    track = video.build_track(scene_clips, [s["duration"] for s in scenes], cfg["aspect"],
                              float(cfg.get("clip_duration", 3)), task, log=log)
    bgm = _pick_bgm(cfg.get("bgm", "random"))
    if bgm:
        log(f"🎵 music: {bgm.name}")
    log("🔥 rendering final video…")
    out = video.final_mix(track, voice, ass, bgm, task / "final.mp4", total,
                          float(cfg.get("voice_volume", 1.0)), float(cfg.get("bgm_volume", 0.15)))
    log(f"✅ done: {out}")
    return {"video": out, "script": script, "title": title, "terms": terms, "task": task}
