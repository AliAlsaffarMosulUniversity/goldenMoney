"""Automatic checks for each task. Each checker returns {check_name: value in [0, 1]}.

The automatic score of an output is the mean of its check values.
Model-generated code (ffmpeg command, Python function) runs in a temporary
directory, in a subprocess, with a timeout.
"""
import io
import json
import re
import shlex
import subprocess
import sys
import tempfile
import textwrap
import xml.etree.ElementTree as ET

FENCE = re.compile(r"```([A-Za-z0-9_+-]*)[ \t]*\n(.*?)```", re.S)


def blocks(text: str, lang: str | None = None) -> list[str]:
    found = [(l.lower(), body) for l, body in FENCE.findall(text)]
    return [b for l, b in found if lang is None or l == lang]


# ---------------------------------------------------------------- report
REPORT_DATA = {"North": [120, 135, 150, 170], "South": [95, 90, 88, 101],
               "East": [140, 152, 149, 160], "West": [60, 72, 85, 99]}
HEADINGS = ["Summary", "Key figures", "Risks", "Recommendations"]


def _numbers(s: str) -> set[str]:
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", s)}


def check_report(text: str) -> dict:
    heads = [h.strip() for h in re.findall(r"^##\s+(.+)$", text, re.M)]
    words = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'.,%-]*", re.sub(r"[#*|`>-]", " ", text)))
    m = re.search(r"^##\s+Key figures\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    key = m.group(1) if m else ""
    nums = _numbers(key)
    totals = {r: sum(v) for r, v in REPORT_DATA.items()}
    region_hits = sum(str(t) in nums for t in totals.values()) / len(totals)
    company = str(sum(totals.values()))
    return {
        "headings_exact_order": float(heads == HEADINGS),
        "length_250_450_words": float(250 <= words <= 450),
        "regional_totals_correct": region_hits,
        "company_total_correct": float(company in nums),
    }


# ---------------------------------------------------------------- video
SRT_TIME = r"(\d{2}):(\d{2}):(\d{2}),(\d{3})"


def _secs(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def _srt_ok(srt: str) -> bool:
    cues = [c for c in re.split(r"\n\s*\n", srt.strip()) if c.strip()]
    if not cues:
        return False
    last = -1.0
    for c in cues:
        lines = c.strip().splitlines()
        if len(lines) < 3 or not lines[0].strip().isdigit():
            return False
        t = re.fullmatch(SRT_TIME + r" --> " + SRT_TIME, lines[1].strip())
        if not t:
            return False
        a, b = _secs(*t.groups()[:4]), _secs(*t.groups()[4:])
        if not (0 <= a < b <= 30) or a < last:
            return False
        last = b
    return True


def _probe(path: str) -> tuple[float, int, int]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:format=duration", "-of", "json", path],
        capture_output=True, text=True, timeout=30).stdout
    info = json.loads(out)
    st = info["streams"][0]
    return float(info["format"]["duration"]), st["width"], st["height"]


def check_video(text: str) -> dict:
    js, srt, sh = blocks(text, "json"), blocks(text, "srt"), blocks(text, "bash") + blocks(text, "sh")
    r = {"three_blocks_present": float(bool(js and srt and sh)),
         "storyboard_schema_valid": 0.0, "durations_sum_30": 0.0,
         "srt_valid": float(bool(srt) and _srt_ok(srt[0])),
         "ffmpeg_renders": 0.0, "render_30s_1080x1920": 0.0}
    try:
        board = json.loads(js[0])
        shots = board["shots"]
        ok = (isinstance(board.get("title"), str) and len(shots) == 5
              and [s["id"] for s in shots] == [1, 2, 3, 4, 5]
              and all(isinstance(s[k], str) for s in shots for k in ("visual", "on_screen_text", "narration"))
              and all(len(s["on_screen_text"]) <= 42 for s in shots))
        r["storyboard_schema_valid"] = float(ok)
        r["durations_sum_30"] = float(abs(sum(float(s["duration_s"]) for s in shots) - 30) < 0.01)
    except Exception:
        pass
    if sh:
        cmd = " ".join(l.rstrip("\\").strip() for l in sh[0].strip().splitlines())
        try:
            argv = shlex.split(cmd)
        except ValueError:
            argv = []
        if argv and argv[0] == "ffmpeg":
            with tempfile.TemporaryDirectory() as d:
                try:
                    subprocess.run(argv + ["-y"] if "-y" not in argv else argv, cwd=d,
                                   capture_output=True, timeout=180)
                    dur, w, h = _probe(f"{d}/out.mp4")
                    r["ffmpeg_renders"] = 1.0
                    r["render_30s_1080x1920"] = float(abs(dur - 30) <= 1.5 and (w, h) == (1080, 1920))
                except Exception:
                    pass
    return r


# ---------------------------------------------------------------- image
FORBIDDEN = {"image", "script", "style", "text", "foreignObject"}


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _svg_checks(svg: str) -> dict:
    import cairosvg
    from PIL import Image
    r = {"parses": 0.0, "viewbox_24": 0.0, "no_forbidden": 0.0, "style_spec": 0.0, "renders_visible": 0.0}
    try:
        root = ET.fromstring(svg.strip())
    except ET.ParseError:
        return r
    r["parses"] = 1.0
    r["viewbox_24"] = float(re.sub(r"[\s,]+", " ", root.get("viewBox", "")).strip() == "0 0 24 24")
    tags = {_local(e.tag) for e in root.iter()}
    hrefs = [v for e in root.iter() for k, v in e.attrib.items() if k.endswith("href")]
    r["no_forbidden"] = float(not (tags & FORBIDDEN) and not any(not h.startswith("#") for h in hrefs))
    attrs = " ".join(f'{k}="{v}"' for e in root.iter() for k, v in e.attrib.items())
    r["style_spec"] = float(all(s in attrs for s in ('stroke-width="2"', 'stroke="currentColor"',
                                                       'stroke-linecap="round"', 'stroke-linejoin="round"')))
    try:
        png = cairosvg.svg2png(bytestring=svg.replace("currentColor", "#000").encode(), output_width=96, output_height=96)
        alpha = Image.open(io.BytesIO(png)).convert("RGBA").getchannel("A")
        r["renders_visible"] = float(alpha.getbbox() is not None)
    except Exception:
        pass
    return r


def check_image(text: str) -> dict:
    svgs = blocks(text, "svg") or blocks(text, "xml")
    r = {"five_icons": float(len(svgs) == 5)}
    per = [_svg_checks(s) for s in svgs[:5]] + [None] * (5 - len(svgs[:5]))
    for key in ("parses", "viewbox_24", "no_forbidden", "style_spec", "renders_visible"):
        r[key] = sum(p[key] for p in per if p) / 5
    return r


# ---------------------------------------------------------------- code
CODE_CASES = [
    ("1h30m", 5400), ("45s", 45), ("2H", 7200), ("1h 5m 10s", 3910), (" 3m ", 180),
    ("0s", 0), ("1H2M3S", 3723), ("10m5s", 605), ("100h", 360000), ("1h 0m", 3600),
    ("", ValueError), ("   ", ValueError), ("5", ValueError), ("h", ValueError),
    ("1x", ValueError), ("1h1h", ValueError), ("1m1h", ValueError), ("-5s", ValueError),
    ("1.5h", ValueError), ("1h-5m", ValueError), ("1hm", ValueError), ("abc", ValueError),
    ("5s 3m", ValueError), ("1h 2", ValueError),
]

RUNNER = textwrap.dedent("""
    import json, sys
    sys.path.insert(0, '.')
    from solution import parse_duration
    cases = json.loads(sys.argv[1])
    res = []
    for inp, exp in cases:
        try:
            got = parse_duration(inp)
            res.append(exp != 'ValueError' and got == exp)
        except ValueError:
            res.append(exp == 'ValueError')
        except Exception:
            res.append(False)
    print(json.dumps(res))
""")


def check_code(text: str) -> dict:
    py = blocks(text, "python") or blocks(text, "py")
    r = {"single_python_block": float(len(py) == 1), "compiles": 0.0, "hidden_tests_pass_rate": 0.0}
    if not py:
        return r
    try:
        compile(py[0], "solution.py", "exec")
        r["compiles"] = 1.0
    except SyntaxError:
        return r
    cases = [(i, "ValueError" if e is ValueError else e) for i, e in CODE_CASES]
    with tempfile.TemporaryDirectory() as d:
        open(f"{d}/solution.py", "w").write(py[0])
        open(f"{d}/runner.py", "w").write(RUNNER)
        try:
            out = subprocess.run([sys.executable, "-I", "runner.py", json.dumps(cases)], cwd=d,
                                 capture_output=True, text=True, timeout=30).stdout
            res = json.loads(out.strip().splitlines()[-1])
            r["hidden_tests_pass_rate"] = sum(res) / len(res)
        except Exception:
            pass
    return r


CHECKERS = {"report": check_report, "video": check_video, "image": check_image, "code": check_code}


def score(domain: str, text: str) -> tuple[float, dict]:
    detail = CHECKERS[domain](text)
    return sum(detail.values()) / len(detail), detail
