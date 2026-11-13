"""Load/save user settings (config.json in the project root)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / "config.json"
STORAGE = ROOT / "storage"
MUSIC_DIR = ROOT / "resource" / "music"
FONTS_DIR = ROOT / "resource" / "fonts"

DEFAULTS = {
    "llm_provider": "gemini",
    "llm_api_key": "",
    "llm_model": "",
    "llm_base_url": "",
    "pexels_api_key": "",
    "pixabay_api_key": "",
    "language": "Arabic",
    "aspect": "9:16",
    "video_source": "pixabay",
    "local_clips_dir": "",
    "clip_duration": 3,
    "voice": "ar-IQ-BasselNeural",
    "voice_rate": 0,
    "voice_volume": 1.0,
    "subtitles": True,
    "font_name": "Arial",
    "font_size": 0,
    "font_color": "#FFFFFF",
    "outline_color": "#000000",
    "highlight_color": "#FFD400",
    "subtitle_position": "bottom",
    "bgm": "random",
    "bgm_volume": 0.15,
    "paragraphs": 2,
    "ui_mode": "night",
    "use_my_images": True,
    "image_captions": False,
    "use_logos": True,
    "logo_size": 0.14,
    "logo_corner": "right",
}


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_FILE.exists():
        try:
            cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
