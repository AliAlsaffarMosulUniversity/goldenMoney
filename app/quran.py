"""Quran text, translations and recitations for the Ayah video mode.

The text is never written or changed by AI: it is downloaded from api.alquran.cloud (the Tanzil
Uthmani text), and each recitation file from everyayah.com. Both are cached in storage/quran so
an ayah is only downloaded once.
"""
import json
import re
import time
from pathlib import Path

import requests

from .config import STORAGE

CACHE = STORAGE / "quran"
TEXT_API = "https://api.alquran.cloud/v1/surah/{surah}/{edition}"
# tafsir books that api.alquran.cloud does not have: the quran.com data published by github.com/spa5k/tafsir_api
TAFSIR_API = "https://cdn.jsdelivr.net/gh/spa5k/tafsir_api@main/tafsir/{slug}/{surah}.json"
TAFSIR_SLUGS = {"ar.mukhtasar": "ar-tafsir-al-mukhtasar"}
AUDIO_URL = "https://everyayah.com/data/{reciter}/{surah:03d}{ayah:03d}.mp3"
TEXT_EDITION = "quran-uthmani"

# (name, number of ayahs) for the 114 surahs, from api.alquran.cloud (6236 ayahs in all)
SURAHS = [
    ("الفاتحة", 7), ("البقرة", 286), ("آل عمران", 200), ("النساء", 176), ("المائدة", 120), ("الأنعام", 165),
    ("الأعراف", 206), ("الأنفال", 75), ("التوبة", 129), ("يونس", 109), ("هود", 123), ("يوسف", 111),
    ("الرعد", 43), ("إبراهيم", 52), ("الحجر", 99), ("النحل", 128), ("الإسراء", 111), ("الكهف", 110),
    ("مريم", 98), ("طه", 135), ("الأنبياء", 112), ("الحج", 78), ("المؤمنون", 118), ("النور", 64),
    ("الفرقان", 77), ("الشعراء", 227), ("النمل", 93), ("القصص", 88), ("العنكبوت", 69), ("الروم", 60),
    ("لقمان", 34), ("السجدة", 30), ("الأحزاب", 73), ("سبأ", 54), ("فاطر", 45), ("يس", 83), ("الصافات", 182),
    ("ص", 88), ("الزمر", 75), ("غافر", 85), ("فصلت", 54), ("الشورى", 53), ("الزخرف", 89), ("الدخان", 59),
    ("الجاثية", 37), ("الأحقاف", 35), ("محمد", 38), ("الفتح", 29), ("الحجرات", 18), ("ق", 45),
    ("الذاريات", 60), ("الطور", 49), ("النجم", 62), ("القمر", 55), ("الرحمن", 78), ("الواقعة", 96),
    ("الحديد", 29), ("المجادلة", 22), ("الحشر", 24), ("الممتحنة", 13), ("الصف", 14), ("الجمعة", 11),
    ("المنافقون", 11), ("التغابن", 18), ("الطلاق", 12), ("التحريم", 12), ("الملك", 30), ("القلم", 52),
    ("الحاقة", 52), ("المعارج", 44), ("نوح", 28), ("الجن", 28), ("المزمل", 20), ("المدثر", 56),
    ("القيامة", 40), ("الإنسان", 31), ("المرسلات", 50), ("النبأ", 40), ("النازعات", 46), ("عبس", 42),
    ("التكوير", 29), ("الانفطار", 19), ("المطففين", 36), ("الانشقاق", 25), ("البروج", 22), ("الطارق", 17),
    ("الأعلى", 19), ("الغاشية", 26), ("الفجر", 30), ("البلد", 20), ("الشمس", 15), ("الليل", 21),
    ("الضحى", 11), ("الشرح", 8), ("التين", 8), ("العلق", 19), ("القدر", 5), ("البينة", 8), ("الزلزلة", 8),
    ("العاديات", 11), ("القارعة", 11), ("التكاثر", 8), ("العصر", 3), ("الهمزة", 9), ("الفيل", 5), ("قريش", 4),
    ("الماعون", 7), ("الكوثر", 3), ("الكافرون", 6), ("النصر", 3), ("المسد", 5), ("الإخلاص", 4), ("الفلق", 5),
    ("الناس", 6),
]

