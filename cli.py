"""Command-line use:  python cli.py "video subject" [--aspect 16:9] [--script-file s.txt]"""
import argparse

from app import pipeline
from app.config import load_config

ap = argparse.ArgumentParser(description="AutoShorts: make a short video from a subject")
ap.add_argument("subject")
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
script = open(a.script_file, encoding="utf-8").read() if a.script_file else ""
terms = [t.strip() for t in a.terms.split(",")] if a.terms else None
pipeline.run(cfg, a.subject, script, terms)
