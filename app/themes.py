"""Night and day palettes for the web UI: graphite grey, black and gold.
Each palette sets Streamlit's own theme and the CSS variables used by ui.css."""

_GOLD = "linear-gradient(135deg, #FBE7A1 0%, #E9C46A 28%, #D4A72C 62%, #B8860B 100%)"

NIGHT = {
    "streamlit": {"base": "dark", "primaryColor": "#D4A72C", "backgroundColor": "#0C0C0E",
                  "secondaryBackgroundColor": "#1B1C20", "textColor": "#EDEDEF"},
    "css": {
        "--bg-a": "#141518", "--bg-b": "#08080A",
        "--glow-1": "rgba(212,167,44,.10)", "--glow-2": "rgba(160,165,175,.07)",
        "--surface": "linear-gradient(180deg, #1E1F24, #18191D)", "--line": "rgba(255,255,255,.07)",
        "--text": "#EDEDEF", "--muted": "#9A9DA6",
        "--accent": "#D4A72C", "--accent-text": "#E9C46A", "--accent-grad": _GOLD, "--accent-edge": "#7A5A0C",
        "--accent-glow": "rgba(212,167,44,.30)", "--accent-ring": "rgba(212,167,44,.22)",
        "--accent-soft": "rgba(212,167,44,.05)", "--accent-line": "rgba(212,167,44,.40)", "--on-accent": "#1A1405",
        "--hero-bg": "radial-gradient(700px 260px at 85% 0%, rgba(212,167,44,.16), transparent 70%), linear-gradient(135deg, #202126, #141518)",
        "--hero-border": "rgba(212,167,44,.35)", "--hero-sub": "#C4C6CC",
        "--title-grad": "linear-gradient(90deg, #FFF4D0, #E9C46A 45%, #C9971F)",
        "--badge-text": "#D9DBE0", "--badge-bg": "rgba(255,255,255,.05)", "--badge-border": "rgba(255,255,255,.14)",
        "--btn-top": "#34363D", "--btn-bot": "#24252A", "--btn-line": "rgba(255,255,255,.10)", "--btn-edge": "#0E0E10",
        "--btn-text": "#EDEDEF",
        "--btn-shadow": "0 8px 16px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.10)",
        "--field": "#121316", "--field-line": "rgba(255,255,255,.10)", "--field-inset": "inset 0 2px 6px rgba(0,0,0,.45)",
        "--sidebar-bg": "linear-gradient(180deg, #1A1B1F, #0E0E10)",
        "--shadow-md": "0 14px 34px rgba(0,0,0,.50), inset 0 1px 0 rgba(255,255,255,.04)",
        "--shadow-lg": "0 20px 50px rgba(0,0,0,.60), inset 0 1px 0 rgba(255,255,255,.06)",
    },
}

DAY = {
    "streamlit": {"base": "light", "primaryColor": "#B8860B", "backgroundColor": "#ECEDEF",
                  "secondaryBackgroundColor": "#FFFFFF", "textColor": "#1C1C1F"},
    "css": {
        "--bg-a": "#F1F2F4", "--bg-b": "#E2E4E8",
        "--glow-1": "rgba(212,167,44,.12)", "--glow-2": "rgba(120,125,135,.10)",
        "--surface": "linear-gradient(180deg, #FFFFFF, #F8F8F9)", "--line": "rgba(20,20,25,.08)",
        "--text": "#1C1C1F", "--muted": "#5F636B",
        "--accent": "#B8860B", "--accent-text": "#8A6508", "--accent-grad": _GOLD, "--accent-edge": "#8A6508",
        "--accent-glow": "rgba(184,134,11,.28)", "--accent-ring": "rgba(184,134,11,.20)",
        "--accent-soft": "rgba(184,134,11,.05)", "--accent-line": "rgba(184,134,11,.45)", "--on-accent": "#1A1405",
        "--hero-bg": "radial-gradient(700px 260px at 85% 0%, rgba(212,167,44,.18), transparent 70%), linear-gradient(135deg, #2A2B30, #17181B)",
        "--hero-border": "rgba(184,134,11,.45)", "--hero-sub": "#D4D6DB",
        "--title-grad": "linear-gradient(90deg, #FFF4D0, #E9C46A 45%, #C9971F)",
        "--badge-text": "#E5E7EB", "--badge-bg": "rgba(255,255,255,.08)", "--badge-border": "rgba(255,255,255,.18)",
        "--btn-top": "#FFFFFF", "--btn-bot": "#E3E5E9", "--btn-line": "rgba(20,20,25,.14)", "--btn-edge": "#AEB3BC",
        "--btn-text": "#1C1C1F",
        "--btn-shadow": "0 6px 14px rgba(20,20,25,.12), inset 0 1px 0 #FFFFFF",
        "--field": "#F7F7F8", "--field-line": "rgba(20,20,25,.16)", "--field-inset": "inset 0 1px 3px rgba(20,20,25,.08)",
        "--sidebar-bg": "linear-gradient(180deg, #F7F7F8, #E9EAED)",
        "--shadow-md": "0 10px 26px rgba(20,20,25,.10)",
        "--shadow-lg": "0 16px 40px rgba(20,20,25,.22)",
    },
}

THEMES = {"night": NIGHT, "day": DAY}


def css_vars(mode: str) -> str:
    t = THEMES.get(mode, NIGHT)["css"]
    return ":root{" + ";".join(f"{k}:{v}" for k, v in t.items()) + "}"