# everyayah.com folder -> reciter's name (each folder was checked to hold the whole Quran)
RECITERS = {
    "Alafasy_128kbps": "مشاري راشد العفاسي",
    "Abdul_Basit_Murattal_192kbps": "عبد الباسط عبد الصمد (مرتّل)",
    "Abdul_Basit_Mujawwad_128kbps": "عبد الباسط عبد الصمد (مجوّد)",
    "Husary_128kbps": "محمود خليل الحصري",
    "Husary_Muallim_128kbps": "محمود خليل الحصري (المصحف المعلّم)",
    "Minshawy_Murattal_128kbps": "محمد صديق المنشاوي",
    "MaherAlMuaiqly128kbps": "ماهر المعيقلي",
    "Abdurrahmaan_As-Sudais_192kbps": "عبد الرحمن السديس",
    "Saood_ash-Shuraym_128kbps": "سعود الشريم",
    "Ghamadi_40kbps": "سعد الغامدي",
    "Abu_Bakr_Ash-Shaatree_128kbps": "أبو بكر الشاطري",
    "Yasser_Ad-Dussary_128kbps": "ياسر الدوسري",
    "Nasser_Alqatami_128kbps": "ناصر القطامي",
    "Hudhaify_128kbps": "علي الحذيفي",
    "Muhammad_Ayyoub_128kbps": "محمد أيوب",
    "Muhammad_Jibreel_128kbps": "محمد جبريل",
    "Abdullah_Basfar_192kbps": "عبد الله بصفر",
    "Hani_Rifai_192kbps": "هاني الرفاعي",
    "Ahmed_ibn_Ali_al-Ajamy_128kbps_ketaballah.net": "أحمد بن علي العجمي",
}

# shown under the ayah (optional); the short name is written in the video as the source
TRANSLATIONS = {
    "none": "بدون",
    "ar.mukhtasar": "المختصر في التفسير (مركز تفسير)",
    "ar.muyassar": "التفسير الميسّر (مجمع الملك فهد)",
    "en.sahih": "English — Saheeh International",
}

# written small at the bottom of the video, so viewers know where the text under the ayah comes from
TRANSLATION_SOURCES = {
    "ar.mukhtasar": "التفسير: المختصر في التفسير",
    "ar.muyassar": "التفسير: التفسير الميسّر",
    "en.sahih": "Translation: Saheeh International",
}

# harakat, Quranic annotation marks and tatweel: ignored when comparing or measuring text
_MARKS = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_PAUSE = re.compile("[ۖ-ۜ]")
_BASMALA = "بسم الله الرحمن الرحيم"
_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def plain(text: str) -> str:
    return _MARKS.sub("", text).replace("ٱ", "ا")


def letters(text: str) -> int:
    """How long a text looks on screen: letters only, without marks or spaces."""
    return len(plain(text).replace(" ", ""))


def arabic_number(n: int) -> str:
    return str(n).translate(_DIGITS)


def surah_name(surah: int) -> str:
    return SURAHS[surah - 1][0]


def ayah_count(surah: int) -> int:
    return SURAHS[surah - 1][1]


def check_range(surah: int, start: int, end: int) -> None:
    if not 1 <= surah <= 114:
        raise ValueError("رقم السورة يجب أن يكون بين 1 و 114")
    n = ayah_count(surah)
    if not (1 <= start <= end <= n):
        raise ValueError(f"سورة {surah_name(surah)} فيها {n} آية: اختر آيات بين 1 و {n}، وآية البداية قبل آية النهاية")


def parse_ref(ref: str) -> tuple[int, int, int]:
    """'2:255' or '2:255-257' or '112' (whole surah) -> (surah, start, end)."""
    m = re.fullmatch(r"\s*(\d{1,3})\s*(?::\s*(\d{1,3})\s*(?:-\s*(\d{1,3}))?)?\s*", ref)
    if not m:
        raise ValueError("اكتب المرجع هكذا: 2:255 أو 2:255-257 أو 112")
    surah = int(m.group(1))
    if not 1 <= surah <= 114:
        raise ValueError("رقم السورة يجب أن يكون بين 1 و 114")
    start = int(m.group(2) or 1)
    end = int(m.group(3) or (m.group(2) or ayah_count(surah)))
    check_range(surah, start, end)
    return surah, start, end


def strip_basmala(text: str) -> str:
    """The Tanzil text puts the basmala in front of the first ayah of every surah except
    Al-Fatiha (where it is ayah 1) and At-Tawbah (which has none). The recitation of that ayah
    does not include it, so it is taken off here and shown as its own scene instead."""
    words = text.split()
    if len(words) > 4 and plain(" ".join(words[:4])) == _BASMALA:
        return " ".join(words[4:])
    return text


