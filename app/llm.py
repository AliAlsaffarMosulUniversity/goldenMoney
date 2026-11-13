"""Script generation with a choice of AI providers."""
import json
import re

# OpenAI-compatible providers share one client; Claude uses the Anthropic SDK.
PROVIDERS = {
    "gemini": {"label": "Google Gemini", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "model": "gemini-2.5-flash"},
    "openai": {"label": "OpenAI", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    "claude": {"label": "Anthropic Claude", "base_url": "", "model": "claude-opus-5-5"},
    "deepseek": {"label": "DeepSeek", "base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    "openrouter": {"label": "OpenRouter", "base_url": "https://openrouter.ai/api/v1", "model": "openai/gpt-4o-mini"},
    "groq": {"label": "Groq", "base_url": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile"},
    "ollama": {"label": "Ollama (local, free)", "base_url": "http://localhost:11434/v1", "model": "llama3.1"},
    "custom": {"label": "Custom OpenAI-compatible", "base_url": "", "model": ""},
}

# Claude models that accept server-side refusal fallbacks and the effort setting.
_CLAUDE_FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-1", "claude-fable-5-2"}

SYSTEM_PROMPT = (
    "You write voice-over scripts for short social-media videos (Reels, Shorts, TikTok). "
    "Reply with a single JSON object and nothing else."
)


def _build_prompt(subject: str, language: str, paragraphs: int) -> str:
    return f"""Write a voice-over script about: "{subject}"

Rules:
- Language of the script: {language}.
- {paragraphs} short paragraph(s), engaging hook in the first sentence, no greetings, no hashtags, no emojis.
- Plain spoken text only: no headings, no markdown, no stage directions, no "narrator:" labels.
- Split the script into scenes of ONE sentence each (5 to 10 scenes in total).
- For every scene give 2 or 3 short ENGLISH search terms (1-3 words) describing concrete,
  filmable visuals for THAT sentence, for searching stock-footage sites (no abstract words).

Return JSON exactly in this shape:
{{"title": "...", "scenes": [{{"text": "sentence", "terms": ["...", "..."]}}]}}"""


_HINTS = {
    400: "الطلب مرفوض. غالباً اسم النموذج غير مناسب، أو الخدمة غير متاحة في بلدك.",
    401: "المفتاح (API Key) غير صحيح. انسخه من جديد والصقه في الإعدادات ثم احفظ.",
    402: "رصيد حسابك في الخدمة انتهى.",
    403: "الخدمة رفضت الاتصال من جهازك. غالباً هي محجوبة في بلدك. جرّب مزوّد OpenRouter.",
    404: "اسم النموذج غير موجود. اكتب اسم نموذج صحيحاً في خانة «اسم النموذج»، أو اتركها فارغة.",
    429: "تجاوزت الحد المجاني المسموح. انتظر دقيقة ثم أعد المحاولة.",
}


def _call(cfg: dict, prompt: str) -> str:
    """Call the provider and turn API errors into a clear Arabic message."""
    if not cfg.get("llm_api_key") and cfg.get("llm_provider") != "ollama":
        raise RuntimeError("أدخل مفتاح الذكاء الاصطناعي (API Key) في الإعدادات ثم اضغط حفظ.")
    try:
        return _call_raw(cfg, prompt)
    except RuntimeError:
        raise
    except Exception as e:
        label = PROVIDERS.get(cfg.get("llm_provider"), PROVIDERS["custom"])["label"]
        status = getattr(e, "status_code", None)
        hint = _HINTS.get(status) or ("تعذّر الاتصال بالخدمة. تأكد من الإنترنت." if status is None else "خطأ من الخدمة.")
        raise RuntimeError(f"{label}: {hint}\n\n({type(e).__name__}: {str(e)[:300]})") from e


def _call_raw(cfg: dict, prompt: str) -> str:
    provider = cfg.get("llm_provider", "gemini")
    preset = PROVIDERS.get(provider, PROVIDERS["custom"])
    model = cfg.get("llm_model") or preset["model"]
    key = cfg.get("llm_api_key", "")

    if provider == "claude":
        import anthropic

        client = anthropic.Anthropic(api_key=key or None)
        kwargs = {}
        if model in _CLAUDE_FALLBACK_MODELS:
            kwargs = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default",
                      "output_config": {"effort": "low"}}
        resp = client.beta.messages.create(
            model=model, max_tokens=16000, system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}], **kwargs,
        )
        if resp.stop_reason == "refusal":
            raise RuntimeError("Claude declined this topic. Try a different subject.")
        return "".join(b.text for b in resp.content if b.type == "text")

    from openai import OpenAI

    base_url = cfg.get("llm_base_url") or preset["base_url"]
    if not base_url:
        raise RuntimeError("Set a Base URL for the custom provider in Settings.")
    client = OpenAI(api_key=key or "ollama", base_url=base_url)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


def _json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise RuntimeError(f"The AI reply was not JSON:\n{text[:500]}")
    return json.loads(match.group(0))


def _parse(text: str) -> dict:
    data = _json(text)
    scenes = []
    for sc in data.get("scenes", []):
        t = str(sc.get("text", "")).strip()
        terms = [str(x).strip() for x in sc.get("terms", []) if str(x).strip()]
        if t:
            scenes.append({"text": t, "terms": terms or ["abstract background"]})
    if not scenes:
        raise RuntimeError("The AI returned an empty script.")
    return {"title": str(data.get("title", "")).strip(), "scenes": scenes,
            "script": " ".join(s["text"] for s in scenes),
            "search_terms": [t for s in scenes for t in s["terms"][:1]]}


def generate_script(cfg: dict, subject: str) -> dict:
    prompt = _build_prompt(subject, cfg.get("language", "Arabic"), int(cfg.get("paragraphs", 2)))
    return _parse(_call(cfg, prompt))


def generate_terms(cfg: dict, subject: str, script: str) -> list[str]:
    """Search terms, in script order, for a script the user wrote themselves."""
    prompt = (f'Video subject: "{subject}"\nScript:\n{script}\n\n'
              'For each sentence of this script, in order, give one short ENGLISH stock-footage search term '
              '(1-3 words, concrete and filmable). Return JSON: {"terms": ["...", "..."]}')
    data = _json(_call(cfg, prompt))
    return [str(t).strip() for t in data.get("terms", []) if str(t).strip()]
