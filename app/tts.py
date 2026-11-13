"""Free voice-over with Microsoft Edge TTS (no API key), plus word timings for subtitles."""
import asyncio

VOICES = {
    # Iraq
    "ar-IQ-BasselNeural": "عربي (العراق) - باسل - ذكر",
    "ar-IQ-RanaNeural": "عربي (العراق) - رنا - أنثى",
    # Gulf
    "ar-SA-HamedNeural": "عربي (السعودية) - حامد - ذكر",
    "ar-SA-ZariyahNeural": "عربي (السعودية) - زارية - أنثى",
    "ar-KW-FahedNeural": "عربي (الكويت) - فهد - ذكر",
    "ar-KW-NouraNeural": "عربي (الكويت) - نورة - أنثى",
    "ar-AE-HamdanNeural": "عربي (الإمارات) - حمدان - ذكر",
    "ar-AE-FatimaNeural": "عربي (الإمارات) - فاطمة - أنثى",
    "ar-QA-MoazNeural": "عربي (قطر) - معاذ - ذكر",
    "ar-QA-AmalNeural": "عربي (قطر) - أمل - أنثى",
    "ar-BH-AliNeural": "عربي (البحرين) - علي - ذكر",
    "ar-BH-LailaNeural": "عربي (البحرين) - ليلى - أنثى",
    "ar-OM-AbdullahNeural": "عربي (عُمان) - عبدالله - ذكر",
    "ar-OM-AyshaNeural": "عربي (عُمان) - عائشة - أنثى",
    "ar-YE-SalehNeural": "عربي (اليمن) - صالح - ذكر",
    "ar-YE-MaryamNeural": "عربي (اليمن) - مريم - أنثى",
    # Levant
    "ar-JO-TaimNeural": "عربي (الأردن) - تيم - ذكر",
    "ar-JO-SanaNeural": "عربي (الأردن) - سناء - أنثى",
    "ar-SY-LaithNeural": "عربي (سوريا) - ليث - ذكر",
    "ar-SY-AmanyNeural": "عربي (سوريا) - أماني - أنثى",
    "ar-LB-RamiNeural": "عربي (لبنان) - رامي - ذكر",
    "ar-LB-LaylaNeural": "عربي (لبنان) - ليلى - أنثى",
    # Egypt & North Africa
    "ar-EG-ShakirNeural": "عربي (مصر) - شاكر - ذكر",
    "ar-EG-SalmaNeural": "عربي (مصر) - سلمى - أنثى",
    "ar-LY-OmarNeural": "عربي (ليبيا) - عمر - ذكر",
    "ar-TN-HediNeural": "عربي (تونس) - الهادي - ذكر",
    "ar-DZ-IsmaelNeural": "عربي (الجزائر) - إسماعيل - ذكر",
    "ar-MA-JamalNeural": "عربي (المغرب) - جمال - ذكر",
    # multilingual voices (also read Arabic text)
    "en-US-BrianMultilingualNeural": "متعدد اللغات - Brian - ذكر",
    "en-US-AvaMultilingualNeural": "متعدد اللغات - Ava - أنثى",
    "en-US-EmmaMultilingualNeural": "متعدد اللغات - Emma - أنثى",
    # English & others
    "en-US-AvaNeural": "English (US) - Ava - female",
    "en-US-GuyNeural": "English (US) - Guy - male",
    "en-US-JennyNeural": "English (US) - Jenny - female",
    "en-GB-RyanNeural": "English (UK) - Ryan - male",
    "en-GB-SoniaNeural": "English (UK) - Sonia - female",
    "fr-FR-HenriNeural": "Français - Henri - male",
    "es-ES-AlvaroNeural": "Español - Álvaro - male",
    "tr-TR-AhmetNeural": "Türkçe - Ahmet - male",
}

SAMPLE_AR = "جامعة الموصل جميلة جداً، وجميع الجهود تُبذل لإنجاز المشاريع الجديدة."
SAMPLE_EN = "Hello! This is a short sample of how this voice sounds."


def sample_text(voice: str) -> str:
    return SAMPLE_AR if voice.startswith("ar-") or "Multilingual" in voice else SAMPLE_EN


async def _synthesize(text: str, voice: str, rate: int, out_path: str, pitch: int = 0, volume: int = 0) -> list[dict]:
    import edge_tts

    words = []
    comm = edge_tts.Communicate(text, voice, rate=f"{rate:+d}%", pitch=f"{pitch:+d}Hz", volume=f"{volume:+d}%",
                                boundary="WordBoundary")
    with open(out_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                start = chunk["offset"] / 1e7
                words.append({"text": chunk["text"], "start": start, "end": start + chunk["duration"] / 1e7})
    return words


def synthesize(text: str, voice: str, rate: int, out_path: str, pitch: int = 0, volume: int = 0) -> list[dict]:
    """Write an MP3 and return word timings [{text, start, end}] in seconds."""
    try:
        return asyncio.run(_synthesize(text, voice, rate, out_path, pitch, volume))
    except Exception as e:  # network problems, bad voice name, etc.
        raise RuntimeError(f"Edge TTS failed ({e}). Check your internet connection and the voice name.") from e
