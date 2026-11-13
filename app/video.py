"""Video assembly with FFmpeg: slow camera moves, smooth transitions, subtitles, music."""
import random
import re
import shutil
import subprocess
from pathlib import Path

from .config import FONTS_DIR

SIZES = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}
FPS = 30
XFADE = 0.35
_TRANSITIONS = ["fade", "smoothleft", "fade", "smoothup", "fade", "circleopen", "fade", "smoothright"]


def ffmpeg_bin() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        raise RuntimeError("FFmpeg was not found. Install it (see README) and try again.") from e


def _run(args: list, cwd: Path | None = None) -> str:
    p = subprocess.run([ffmpeg_bin(), "-hide_banner", "-y", *map(str, args)],
                       cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError("FFmpeg error:\n" + p.stderr[-2000:])
    return p.stderr


def duration(path) -> float:
    p = subprocess.run([ffmpeg_bin(), "-hide_banner", "-i", str(path)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", p.stderr)
    if not m:
        raise RuntimeError(f"Could not read duration of {path}")
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def _motion(w: int, h: int, length: float, i: int) -> str:
    """Scale to cover the frame (plus margin), then slowly pan across it — a gentle 'Ken Burns' move."""
    mw, mh = int(w * 1.12) // 2 * 2, int(h * 1.12) // 2 * 2
    d = max(length, 0.1)
    moves = [
        (f"(iw-ow)*t/{d:.3f}", "(ih-oh)/2"),          # pan right
        (f"(iw-ow)*(1-t/{d:.3f})", "(ih-oh)/2"),      # pan left
        ("(iw-ow)/2", f"(ih-oh)*t/{d:.3f}"),          # pan down
        ("(iw-ow)/2", f"(ih-oh)*(1-t/{d:.3f})"),      # pan up
    ]
    x, y = moves[i % len(moves)]
    return (f"scale={mw}:{mh}:force_original_aspect_ratio=increase,crop={mw}:{mh},"
            f"crop={w}:{h}:x='{x}':y='{y}',setsar=1,fps={FPS},"
            f"eq=contrast=1.06:saturation=1.15,format=yuv420p")


def _segment(src: Path, out: Path, length: float, w: int, h: int, i: int) -> None:
    try:
        src_len = duration(src)
    except RuntimeError:
        src_len = 0
    if src_len < 0.5:
        raise RuntimeError(f"bad clip {src}")
    loop = ["-stream_loop", "-1"] if src_len < length else []
    start = random.uniform(0, src_len - length - 0.2) if src_len > length + 0.5 else 0
    _run([*loop, "-ss", f"{start:.3f}", "-i", src, "-t", f"{length:.3f}", "-vf", _motion(w, h, length, i),
          "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", FPS, out])


def build_track(scene_clips: list[list[Path]], scene_durs: list[float], aspect: str, clip_len: float,
                work: Path, log=print) -> Path:
    """One or more clips per scene, cut to the scene's length, joined with smooth transitions."""
    w, h = SIZES[aspect]
    segs_dir = work / "segments"
    segs_dir.mkdir(exist_ok=True)
    plan = []  # (clip, visible_length)
    for clips, dur in zip(scene_clips, scene_durs):
        n = max(1, min(len(clips), round(dur / clip_len)))
        for k in range(n):
            plan.append((clips[k % len(clips)], dur / n))

    segs, lengths = [], []
    for i, (clip, length) in enumerate(plan):
        seg = segs_dir / f"seg_{i:03d}.mp4"
        # each segment is longer by the transition overlap so the timeline stays in sync with the voice
        _segment(clip, seg, length + XFADE, w, h, i)
        segs.append(seg)
        lengths.append(length)
        log(f"🎞️ clip {i + 1}/{len(plan)}")

    out = work / "track.mp4"
    if len(segs) == 1:
        shutil.copy(segs[0], out)
        return out
    inputs, chain, prev, offset = [], [], "0:v", 0.0
    for i, seg in enumerate(segs):
        inputs += ["-i", f"segments/{seg.name}"]
    for i in range(1, len(segs)):
        offset += lengths[i - 1]
        tr = _TRANSITIONS[i % len(_TRANSITIONS)]
        label = f"v{i}"
        chain.append(f"[{prev}][{i}:v]xfade=transition={tr}:duration={XFADE}:offset={offset:.3f}[{label}]")
        prev = label
    log("🔀 adding transitions…")
    _run([*inputs, "-filter_complex", ";".join(chain), "-map", f"[{prev}]", "-c:v", "libx264",
          "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", out.name], cwd=work)
    return out


def concat_audio(parts: list[Path], out: Path) -> None:
    listing = out.parent / "voice_parts.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    _run(["-f", "concat", "-safe", "0", "-i", listing.name, "-c:a", "pcm_s16le", out.name], cwd=out.parent)


def to_wav(src: Path, dst: Path) -> None:
    _run(["-i", src, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", dst])


def final_mix(track: Path, voice: Path, ass: Path | None, bgm: Path | None, out: Path,
              total: float, voice_vol: float, bgm_vol: float) -> Path:
    """Burn subtitles and mix voice + background music (music dips while the voice speaks).
    Runs inside the task folder so paths stay relative (avoids Windows drive-letter escaping problems)."""
    work = out.parent
    inputs = ["-i", track.name, "-i", voice.name]
    if bgm:
        local_bgm = work / ("bgm" + bgm.suffix)
        if bgm.resolve() != local_bgm.resolve():
            shutil.copy(bgm, local_bgm)
        inputs += ["-stream_loop", "-1", "-i", local_bgm.name]

    if ass:
        fonts = work / "fonts"
        if not fonts.exists():
            fonts.mkdir()
            for f in FONTS_DIR.glob("*.[ot]tf"):
                shutil.copy(f, fonts / f.name)
        vchain = f"[0:v]subtitles={ass.name}:fontsdir=fonts,fade=t=out:st={max(0, total - 0.6):.2f}:d=0.6[v]"
    else:
        vchain = f"[0:v]fade=t=out:st={max(0, total - 0.6):.2f}:d=0.6[v]"

    fade_st = max(0.0, total - 2)
    if bgm:
        achain = (f"[1:a]volume={voice_vol},apad,asplit=2[va][sc];"
                  f"[2:a]volume={bgm_vol},afade=t=in:d=1,afade=t=out:st={fade_st:.2f}:d=2[ba];"
                  f"[ba][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[duck];"
                  f"[va][duck]amix=inputs=2:duration=first:normalize=0[a]")
    else:
        achain = f"[1:a]volume={voice_vol},apad[a]"

    _run([*inputs, "-filter_complex", f"{vchain};{achain}", "-map", "[v]", "-map", "[a]",
          "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
          "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out.name], cwd=work)
    return out
