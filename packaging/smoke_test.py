"""CI check on Windows: real Edge TTS voice + subtitles + a rendered video (colour clips, no API keys)."""
import shutil
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import subtitles, tts, video  # noqa: E402

work = Path("storage") / "smoke"
work.mkdir(parents=True, exist_ok=True)
print("ffmpeg:", video.ffmpeg_bin())
words = tts.synthesize("مرحباً، هذا اختبار للأداة على ويندوز", "ar-IQ-BasselNeural", 0, str(work / "v.mp3"))
assert words, "no word timings from Edge TTS"
assert tts.synthesize("اختبار طبقة الصوت", "ar-SA-ZariyahNeural", 10, str(work / "p.mp3"), 5, -10), "pitch/volume failed"
subtitles.write_srt(words, str(work / "v.srt"))
bad = []
for v in tts.VOICES:  # every voice offered in the app must really exist
    try:
        tts.synthesize(tts.sample_text(v)[:25], v, 0, str(work / "s.mp3"))
    except Exception as e:
        bad.append(f"{v}: {e}")
print(f"voices checked: {len(tts.VOICES)}, failed: {len(bad)}")
assert not bad, "\n".join(bad)
video.to_wav(work / "v.mp3", work / "voice.wav")
total = video.duration(work / "voice.wav") + 0.5
subtitles.write_ass(words, str(work / "subtitles.ass"), 1080, 1920, {"font_name": "Arial"})
clips = []
for i, c in enumerate(["red", "blue"]):
    p = work / f"c{i}.mp4"
    subprocess.run([video.ffmpeg_bin(), "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"color=c={c}:s=1280x720:d=5", "-pix_fmt", "yuv420p", str(p)], check=True)
    clips.append(p)
track = video.build_track([[clips[0]], [clips[1]]], [total / 2, total / 2], "9:16", 3, work)
out = video.final_mix(track, work / "voice.wav", work / "subtitles.ass", None, work / "final.mp4", total, 1.0, 0.15)
d = video.duration(out)
print("rendered", out, round(d, 2), "s")
assert abs(d - total) < 0.5

# Ayah video: real Quran text + recitation, rendered with the bundled Amiri Quran font
from app import pipeline, quran  # noqa: E402
from app.config import load_config  # noqa: E402
assert quran.parse_ref("2:255-257") == (2, 255, 257)
assert len(quran.SURAHS) == 114 and sum(c for _, c in quran.SURAHS) == 6236
assert quran.get_ayahs(2, 1, 1)[0]["text"] == "الٓمٓ", "basmala not taken off the first ayah"
for r in quran.RECITERS:   # every reciter offered in the app must have the last ayah of the Quran
    assert quran.recitation(r, 114, 6).stat().st_size > 1000, r
cfg = load_config()
cfg.update(aspect="9:16", quran_translation="ar.muyassar", quran_background="gradient", use_logos=False)
res = pipeline.run_quran(cfg, 112, 1, 4, log=lambda m: None)
d = video.duration(res["video"])
print("ayah video", res["title"], round(d, 2), "s")
assert d > 10
shutil.rmtree(work)
print("SMOKE TEST OK")
