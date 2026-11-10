# Thumbnails and titles: de-slopping the look

YouTube's thumbnail is the uploader's ad for the video, and it's A/B-tested toward shock faces and red arrows. YouTube also generates three frames automatically from inside the video. Use those instead.

## Thumbnail URLs (no key, served by YouTube's image CDN)
| file | what it is |
|---|---|
| `https://i.ytimg.com/vi/<id>/hq1.jpg` | auto frame at ~25% of the video |
| `https://i.ytimg.com/vi/<id>/hq2.jpg` | auto frame at ~50%: **Karpathy's choice** ("a representative frame") |
| `https://i.ytimg.com/vi/<id>/hq3.jpg` | auto frame at ~75% |
| `https://i.ytimg.com/vi/<id>/mqdefault.jpg` | uploader thumbnail, 16:9 |
| `https://i.ytimg.com/vi/<id>/hqdefault.jpg` | uploader thumbnail, 4:3 letterboxed |

`hq1–3` are 480×360 with letterbox bars on 16:9 videos. The template uses `object-fit: cover` in a 16:9 box, which crops the bars off.

## Modes (`display.thumbnails`, also switchable in the site's Settings)
- `mid`: hq2. Honest and calm. Default.
- `frames`: hq1, then cycles hq1→hq2→hq3 on hover. A free "preview" of the whole video, and the most delightful option.
- `blur`: uploader thumbnail, blurred until hover. For people who want recognition without the shouting.
- `original`: uploader thumbnail.
- `none`: text cards (title on an accent gradient). Maximum calm.

Ideas to offer if they want more: grayscale until hover (`filter: grayscale(1)`), or AI-generated typographic covers. Keep it optional. Never generate fake frames that pretend to be from the video.

## Titles (`display.titles`)
The judge writes `plain_title`: ≤70 chars, factual, says what the video *is*. Example: "I Tried This For 30 Days And It CHANGED EVERYTHING 😱" → "30-day experiment with daily cold showers".
- `original`: Karpathy's choice. Filtering happens through what gets in, not by rewriting.
- `plain`: plain title on cards. The original shows on hover (card `title` attribute) and always on the watch page ("Original title: …").
- `both`: plain title, with the original underneath in smaller text.

Rules: never hide the original entirely, and never change meaning. If the original is already plain, `plain_title` must equal it.

## Other de-slop knobs
- `display.hide_counts`: no view counts (popularity ≠ quality).
- `rules.drop_clickbait` + `rules.clickbait_max`: remove videos scored above the threshold, even if recommended.
- `rules.hide_shorts`: drop anything ≤60s or linked as `/shorts/` (Shorts can run to 3 min; with the API key, ≤60s catches most).
- Watch page: plays on youtube-nocookie with `rel=0`, so end-screen suggestions stay limited to the same channel. Our own "why it's here" and the recommender quotes replace YouTube's comments section.
- `display.finite_feed: N`: N videos a day, then "That's the feed."
