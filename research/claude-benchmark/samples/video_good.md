```json
{"title": "Arc: carry less plastic", "shots": [
 {"id": 1, "duration_s": 6, "visual": "Plastic bottles pile up on a desk", "on_screen_text": "Still buying bottled water?", "narration": "Still buying bottled water every day?"},
 {"id": 2, "duration_s": 6, "visual": "Hand lifts a steel Arc bottle", "on_screen_text": "Meet Arc", "narration": "Meet Arc, the steel bottle built to last."},
 {"id": 3, "duration_s": 6, "visual": "Ice cubes clink inside the bottle", "on_screen_text": "Cold for 24 hours", "narration": "It keeps water cold for twenty-four hours."},
 {"id": 4, "duration_s": 6, "visual": "Bottle clips onto a backpack", "on_screen_text": "Goes where you go", "narration": "It clips on and goes wherever you go."},
 {"id": 5, "duration_s": 6, "visual": "Logo on a teal background", "on_screen_text": "Arc. Refill the planet.", "narration": "Arc. Refill, not landfill."}]}
```

```srt
1
00:00:00,000 --> 00:00:05,500
Still buying bottled water every day?

2
00:00:06,000 --> 00:00:11,500
Meet Arc, the steel bottle built to last.

3
00:00:12,000 --> 00:00:17,500
It keeps water cold for twenty-four hours.

4
00:00:18,000 --> 00:00:23,500
It clips on and goes wherever you go.

5
00:00:24,000 --> 00:00:29,500
Arc. Refill, not landfill.
```

```bash
ffmpeg -f lavfi -i color=c=teal:s=1080x1920:d=30 -vf "drawtext=text='Still buying bottled water?':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,0,6)',drawtext=text='Meet Arc':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,6,12)',drawtext=text='Cold for 24 hours':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,12,18)',drawtext=text='Goes where you go':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,18,24)',drawtext=text='Arc. Refill the planet.':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,24,30)'" -c:v libx264 -pix_fmt yuv420p out.mp4
```
