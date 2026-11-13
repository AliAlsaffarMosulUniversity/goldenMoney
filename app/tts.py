"""Free voice-over with Microsoft Edge TTS (no API key), plus word timings for subtitles."""
import asyncio

VOICES = {
    "ar-SA-HamedNeural": "عربي (السعودية) - حامد - ذكر",
    "ar-SA-ZariyahNeural": "عربي (السعودية) - زارية - أنثى",
    "ar-IQ-BasselNeural": "عربي (العراق) - باسل - ذكر",
    "ar-IQ-RanaNeural": "عربي (العراق) - رنا - أنثى",
    "ar-EG-ShakirNeural": "عربي (مصر) - شاكر - ذكر",
    "ar-EG-SalmaNeural": "عربي (مصر) - سلمى - أنثى",
    "ar-AE-HamdanNeural": "عربي (الإمارات) - حمدان - ذكر",
    "ar-AE-FatimaNeural": "عربي (الإمارات) - فاطمة - أنثى",
    "ar-JO-TaimNeural": "عربي (الأردن) - تيم - ذكر",
    "ar-SY-LaithNeural": "عربي (سوريا) - ليث - ذكر",
    "en-US-AndrewNeural": "English (US) - Andrew - male",
    "en-US-AvaNeural": "English (US) - Ava - female",
    "en-US-GuyNeural": "English (US) - Guy - male",
    "en-US-JennyNeural": "English (US) - Jenny - female",
    "en-GB-RyanNeural": "English (UK) - Ryan - male",
    "en-GB-SoniaNeural": "English (UK) - Sonia - female",
    "fr-FR-HenriNeural": "Français - Henri - male",
    "es-ES-AlvaroNeural": "Español - Álvaro - male",
    "tr-TR-AhmetNeural": "Türkçe - Ahmet - male",
}


async def _synthesize(text: str, voice: str, rate: int, out_path: str) -> list[dict]:
    import edge_tts

    words = []
    comm = edge_tts.Communicate(text, voice, rate=f"{rate:+d}%", boundary="WordBoundary")
    with open(out_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                start = chunk["offset"] / 1e7
                words.append({"text": chunk["text"], "start": start, "end": start + chunk["duration"] / 1e7})
    return words


def synthesize(text: str, voice: str, rate: int, out_path: str) -> list[dict]:
    """Write an MP3 and return word timings [{text, start, end}] in seconds."""
    try:
        return asyncio.run(_synthesize(text, voice, rate, out_path))
    except Exception as e:  # network problems, bad voice name, etc.
        raise RuntimeError(f"Edge TTS failed ({e}). Check your internet connection and the voice name.") from e
