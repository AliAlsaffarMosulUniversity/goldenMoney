"""TikTok-style subtitles: short word groups, bold text, the spoken word highlighted."""
import re

_END = re.compile(r"[.!?؟،,;:…]$")
_RTL = re.compile(r"[\u0590-\u08FF]")
_STRIP = re.compile(r"^[\"'«»“”(]+|[\"'«»“”).!?؟،,;:…]+$")


def _chunks(words, max_words):
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or _END.search(w["text"]):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def _ts(sec):
    cs = int(round(max(sec, 0) * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _col(hex_color):
    h = hex_color.lstrip("#").ljust(6, "0")
    return f"&H{h[4:6]}{h[2:4]}{h[0:2]}&".upper()


def write_ass(words, path, width, height, cfg):
    portrait = height > width
    size = int(cfg.get("font_size") or (width * (0.085 if portrait else 0.055)))
    max_words = 3 if portrait else 5
    pos = cfg.get("subtitle_position", "bottom")
    align = {"bottom": 2, "center": 5, "top": 8}.get(pos, 2)
    margin_v = int(height * (0.28 if portrait else 0.10)) if pos != "center" else 0
    base = _col(cfg.get("font_color", "#FFFFFF"))
    hi = _col(cfg.get("highlight_color", "#FFD400"))
    outline_c = _col(cfg.get("outline_color", "#000000")).replace("&H", "&H00").rstrip("&")
    font = cfg.get("font_name", "Arial")

    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},{base.replace('&H', '&H00').rstrip('&')},&H000000FF,{outline_c},&H96000000,-1,0,0,0,100,100,0,0,1,{max(3, size // 11)},{max(2, size // 25)},{align},{int(width*0.07)},{int(width*0.07)},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for chunk in _chunks(words, max_words):
        texts = [_STRIP.sub("", w["text"]).replace("{", "").replace("}", "") or w["text"] for w in chunk]
        end_all = chunk[-1]["end"] + 0.1
        for k, w in enumerate(chunk):
            start = w["start"]
            end = chunk[k + 1]["start"] if k + 1 < len(chunk) else end_all
            # every word is its own colour run; libass lays runs out left-to-right,
            # so for Arabic/Hebrew we put the words in reverse order ourselves.
            # the alternating, invisible 1/255 alpha keeps libass from merging same-colour words
            parts = [f"{{\\c{hi if j == k else base}\\1a&H0{j % 2}&}}{t}" for j, t in enumerate(texts)]
            if _RTL.search("".join(texts)):
                parts.reverse()
            pop = r"{\fscx85\fscy85\t(0,90,\fscx100\fscy100)}" if k == 0 else ""
            events.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Default,,0,0,0,,{pop}{' '.join(parts)}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(events) + "\n")
