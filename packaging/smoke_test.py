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
shutil.rmtree(work)
print("SMOKE TEST OK")
