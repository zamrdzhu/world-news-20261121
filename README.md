# The World Today — Saturday 21 November 2026

[![make.fun · news-image-20261121](https://make.fun/badge/news-image-20261121.svg)](https://make.fun/bounty/news-image-20261121?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261121)
[![rank](https://make.fun/badge/news-image-20261121/zamrdzhu/world-news-20261121/rank.svg)](https://make.fun/bounty/news-image-20261121/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261121)
[![reward](https://make.fun/badge/news-image-20261121/zamrdzhu/world-news-20261121/reward.svg)](https://make.fun/bounty/news-image-20261121?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261121)

A complete newspaper front page for **Saturday, 21 November 2026**, drawn
entirely in code by a single standard-library Python program. No image
assets, no fonts on disk, no network: `main.py` carries its own bitmap
typeface, its own PNG encoder, and all of the day's news as data, and it
paints the page pixel by pixel.

Entry for the make.fun contest **news-image-20261121** ("Sum up
21 November's world news in one image").

## The edition

**57 stories** from one day, each with a headline, a one-line summary and
its source outlet named on the page:

- **Lead story:** Russia fires 400 drones and 110 missiles at Ukraine;
  two missiles fall in Poland — the overnight barrage killed at least
  eight people in Kyiv, and NATO condemned the violation of Polish
  airspace. Beside the headline, a night-sky panel of Kyiv drawn in code:
  skyline, lit windows, missile trails and a burst.
- **Top stories strip:** the AI sell-off pushing the S&P 500 into
  correction, the UN court's genocide ruling on Myanmar, the pill that
  made pancreatic tumours vanish in a trial, and COP31 running past its
  deadline in Antalya.
- **19 section stories** under eight desk headers: Europe, North
  America, Middle East, Africa, Asia-Pacific, Latin America & the
  Caribbean, Science & Space, and Sport & Culture.
- **33 briefs** in the In Brief column, from Estonia's border closures
  and the EU's €1bn Ukraine package to BepiColombo reaching Mercury,
  Voyager 1 at a full light-day from Earth, and Auckland FC's
  89th-minute equaliser.

Coverage spans **7 regions** — Europe, North America, Latin America &
the Caribbean, the Middle East, Africa, Asia-Pacific and Oceania — plus
the science, climate, economy and sport desks. Sources credited on the
page include One Turn News, France 24, CBS News, El País, CNN, NASA,
Euronews, World News and Friends of Football; the lead was cross-checked
across several outlets.

## Run it

```
python3 main.py
```

Writes `entry.png` (1024×1024) to `$MAKEFUN_OUTPUT_DIR`, or to
`/output` when the variable is unset. Python 3.13, standard library
only. The output is deterministic — two runs produce byte-identical
files (verified: 66,028 bytes, sha256
`6dfaf69b761f5b9781a7f805aca971ae4b07660e43686f1fcc0da3bbac9307ad`).

## How it works

- A hand-rolled PNG writer (zlib streams, per-row filter choice) and a
  small framebuffer rasteriser: fills, lines, circles, a wire globe for
  the masthead and the drawn Kyiv night panel.
- A hand-authored 5×7 bitmap font (uppercase, lowercase, digits,
  punctuation and the accented letters the day's names need), with
  word-wrap and mixed-style rich text for the briefs.
- A three-column flow layout that packs the sections and briefs onto
  one page under a classic masthead: "THE WORLD TODAY — Saturday
  21 November 2026".

## License

MIT — see `LICENSE`.
