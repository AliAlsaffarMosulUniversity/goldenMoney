"""AutoShorts web UI — run with: streamlit run webui.py"""
import streamlit as st

from app import llm, pipeline, tts
from app.config import MUSIC_DIR, load_config, save_config

st.set_page_config(page_title="AutoShorts", page_icon="🎬", layout="wide")
st.markdown("""<style>
[data-testid="stAppViewContainer"], [data-testid="stSidebar"], [data-testid="stMain"] {direction: rtl;}
[data-testid="stMarkdownContainer"], label, p, h1, h2, h3 {text-align: right;}
[data-testid="stSlider"], [data-testid="stFileUploader"], code, pre {direction: ltr;}
textarea, input {direction: auto; text-align: right;}
</style>""", unsafe_allow_html=True)

cfg = load_config()

# ---------------- Settings (sidebar) ----------------
with st.sidebar:
    st.header("⚙️ الإعدادات")
    st.subheader("نموذج الذكاء الاصطناعي")
    keys = list(llm.PROVIDERS)
    cfg["llm_provider"] = st.selectbox("المزوّد", keys, index=keys.index(cfg["llm_provider"]) if cfg["llm_provider"] in keys else 0,
                                       format_func=lambda k: llm.PROVIDERS[k]["label"])
    preset = llm.PROVIDERS[cfg["llm_provider"]]
    cfg["llm_api_key"] = st.text_input("API Key", cfg["llm_api_key"], type="password",
                                       help="Ollama لا يحتاج مفتاح")
    cfg["llm_model"] = st.text_input("اسم النموذج", cfg["llm_model"], placeholder=preset["model"] or "model-name")
    if cfg["llm_provider"] in ("custom", "ollama"):
        cfg["llm_base_url"] = st.text_input("Base URL", cfg["llm_base_url"], placeholder=preset["base_url"])

    st.subheader("مصدر المقاطع")
    sources = {"pixabay": "Pixabay (مجاني)", "pexels": "Pexels (مجاني)", "local": "مجلد على جهازي"}
    cfg["video_source"] = st.selectbox("المصدر", list(sources), index=list(sources).index(cfg["video_source"]) if cfg["video_source"] in sources else 0,
                                       format_func=sources.get)
    if cfg["video_source"] == "pexels":
        cfg["pexels_api_key"] = st.text_input("Pexels API Key", cfg["pexels_api_key"], type="password",
                                              help="pexels.com/api")
    elif cfg["video_source"] == "pixabay":
        cfg["pixabay_api_key"] = st.text_input("Pixabay API Key", cfg["pixabay_api_key"], type="password",
                                               help="مجاني من pixabay.com/api/docs")
    else:
        cfg["local_clips_dir"] = st.text_input("مسار مجلد المقاطع", cfg["local_clips_dir"],
                                               placeholder=r"D:\Videos\clips")

    st.subheader("الترجمة (Subtitles)")
    cfg["font_name"] = st.text_input("الخط", cfg["font_name"],
                                     help="ضع ملفات خطوط ‎.ttf‎ في resource/fonts لاستخدامها")
    c1, c2 = st.columns(2)
    cfg["font_color"] = c1.color_picker("لون النص", cfg["font_color"])
    cfg["outline_color"] = c2.color_picker("لون الحدود", cfg["outline_color"])
    cfg["font_size"] = st.number_input("حجم الخط (0 = تلقائي)", 0, 200, int(cfg["font_size"]))

    if st.button("💾 حفظ الإعدادات", use_container_width=True):
        save_config(cfg)
        st.success("تم الحفظ")

# ---------------- Main ----------------
st.title("🎬 AutoShorts — صانع الفيديوهات القصيرة")
st.caption("اكتب موضوع الفيديو، وستتولى الأداة كتابة السكربت واختيار المقاطع والتعليق الصوتي والترجمة والموسيقى.")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📝 المحتوى")
    subject = st.text_input("موضوع الفيديو", placeholder="مثال: فوائد شرب الماء صباحاً")
    langs = ["Arabic", "English", "French", "Spanish", "Turkish", "German"]
    cfg["language"] = st.selectbox("لغة السكربت", langs, index=langs.index(cfg["language"]) if cfg["language"] in langs else 0)
    cfg["paragraphs"] = st.slider("عدد الفقرات", 1, 5, int(cfg["paragraphs"]))
    if st.button("✍️ اكتب السكربت بالذكاء الاصطناعي"):
        if not subject:
            st.warning("اكتب الموضوع أولاً")
        else:
            with st.spinner("جاري الكتابة…"):
                try:
                    res = llm.generate_script(cfg, subject)
                    st.session_state["script"] = res["script"]
                    st.session_state["terms"] = ", ".join(res["search_terms"])
                except Exception as e:
                    st.error(str(e))
    script = st.text_area("السكربت (اتركه فارغاً ليُكتب تلقائياً)", key="script", height=220)
    terms_txt = st.text_input("كلمات البحث عن المقاطع (بالإنجليزية، مفصولة بفواصل، وبنفس ترتيب جمل السكربت)", key="terms")

