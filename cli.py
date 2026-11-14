"""Command-line use:
  python cli.py "video subject" [--aspect 16:9] [--script-file s.txt]
  python cli.py --ayah 2:255-257 [--reciter Husary_128kbps] [--translation ar.muyassar]   (Ayah video)"""
import argparse
import sys

from app import pipeline
from app.config import load_config

# Windows consoles may not support emoji in the progress messages
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ap = argparse.ArgumentParser(description="AutoShorts: make a short video from a subject")
ap.add_argument("subject", nargs="?", default="")
ap.add_argument("--ayah", help="Ayah video, e.g. 2:255 or 2:255-257 or 112 (a whole surah)")
ap.add_argument("--reciter", help="everyayah.com folder, e.g. Alafasy_128kbps (see app/quran.py)")
ap.add_argument("--translation", choices=["none", "ar.muyassar", "en.sahih"])
ap.add_argument("--background", choices=["gradient", "nature", "my_images", "local"])
ap.add_argument("--aspect", choices=["9:16", "16:9", "1:1"])
ap.add_argument("--voice")
ap.add_argument("--script-file", help="use this script instead of AI writing one")
ap.add_argument("--terms", help="comma-separated English search terms")
ap.add_argument("--no-subtitles", action="store_true")
a = ap.parse_args()

cfg = load_config()
if a.aspect:
    cfg["aspect"] = a.aspect
if a.voice:
    cfg["voice"] = a.voice
if a.no_subtitles:
    cfg["subtitles"] = False
if a.ayah:
    from app import quran
    surah, start, end = quran.parse_ref(a.ayah)
    for key, val in (("quran_reciter", a.reciter), ("quran_translation", a.translation),
                     ("quran_background", a.background)):
        if val:
            cfg[key] = val
    res = pipeline.run_quran(cfg, surah, start, end)
    print(res["title"])
    sys.exit(0)
if not a.subject:
    ap.error("write the video subject, or use --ayah")
script = open(a.script_file, encoding="utf-8").read() if a.script_file else ""
terms = [t.strip() for t in a.terms.split(",")] if a.terms else None
pipeline.run(cfg, a.subject, script, terms)
