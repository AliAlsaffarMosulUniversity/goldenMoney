"""AutoShorts web UI — run with: streamlit run webui.py"""
import streamlit as st

from app import assets, llm, pipeline, tts
from app.config import MUSIC_DIR, load_config, save_config

st.set_page_config(page_title="AutoShorts", page_icon="🎬", layout="wide")
from pathlib import Path

st.markdown(f"<style>{(Path(__file__).parent / 'app' / 'ui.css').read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True)

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


def text_to_speech_tool() -> None:
    """Stand-alone tool: text in, voice-over (MP3) out, optionally with SRT subtitles."""
    import time
    from app import subtitles
    from app.config import STORAGE

    st.caption("أداة مستقلة: اكتب أو الصق أي نص، واحصل على ملف صوتي بصوت طبيعي. مجانية ولا تحتاج مفاتيح.")
    t1, t2 = st.columns([2, 1])
    with t2:
        voices = list(tts.VOICES)
        voice = st.selectbox("الصوت", voices, index=voices.index(cfg["voice"]) if cfg["voice"] in voices else 0,
                             format_func=lambda v: tts.VOICES.get(v, v), key="tts_voice")
        rate = st.slider("السرعة %", -50, 50, 0, key="tts_rate")
        pitch = st.slider("طبقة الصوت (أحدّ / أغلظ)", -30, 30, 0, key="tts_pitch")
        volume = st.slider("ارتفاع الصوت %", -50, 50, 0, key="tts_volume")
        want_srt = st.checkbox("ملف ترجمة SRT أيضاً (لبرامج المونتاج)", key="tts_srt")
    with t1:
        up = st.file_uploader("أو ارفع ملفاً نصياً (txt)", type=["txt"], key="tts_file")
        if up is not None:
            st.session_state["tts_text"] = up.getvalue().decode("utf-8", errors="replace")
        text = st.text_area("النص", key="tts_text", height=300, placeholder="اكتب أو الصق النص هنا…")
        st.caption(f"{len(text.split())} كلمة — حوالي {max(1, round(len(text.split()) / 2.3))} ثانية")
        if st.button("🔊 تحويل إلى صوت", type="primary", use_container_width=True, key="tts_go"):
            if not text.strip():
                st.warning("اكتب النص أولاً")
            else:
                out_dir = STORAGE / "audio"
                out_dir.mkdir(parents=True, exist_ok=True)
                stamp = time.strftime("%Y%m%d-%H%M%S")
                mp3 = out_dir / f"voice-{stamp}.mp3"
                with st.spinner("جاري إنشاء الصوت…"):
                    try:
                        words = tts.synthesize(text, voice, rate, str(mp3), pitch, volume)
                        st.session_state["tts_result"] = {"mp3": str(mp3), "words": words, "srt": None}
                        if want_srt and words:
                            srt = out_dir / f"voice-{stamp}.srt"
                            subtitles.write_srt(words, str(srt))
                            st.session_state["tts_result"]["srt"] = str(srt)
                    except Exception as e:
                        st.error(str(e))
        res = st.session_state.get("tts_result")
        if res:
            st.success("✅ الصوت جاهز")
            st.audio(res["mp3"])
            d1, d2 = st.columns(2)
            with open(res["mp3"], "rb") as f:
                d1.download_button("⬇️ تحميل MP3", f, file_name="voice.mp3", mime="audio/mpeg", use_container_width=True)
            if res.get("srt"):
                with open(res["srt"], "rb") as f:
                    d2.download_button("⬇️ تحميل الترجمة SRT", f, file_name="voice.srt", use_container_width=True)
            st.caption(f"📁 {res['mp3']}")


st.markdown("""
<div class="as-hero">
  <h1><span class="as-ico">🎬</span>AutoShorts</h1>
  <div class="as-sub">صانع الفيديوهات القصيرة بالذكاء الاصطناعي — اكتب الفكرة، والأداة تكتب السكربت وتختار المشاهد وتضيف الصوت والترجمة والموسيقى.</div>
  <span class="as-badge">🎬 Reels · Shorts · TikTok</span>
  <span class="as-badge">🎙️ أصوات عربية طبيعية</span>
  <span class="as-badge amber">✨ مجاني</span>
</div>
""", unsafe_allow_html=True)
tab_video, tab_tts = st.tabs(["🎬 صانع الفيديو", "🔊 تحويل النص إلى صوت"])

with tab_tts:
    text_to_speech_tool()

with tab_video:

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
                        st.session_state["script"] = "\n".join(sc["text"] for sc in res["scenes"])
                    except Exception as e:
                        st.error(str(e))
        script = st.text_area("السكربت (اتركه فارغاً ليُكتب تلقائياً)", key="script", height=220)
        st.caption("🧠 المقاطع تُختار تلقائياً: الأداة تفهم كل جملة من السكربت وتبحث عن مشاهد تناسبها.")
        with st.expander("خيارات متقدمة: كلمات بحث يدوية (اختياري)"):
            terms_txt = st.text_input("كلمات بحث بالإنجليزية بنفس ترتيب الجمل، مفصولة بفواصل. اتركها فارغة للاختيار التلقائي",
                                      key="terms")

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
        if st.button("▶️ استمع للصوت", key="preview_voice"):
            from app.config import STORAGE
            prev = STORAGE / "audio" / "preview.mp3"
            prev.parent.mkdir(parents=True, exist_ok=True)
            with st.spinner("…"):
                try:
                    tts.synthesize(tts.sample_text(cfg["voice"]), cfg["voice"], int(cfg["voice_rate"]), str(prev))
                    st.audio(prev.read_bytes(), format="audio/mp3", autoplay=True)
                except Exception as e:
                    st.error(str(e))
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

    # ---------------- Optional: the user's own pictures and logos ----------------
    st.session_state.setdefault("up_n", 0)
    n_imgs, n_logos = len(assets.list_images()), len(assets.list_logos())
    with st.expander(f"🖼️ صوري وشعاراتي (اختياري) — {n_imgs} صورة، {n_logos} شعار"):
        c_img, c_logo = st.columns([3, 2])

        with c_logo:
            st.markdown("**🏷️ الشعارات** (مثلاً شعار الكلية والجامعة)")
            st.caption("تظهر طوال الفيديو في الزاويتين العلويتين. الأفضل صورة PNG بخلفية شفافة.")
            cfg["use_logos"] = st.toggle("إضافة الشعارات للفيديو", cfg.get("use_logos", True))
            new_logos = st.file_uploader("رفع شعار (حتى شعارين)", type=["png", "jpg", "jpeg", "webp"],
                                         accept_multiple_files=True, key=f"logos_{st.session_state.up_n}")
            if new_logos:
                for f in new_logos:
                    assets.add_logo(f.name, f.getvalue())
                st.session_state.up_n += 1
                st.rerun()
            logos = assets.list_logos()
            for i, lp in enumerate(logos):
                l1, l2 = st.columns([3, 1])
                l1.image(str(lp), width=110, caption=("يمين" if i == 0 else "يسار") if len(logos) >= 2 else None)
                if l2.button("🗑️", key=f"dl_{lp.name}", help="حذف الشعار"):
                    assets.delete_logo(lp.name)
                    st.rerun()
            if len(logos) > 2:
                st.warning("يُستخدم أول شعارين فقط.")
            if len(logos) == 1:
                corners = {"right": "يمين", "left": "يسار"}
                cfg["logo_corner"] = st.radio("مكان الشعار", list(corners), format_func=corners.get, horizontal=True,
                                              index=list(corners).index(cfg.get("logo_corner", "right")))
            cfg["logo_size"] = st.slider("حجم الشعار", 0.08, 0.25, float(cfg.get("logo_size", 0.14)), 0.01)

        with c_img:
            st.markdown("**📷 صوري الخاصة**")
            st.caption("ارفع صورك واكتب وصفاً لكل صورة. الأداة تفهم الوصف وتضع كل صورة في الجملة التي تتكلم عنها.")
            cfg["use_my_images"] = st.toggle("استخدام صوري في الفيديو", cfg.get("use_my_images", True))
            cfg["image_captions"] = st.toggle("كتابة وصف الصورة عليها كعنوان", cfg.get("image_captions", False))
            new_imgs = st.file_uploader("رفع صور", type=["png", "jpg", "jpeg", "webp"],
                                        accept_multiple_files=True, key=f"imgs_{st.session_state.up_n}")
            if new_imgs:
                for f in new_imgs:
                    assets.add_image(f.name, f.getvalue())
                st.session_state.up_n += 1
                st.rerun()
            for img in assets.list_images():
                i1, i2 = st.columns([1, 3])
                i1.image(str(img["path"]), width=120)
                desc = i2.text_input("وصف الصورة", img["desc"], key=f"desc_{img['name']}",
                                     placeholder="مثال: مبنى كلية الإدارة والاقتصاد من الخارج")
                if desc != img["desc"]:
                    assets.update_image(img["name"], desc=desc)
                b1, b2 = i2.columns(2)
                on = b1.checkbox("استخدامها", img["enabled"], key=f"en_{img['name']}")
                if on != img["enabled"]:
                    assets.update_image(img["name"], enabled=on)
                if b2.button("🗑️ حذف", key=f"di_{img['name']}"):
                    assets.delete_image(img["name"])
                    st.rerun()
                if not desc:
                    i2.caption("⚠️ اكتب وصفاً حتى توضع الصورة في المكان المناسب.")

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
