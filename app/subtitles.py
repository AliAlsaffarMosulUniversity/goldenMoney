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


def write_ass(words, path, width, height, cfg, captions=None):
    """captions: optional [(start, end, text)] shown at the top, e.g. descriptions of the user's pictures."""
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
Style: Caption,{font},{int(size * 0.55)},&H00FFFFFF,&H000000FF,&H50000000,&HA0000000,-1,0,0,0,100,100,0,0,3,{max(6, size // 7)},0,8,{int(width*0.08)},{int(width*0.08)},{int(height * (0.13 if portrait else 0.09))},1
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
    for start, end, text in captions or []:
        text = str(text).replace("{", "(").replace("}", ")").replace("\n", " ")
        events.append(f"Dialogue: 1,{_ts(start + 0.2)},{_ts(end - 0.2)},Caption,,0,0,0,,{{\\fad(250,250)}}{text}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(events) + "\n")


def write_srt(words, path, max_words=7):
    """Plain SRT subtitles (for editing software) from word timings."""
    def ts(sec):
        ms = int(round(max(sec, 0) * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    blocks = []
    for n, chunk in enumerate(_chunks(words, max_words), 1):
        text = " ".join(w["text"] for w in chunk)
        blocks.append(f"{n}\n{ts(chunk[0]['start'])} --> {ts(chunk[-1]['end'] + 0.1)}\n{text}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(blocks))


# ---------------- Ayah video: Quran text on screen ----------------
QURAN_FONT = "Amiri Quran"   # resource/fonts/AmiriQuran-Regular.ttf (SIL Open Font License)
QURAN_FONT_SCALE = 1.7       # its tall line spacing makes its letters small for a given font size


def _plain_text(text):
    """Text for an ASS event, shown exactly as given (no override tags, no line breaks)."""
    return str(text).replace("{", "(").replace("}", ")").replace("\\", "/").replace("\n", " ")


def _split_words(text, max_chars):
    """Cut a text into about equal parts of at most ~max_chars, between words (after a full stop when one is near)."""
    words = text.split()
    n = -(-len(text) // max_chars)
    if n <= 1:
        return [text]
    target, out, cur = len(text) / n, [], []
    for w in words:
        cur.append(w)
        size = len(" ".join(cur))
        if len(out) < n - 1 and (size >= target or (size >= target * 0.75 and w[-1] in ".؛:")):
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return out


def write_quran_ass(scenes, path, width, height, opts):
    """scenes: [{"text", "ayah" (None for the basmala), "translation", "start", "duration"}].
    opts: surah (name), reciter (name or ""), translation_font, ayah_scale.
    Each ayah is shown whole while it is recited; a long ayah is shown in screens (split between
    words, timed by length). The text itself is never changed."""
    from . import quran

    portrait, square = height > width, height == width
    max_letters = 80 if portrait else (75 if square else 120)
    base = width * (0.078 if portrait else (0.062 if square else 0.040))
    base *= float(opts.get("ayah_scale", 1.0)) * QURAN_FONT_SCALE
    has_trans = any(sc.get("translation") for sc in scenes)
    tr_max = 380 if portrait else (240 if square else 260)   # characters of translation per screen
    tr_size = int(width * (0.040 if portrait else (0.034 if square else 0.022)))
    head_size = int(width * (0.045 if portrait else (0.038 if square else 0.026)) * QURAN_FONT_SCALE)
    side = int(width * 0.08)
    tfont = opts.get("translation_font", "Arial")
    gold, white = "&H0060C8E8", "&H00FFFFFF"   # ASS colours are BGR

    # with a translation the ayah sits just above the middle and the translation just below it
    if has_trans:
        ayah_align, ayah_mv = 2, int(height * (0.50 if portrait else 0.48))
        tr_mv = int(height * (0.54 if portrait else 0.56))
    else:
        ayah_align, ayah_mv, tr_mv = 5, 0, 0

    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Ayah,{QURAN_FONT},{int(base)},{white},&H000000FF,&H00101010,&H90000000,0,0,0,0,100,100,0,0,1,{max(2, int(base) // 28)},{max(2, int(base) // 18)},{ayah_align},{side},{side},{ayah_mv},-1
Style: Trans,{tfont},{tr_size},&H00E6E6E6,&H000000FF,&H00101010,&H90000000,0,0,0,0,100,100,0,0,1,{max(2, tr_size // 16)},1,8,{side},{side},{tr_mv},-1
Style: Head,{QURAN_FONT},{head_size},{gold},&H000000FF,&H00101010,&H90000000,0,0,0,0,100,100,0,0,1,{max(2, head_size // 16)},1,8,{side},{side},{int(height * (0.10 if portrait else 0.06))},-1
Style: Foot,{tfont},{int(head_size * 0.62 / QURAN_FONT_SCALE)},&H00D0D0D0,&H000000FF,&H00101010,&H90000000,0,0,0,0,100,100,0,0,1,{max(1, head_size // 22)},1,2,{side},{side},{int(height * (0.08 if portrait else 0.05))},-1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    total = sum(sc["duration"] for sc in scenes)
    surah = opts.get("surah", "")
    for sc in scenes:
        t0, dur = sc["start"], sc["duration"]
        text = sc["text"]
        screens = quran.pages(text, max_letters)
        sizes = [max(1, quran.letters(s)) for s in screens]
        t = t0
        for k, (scr, n) in enumerate(zip(screens, sizes)):
            d = dur * n / sum(sizes)
            shown = scr
            if sc.get("ayah") and k == len(screens) - 1:   # ﴿٢٥٥﴾ after the last word of the ayah
                shown += f" \ufd3f{quran.arabic_number(sc['ayah'])}\ufd3e"
            letters = quran.letters(scr)
            fit = 1.0 if letters <= 40 else max(0.8, (40 / letters) ** 0.3)
            size = f"\\fs{int(base * fit)}" if fit < 1 else ""
            ev.append(f"Dialogue: 0,{_ts(t)},{_ts(t + d)},Ayah,,0,0,0,,{{\\fad(220,220){size}}}{_plain_text(shown)}")
            t += d
        if sc.get("translation"):   # a long tafsir is shown in parts, one after the other
            parts = _split_words(sc["translation"], tr_max)
            for k, part in enumerate(parts):
                a, b = t0 + dur * k / len(parts), t0 + dur * (k + 1) / len(parts)
                ev.append(f"Dialogue: 0,{_ts(a)},{_ts(b)},Trans,,0,0,0,,{{\\fad(250,250)}}{_plain_text(part)}")
        if surah:
            label = f"سورة {surah}" + (f" \ufd3f{quran.arabic_number(sc['ayah'])}\ufd3e" if sc.get("ayah") else "")
            ev.append(f"Dialogue: 0,{_ts(t0)},{_ts(t0 + dur)},Head,,0,0,0,,{_plain_text(label)}")
    if opts.get("reciter"):
        ev.append(f"Dialogue: 0,{_ts(0.3)},{_ts(total)},Foot,,0,0,0,,{{\\fad(400,400)}}{_plain_text('بصوت القارئ ' + opts['reciter'])}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(ev) + "\n")