def _surah_edition(surah: int, edition: str) -> list[str]:
    """All the ayahs of one surah in one edition (Quran text or a translation), cached on disk."""
    path = CACHE / "text" / f"{edition}_{surah:03d}.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if len(data) == ayah_count(surah):
                return data
        except ValueError:
            pass
    err = None
    for _ in range(3):   # the CDN now and then answers with an error page: try again
        try:
            if edition in TAFSIR_SLUGS:
                r = requests.get(TAFSIR_API.format(slug=TAFSIR_SLUGS[edition], surah=surah), timeout=60)
                r.raise_for_status()
                rows = sorted(r.json(), key=lambda a: a["ayah"])
                if [a["ayah"] for a in rows] != list(range(1, ayah_count(surah) + 1)):
                    raise ValueError("ayah numbers do not match")
                ayahs = rows
            else:
                r = requests.get(TEXT_API.format(surah=surah, edition=edition), timeout=30)
                r.raise_for_status()
                ayahs = r.json()["data"]["ayahs"]
            break
        except (requests.RequestException, KeyError, TypeError, ValueError) as e:
            err = e
            time.sleep(1.5)
    else:
        raise RuntimeError(f"تعذّر تنزيل نص سورة {surah_name(surah)} ({edition}). تأكد من الاتصال بالإنترنت.\n{err}") from err
    data = [a["text"].replace("\ufeff", "").strip() for a in ayahs]
    if len(data) != ayah_count(surah):
        raise RuntimeError(f"النص الذي وصل لسورة {surah_name(surah)} ناقص ({len(data)} من {ayah_count(surah)} آية)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
    return data


def get_ayahs(surah: int, start: int, end: int, translation: str = "none") -> list[dict]:
    """[{"surah", "ayah", "text", "translation"}] for ayahs start..end of a surah."""
    check_range(surah, start, end)
    text = _surah_edition(surah, TEXT_EDITION)
    trans = _surah_edition(surah, translation) if translation and translation != "none" else None
    out = []
    for n in range(start, end + 1):
        t = text[n - 1]
        if n == 1 and surah != 1:
            t = strip_basmala(t)
        out.append({"surah": surah, "ayah": n, "text": t, "translation": trans[n - 1] if trans else ""})
    return out


def basmala() -> str:
    return _surah_edition(1, TEXT_EDITION)[0]


def wants_basmala(surah: int, start: int) -> bool:
    """A recitation from the start of a surah opens with the basmala (not for Al-Fatiha,
    where it is already ayah 1, nor for At-Tawbah)."""
    return start == 1 and surah not in (1, 9)


def recitation(reciter: str, surah: int, ayah: int) -> Path:
    """Download (once) one ayah recited by one reciter; returns the MP3 file."""
    dst = CACHE / "audio" / reciter / f"{surah:03d}{ayah:03d}.mp3"
    if dst.exists() and dst.stat().st_size > 1000:
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    url = AUDIO_URL.format(reciter=reciter, surah=surah, ayah=ayah)
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"تعذّر تنزيل تلاوة الآية {surah}:{ayah} للقارئ {RECITERS.get(reciter, reciter)}.\n{e}") from e
    data = r.content
    if len(data) < 1000 or not (data[:3] == b"ID3" or data[0] == 0xFF):
        raise RuntimeError(f"ملف التلاوة للآية {surah}:{ayah} غير صالح. جرّب قارئاً آخر.")
    tmp = dst.with_suffix(".part")
    tmp.write_bytes(data)
    tmp.replace(dst)
    return dst


def pages(text: str, max_letters: int) -> list[str]:
    """Split a long ayah into screens that fit, about the same size each, breaking after a
    pause mark (waqf sign) where one is near, otherwise between words. Words are never changed."""
    words = text.split()
    total = letters(text)
    if total <= max_letters or len(words) < 2:
        return [text]
    n = -(-total // max_letters)
    target = total / n
    out, cur, size = [], [], 0
    for i, w in enumerate(words):
        cur.append(w)
        size += letters(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if nxt is None or len(out) >= n - 1 or _PAUSE.fullmatch(nxt):   # never open a screen with a pause mark
            continue
        at_pause = bool(_PAUSE.search(w))
        if size >= target or (at_pause and size >= target * 0.7):
            out.append(" ".join(cur))
            cur, size = [], 0
    if cur:
        out.append(" ".join(cur))
    return out