with col2:
    st.subheader("🎞️ الفيديو")
    aspects = {"9:16": "عمودي 9:16 (Reels / Shorts / TikTok)", "16:9": "أفقي 16:9 (YouTube)", "1:1": "مربع 1:1"}
    cfg["aspect"] = st.selectbox("المقاس", list(aspects), index=list(aspects).index(cfg["aspect"]), format_func=aspects.get)
    cfg["clip_duration"] = st.slider("مدة كل مقطع (ثانية)", 2, 10, int(cfg["clip_duration"]))
    cfg["highlight_color"] = st.color_picker("لون الكلمة المنطوقة", cfg.get("highlight_color", "#FFD400"))
    cfg["subtitles"] = st.toggle("إضافة الترجمة", cfg["subtitles"])
    pos = {"bottom": "أسفل", "center": "وسط", "top": "أعلى"}
    cfg["subtitle_position"] = st.radio("موضع الترجمة", list(pos), index=list(pos).index(cfg["subtitle_position"]),
                                        format_func=pos.get, horizontal=True)

with col3:
    st.subheader("🎙️ الصوت")
    voices = list(tts.VOICES)
    if cfg["voice"] not in voices:
        voices.insert(0, cfg["voice"])
    cfg["voice"] = st.selectbox("صوت التعليق (Edge TTS مجاني)", voices, index=voices.index(cfg["voice"]),
                                format_func=lambda v: tts.VOICES.get(v, v))
    cfg["voice_rate"] = st.slider("سرعة الكلام %", -50, 50, int(cfg["voice_rate"]))
    cfg["voice_volume"] = st.slider("مستوى صوت التعليق", 0.0, 2.0, float(cfg["voice_volume"]), 0.1)

    music = [p.name for p in pipeline.list_music()]
    opts = ["random", "none", *music]
    labels = {"random": "عشوائي من مجلد الموسيقى", "none": "بدون موسيقى"}
    cfg["bgm"] = st.selectbox("الموسيقى الخلفية", opts, index=opts.index(cfg["bgm"]) if cfg["bgm"] in opts else 0,
                              format_func=lambda o: labels.get(o, o))
    up = st.file_uploader("أو ارفع ملف موسيقى", type=["mp3", "wav", "m4a", "ogg"])
    if up is not None:
        (MUSIC_DIR / up.name).write_bytes(up.getbuffer())
        cfg["bgm"] = up.name
        st.caption(f"تمت إضافة: {up.name}")
    cfg["bgm_volume"] = st.slider("مستوى صوت الموسيقى", 0.0, 1.0, float(cfg["bgm_volume"]), 0.05)
    if not music:
        st.caption(f"لا توجد موسيقى بعد — ضع ملفات MP3 في:\n`{MUSIC_DIR}`")

st.divider()
if st.button("🚀 إنشاء الفيديو", type="primary", use_container_width=True):
    if not subject and not script.strip():
        st.warning("اكتب موضوع الفيديو أو السكربت")
    else:
        save_config(cfg)
        terms = [t.strip() for t in terms_txt.split(",") if t.strip()]
        log_box = st.status("جاري إنشاء الفيديو…", expanded=True)
        try:
            res = pipeline.run(cfg, subject or script[:60], script, terms, log=log_box.write)
            log_box.update(label="✅ اكتمل الفيديو", state="complete", expanded=False)
            v1, v2 = st.columns([1, 2])
            v1.video(str(res["video"]))
            with open(res["video"], "rb") as f:
                v2.download_button("⬇️ تحميل الفيديو", f, file_name="video.mp4", mime="video/mp4")
            v2.write(f"📁 `{res['video']}`")
            if res["title"]:
                v2.write(f"**العنوان المقترح:** {res['title']}")
        except Exception as e:
            log_box.update(label="❌ حدث خطأ", state="error")
            st.error(str(e))
