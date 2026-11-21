#!/usr/bin/env python3
"""THE WORLD TODAY - Saturday 21 November 2026.

Draws a complete newspaper front page in code and writes it to
/output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png outside the grader).

Pure Python standard library: the pixels are rasterised into a framebuffer
with a hand-made 5x7 bitmap font, then encoded as a PNG with zlib.
No network, no assets, fully deterministic - two runs write the same bytes.
"""

import os
import struct
import zlib

W = 1024
H = 1024

PAPER = (248, 244, 233)
INK = (22, 19, 14)
RED = (163, 22, 33)
MUTED = (97, 89, 73)
FAINT = (203, 196, 176)
NAVY = (14, 22, 46)
SKY = (43, 60, 105)
GOLD = (219, 166, 66)
SMOKE = (120, 116, 108)


# ---------------------------------------------------------------- PNG writer

def _chunk(kind, data):
    return (struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))


def _filter_row(row, prev, kind):
    """One PNG scanline filter (0 none, 1 sub, 2 up), bytes in and out."""
    out = bytearray(len(row))
    if kind == 0:
        out[:] = row
    elif kind == 1:
        for i, b in enumerate(row):
            left = row[i - 3] if i >= 3 else 0
            out[i] = (b - left) & 0xFF
    else:
        for i, b in enumerate(row):
            out[i] = (b - prev[i]) & 0xFF
    return out


def _signed_cost(buf):
    return sum(b if b < 128 else 256 - b for b in buf)


def png_bytes(width, height, rgb):
    """Encode an RGB bytearray as PNG bytes, picking the cheapest of the
    none/sub/up filters per row so the file stays small. Deterministic."""
    raw = bytearray()
    stride = width * 3
    prev = bytes(stride)
    for y in range(height):
        row = bytes(rgb[y * stride:(y + 1) * stride])
        best_kind, best = 0, None
        for kind in (0, 1, 2):
            cand = _filter_row(row, prev, kind)
            if best is None or _signed_cost(cand) < _signed_cost(best):
                best_kind, best = kind, cand
        raw.append(best_kind)
        raw.extend(best)
        prev = row
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))


# ---------------------------------------------------------------- framebuffer

class Page:
    def __init__(self, width, height, bg):
        self.w = width
        self.h = height
        self.px = bytearray(bg * (width * height))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def fill(self, x, y, w, h, color):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def hline(self, x, y, w, color, thick=1):
        self.fill(x, y, w, thick, color)

    def vline(self, x, y, h, color, thick=1):
        self.fill(x, y, thick, h, color)

    def line(self, x0, y0, x1, y1, color, thick=1):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.fill(x0 - thick // 2, y0 - thick // 2, thick, thick, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, color, thick=1):
        for a in range(720):
            import math
            t = a * math.pi / 360.0
            x = int(round(cx + r * math.cos(t)))
            y = int(round(cy + r * math.sin(t)))
            self.fill(x - thick // 2, y - thick // 2, thick, thick, color)

    def disc(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            span = int((r * r - (yy - cy) ** 2) ** 0.5)
            self.fill(cx - span, yy, 2 * span + 1, 1, color)


# ---------------------------------------------------------------- the font
# A 5x7 bitmap font, drawn by hand for this page. Each glyph is 7 rows of
# 5 pixels; '#' is ink, '.' is blank.

FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
}

FONT.update({
    "a": (".....", ".....", ".####", "....#", ".####", "#...#", ".####"),
    "b": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    "c": (".....", ".....", ".####", "#....", "#....", "#....", ".####"),
    "d": ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"),
    "e": (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    "f": ("..##.", ".#...", "####.", ".#...", ".#...", ".#...", ".#..."),
    "g": (".....", ".####", "#...#", "#...#", ".####", "....#", ".###."),
    "h": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "i": ("..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."),
    "j": ("...#.", ".....", "..##.", "...#.", "...#.", "#..#.", ".##.."),
    "k": ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    "l": (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "m": (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    "n": (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "o": (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    "p": (".....", ".....", "####.", "#...#", "####.", "#....", "#...."),
    "q": (".....", ".....", ".####", "#...#", ".####", "....#", "....#"),
    "r": (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    "s": (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    "t": (".#...", ".#...", "####.", ".#...", ".#...", ".#..#", "..##."),
    "u": (".....", ".....", "#...#", "#...#", "#...#", "#..##", ".####"),
    "v": (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "w": (".....", ".....", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."),
    "x": (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    "y": (".....", ".....", "#...#", "#...#", ".####", "....#", ".###."),
    "z": (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".....", ".##..", ".#..."),
    "'": (".##..", ".##..", ".#...", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    ":": (".....", ".##..", ".##..", ".....", ".....", ".##..", ".##.."),
    ";": (".....", ".##..", ".##..", ".....", ".....", ".##..", ".#..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "(": ("...#.", "..#..", "..#..", "..#..", "..#..", "..#..", "...#."),
    ")": (".#...", "..#..", "..#..", "..#..", "..#..", "..#..", ".#..."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "%": ("##..#", "##.#.", "....#", "...#.", "..#..", ".#...", "#..##"),
    "&": (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "*": (".....", "#.#.#", ".###.", "#####", ".###.", "#.#.#", "....."),
    "#": (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    "@": (".###.", "#...#", "#.###", "#.#.#", "#.##.", "#....", ".####"),
    "£": ("..##.", ".#...", "####.", ".#...", ".#...", "#....", "#####"),
    "€": (".###.", "#....", "#####", "#....", "#####", "#....", ".###."),
    "°": (".##..", "#..#.", ".##..", ".....", ".....", ".....", "....."),
    "·": (".....", ".....", ".....", ".....", ".##..", ".##..", "....."),
    "•": (".....", ".....", ".###.", ".###.", ".###.", ".....", "....."),
    "—": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "–": (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
})


# ---------------------------------------------------------------- text engine

def clean(s):
    """Map characters outside the font onto ones inside it."""
    return (s.replace("‘", "'").replace("’", "'")
             .replace("“", '"').replace("”", '"')
             .replace("…", "...").replace(" ", " "))


def text_w(s, scale, bold=False):
    if not s:
        return 0
    adv = 6 * scale + (1 if bold else 0)
    return len(s) * adv - scale


def draw_text(page, x, y, s, scale, color, bold=False):
    """Draw one line of text with its top at y; returns the x just past it."""
    adv = 6 * scale + (1 if bold else 0)
    off = max(1, scale // 2) if bold else 0
    for ch in clean(s):
        glyph = FONT.get(ch, FONT["?"])
        for gy, row in enumerate(glyph):
            for gx, cell in enumerate(row):
                if cell == "#":
                    page.fill(x + gx * scale, y + gy * scale, scale, scale, color)
                    if bold:
                        page.fill(x + gx * scale + off, y + gy * scale,
                                  scale, scale, color)
        x += adv
    return x


def wrap(s, scale, max_px, bold=False):
    """Greedy word wrap to lines of at most max_px pixels."""
    lines, cur = [], ""
    for word in clean(s).split():
        trial = word if not cur else cur + " " + word
        if text_w(trial, scale, bold) <= max_px or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_block(page, x, y, s, scale, color, max_px, bold=False, leading=3):
    """Draw wrapped text; returns the y just past the block."""
    for ln in wrap(s, scale, max_px, bold):
        draw_text(page, x, y, ln, scale, color, bold)
        y += 7 * scale + leading
    return y


# ---------------------------------------------------------------- the news
# Saturday 21 November 2026, gathered from the day's reporting and
# cross-checked on the lead stories. Each full story is drawn as headline,
# one-line summary and its source; briefs carry the same in one paragraph.

LEAD = {
    "kicker": "LEAD STORY · KYIV AND WARSAW",
    "headline": "Russia fires 400 drones and 110 missiles at Ukraine; "
                "two missiles fall in Poland",
    "summary": "The overnight barrage killed at least eight people in Kyiv "
               "and wrecked bridges and stations. Poland's PM Tusk called "
               "the missiles on Polish soil a deliberate provocation; NATO "
               "condemned a grave violation and moved jets.",
    "source": "France 24 · CBS News · El País",
}

TOP = [
    ("AI sell-off pushes S&P 500 into correction",
     "US stocks fell 3.7% Friday; the Nikkei lost 5.06%, gold and Bitcoin too.",
     "One Turn News"),
    ("UN court: Myanmar committed genocide of Rohingya",
     "The ICJ ruled for the Rohingya; Britain expelled Myanmar's envoy.",
     "One Turn News"),
    ("Pill makes pancreatic cancer vanish in trial",
     "Daraxonrasib left tumours undetectable in 1 in 12 patients.",
     "One Turn News"),
    ("COP31 talks run past deadline in Antalya",
     "Nearly 200 nations deadlocked over fossil fuels at the UN summit.",
     "One Turn News"),
]

SECTIONS = [
    ("EUROPE", [
        ("UK and EU sign biggest post-Brexit agreements",
         "PM Burnham and EU leaders signed deals on food exports, carbon and youth mobility.",
         "One Turn News"),
        ("Gen Z protests sweep 25 European countries",
         "Thousands of students marched over living costs, military spending and climate.",
         "One Turn News"),
        ("Spain heads to Nov. 29 election",
         "Conservatives gain as PM Sánchez conceded 'mistakes' before the vote.",
         "One Turn News"),
        ("Kryvyi Rih strike kills two and wounds dozens",
         "A Russian strike on the city wounded dozens of people, four children among them.",
         "One Turn News"),
    ]),
    ("NORTH AMERICA", [
        ("FBI criminal database reportedly hacked",
         "The FBI crime database was reportedly hacked as US outages continued.",
         "CNN"),
        ("Man convicted over deadly Palisades fire",
         "He was convicted in Los Angeles of starting the deadly Palisades fire.",
         "One Turn News"),
        ("Indian man jailed 19 years in Sikh plot",
         "He was sentenced in New York over a plot to murder a Sikh separatist leader.",
         "One Turn News"),
        ("Bayer's $7.25bn Roundup deal approved",
         "A US judge approved Bayer's $7.25 billion settlement of Roundup claims.",
         "One Turn News"),
        ("Trump defends Putin, Xi ties after summit",
         "The three leaders' Shenzhen declaration omitted any section on Ukraine.",
         "One Turn News"),
    ]),
    ("MIDDLE EAST", [
        ("Israeli strikes kill Palestinians in Gaza",
         "Strikes killed Palestinians in Gaza; raids and violence continued in the West Bank.",
         "One Turn News"),
        ("Saudi coalition stops Houthi missiles",
         "Defences stopped missiles aimed at Riyadh after a strike damaged the PIF tower.",
         "One Turn News"),
        ("Trump: 'We have time' as Iran war runs on",
         "Trump signalled the war will continue into 2027; Hormuz attacks go on, talks stall.",
         "One Turn News"),
    ]),
    ("AFRICA", [
        ("Boat with funeral mourners capsizes",
         "The boat capsized in the waters of Bayelsa State, in the Niger Delta.",
         "One Turn News"),
        ("Tanzania opposition chief convicted",
         "A Dar es Salaam court convicted Tundu Lissu, the opposition leader, of sedition.",
         "One Turn News"),
    ]),
    ("ASIA-PACIFIC", [
        ("Seoul court overturns ex-PM Han sentence",
         "Seoul's top court overturned the 15-year sentence and ordered a retrial.",
         "World News"),
    ]),
    ("LATIN AMERICA & CARIBBEAN", [
        ("Magnitude 6.7 earthquake shakes central Peru",
         "A magnitude 6.7 earthquake struck central Peru on Saturday.",
         "One Turn News"),
    ]),
    ("SCIENCE & SPACE", [
        ("Voyager 1 now a full light-day from Earth",
         "Launched 49 years ago, Voyager 1 is 24 light-hours out; signals take a day.",
         "NASA"),
    ]),
    ("SPORT & CULTURE", [
        ("Alcaraz beats Cobolli, unbeaten in Turin",
         "Carlos Alcaraz beat Flavio Cobolli in Turin, unbeaten in group play.",
         "One Turn News"),
        ("Morocco hit six past Fiji at U-17 World Cup",
         "Morocco beat Fiji 6-0; Mali beat New Zealand 3-0 in the group stage.",
         "Friends of Football"),
    ]),
]

BRIEFS = [
    ("Estonia to close its Russian border crossings", "Narva posts to shut.", "One Turn News"),
    ("French police sentenced over beating", "Paris court rules on 2020 attack.", "One Turn News"),
    ("Depardieu, Houellebecq face inquiry", "France investigates alleged gang rape.", "One Turn News"),
    ("EU agrees €1bn for Ukraine drones, air defence", "New package for Kyiv's defences.", "Euronews"),
    ("Court lets Trump end Venezuelan protections", "TPS for 600,000 people can lapse.", "World News"),
    ("Bukele to register for a third term", "El Salvador votes on Feb. 28, 2027.", "World News"),
    ("Salvadoran troops lose soldiers in Haiti", "Explosives hit the security mission.", "One Turn News"),
    ("Iraq moves into Jurf al-Sakhar stronghold", "Entry agreed in a negotiated deal.", "One Turn News"),
    ("Kenya begins onshore crude drilling", "Drilling starts in Turkana County.", "One Turn News"),
    ("South Korea ruling party targets chief justice", "Impeachment move in Seoul.", "One Turn News"),
    ("Teen accused of organising arsons on Signal", "Police link blazes to the chat app.", "One Turn News"),
    ("BepiColombo reaches Mercury after eight years", "ESA-JAXA probe enters orbit.", "One Turn News"),
    ("X-ray laser beats the spacing of atoms", "Hamburg flashes shorter than atomic gaps.", "One Turn News"),
    ("Curiosity photographs twilight clouds on Mars", "Drifting clouds over Gale Crater.", "One Turn News"),
    ("Study rethinks human family tree", "Taung fossils question species groups.", "One Turn News"),
    ("Blue sucker fish live past 100", "Missouri River fish outlive a century.", "One Turn News"),
    ("Compound burns fat but spares muscle", "Berkeley trial of an experimental drug.", "One Turn News"),
    ("Oil steady near $90 despite Gulf attacks", "Glut fears balance Middle East risk.", "One Turn News"),
    ("Washington Spirit reach NWSL final", "Spirit win through to the title game.", "One Turn News"),
    ("Choi Min-jeong cruises in Seoul short track", "Easy progress at the World Tour stop.", "One Turn News"),
    ("Mao Shimada leads Finlandia Trophy", "Ahead after the short program in Espoo.", "One Turn News"),
    ("Bayliss goal saves Auckland", "89th-minute goal earns 1-1 Victory draw.", "Friends of Football"),
    ("Giant tree rises in St Peter's Square", "Vatican raises its holiday tree.", "One Turn News"),
    ("Rabbit island draws crowds in Japan", "Okunoshima draws visitors yearly.", "One Turn News"),
    ("Six killed in Tbilisi gas blast", "Apartment block partly collapsed.", "World News"),
    ("Argentina risk index tops 1,000 points", "Bonds slump in Buenos Aires.", "One Turn News"),
    ("Uganda curbs gatherings over Ebola threat", "Travel restricted around Kampala.", "One Turn News"),
    ("Nepal PM to make first India visit", "Balendra Shah heads to Delhi.", "One Turn News"),
    ("CERN finds ultra-rare particle decay", "First evidence reported in Geneva.", "One Turn News"),
    ("Saudi Arabia, Japan agree oil stockpile deal", "Pact signed in Tokyo.", "One Turn News"),
    ("US sells deep-sea mining leases", "Leases off American Samoa sold.", "One Turn News"),
    ("A Lim Kim leads LPGA finale", "Hole-in-one gives her a two-shot lead.", "One Turn News"),
    ("Ancient supermountains in Antarctica", "Found beneath the ice.", "One Turn News"),
]


# Accented letters used by the day's names (Sánchez, El País, Bogotá...).
FONT.update({
    "á": (".#...", ".#...", ".####", "....#", ".####", "#...#", ".####"),
    "é": ("...#.", "..#..", ".###.", "#...#", "#####", "#....", ".###."),
    "í": ("..#..", ".#...", ".##..", "..#..", "..#..", "..#..", ".###."),
    "ó": ("...#.", "..#..", ".###.", "#...#", "#...#", "#...#", ".###."),
    "ú": ("...#.", "..#..", "#...#", "#...#", "#...#", "#..##", ".####"),
    "ñ": (".....", ".#.#.", "####.", "#...#", "#...#", "#...#", "#...#"),
    "ü": (".....", ".#.#.", "#...#", "#...#", "#...#", "#..##", ".####"),
    "ç": (".....", ".....", ".####", "#....", "#....", ".####", ".#..."),
})


# ---------------------------------------------------------------- artwork

def draw_globe(page, cx, cy, r, color):
    """A wire globe: rim, meridians and parallels, for the masthead."""
    import math
    page.circle(cx, cy, r, color, 2)
    for frac in (0.35, 0.7, 1.0):
        rx = max(1, int(r * frac))
        for a in range(90):
            t = a * math.pi / 45.0
            x = int(round(cx + rx * math.cos(t)))
            y = int(round(cy + r * math.sin(t)))
            page.set(x, y, color)
            page.set(x, y + 1, color)
    for frac in (-0.6, -0.3, 0.0, 0.3, 0.6):
        yy = int(round(cy + r * frac))
        half = int(r * (1 - frac * frac) ** 0.5)
        page.hline(cx - half, yy, 2 * half, color, 1)


def draw_lead_art(page, x, y, w, h):
    """Night over Kyiv, drawn in code: skyline, lit windows, missile
    trails and a burst - an illustration, not a photograph."""
    import math
    page.fill(x, y, w, h, NAVY)
    for i in range(6):  # sky lightens toward the horizon
        shade = (43 + i * 6, 60 + i * 7, 105 + i * 8)
        page.fill(x, y + h - (i + 1) * 5, w, 5, shade)
    seed = 1234567  # deterministic star field
    for _ in range(46):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        sx = x + seed % (w - 4)
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        sy = y + seed % (h // 2)
        page.set(sx, sy, (210, 214, 226))
    base = y + h
    towers = [(0, 34, 26), (30, 52, 34), (70, 40, 22), (96, 62, 40),
              (142, 44, 26), (172, 56, 30), (206, 38, 24), (234, 58, 36),
              (274, 42, 28)]
    for tx, th, tw in towers:  # skyline silhouettes with lit windows
        page.fill(x + tx, base - th, tw, th, (8, 10, 18))
        for wy in range(base - th + 5, base - 6, 8):
            for wx in range(x + tx + 4, x + tx + tw - 3, 7):
                if (wx * 31 + wy * 17) % 5 < 2:
                    page.fill(wx, wy, 2, 3, GOLD)
    for (sx, sy, ex, ey) in ((x + 30, y + 8, x + 120, base - 58),
                             (x + 96, y + 4, x + 190, base - 66),
                             (x + 250, y + 10, x + 168, base - 50)):
        steps = 26  # a missile trail arcing down to the city
        for i in range(steps + 1):
            t = i / steps
            px = int(sx + (ex - sx) * t)
            py = int(sy + (ey - sy) * t + 26 * t * t)
            page.fill(px, py, 2, 2, SMOKE)
        page.disc(ex, ey, 3, GOLD)
    cx, cy = x + 190, base - 66  # the burst where one trail ends
    for a in range(12):
        t = a * math.pi / 6.0
        x2 = int(cx + 13 * math.cos(t))
        y2 = int(cy + 13 * math.sin(t))
        page.line(cx, cy, x2, y2, RED, 2)
    page.disc(cx, cy, 4, (240, 120, 60))
    for dx, dy in ((-14, -30), (20, -22)):  # two drones, simple crosses
        page.line(x + 150 + dx - 5, y + 40 + dy, x + 150 + dx + 5, y + 40 + dy, (200, 204, 214), 2)
        page.line(x + 150 + dx, y + 40 + dy - 4, x + 150 + dx, y + 40 + dy + 4, (200, 204, 214), 2)
    page.fill(x, base - 12, w, 12, INK)
    cap = "KYIV BEFORE DAWN — TRAILS OVER THE CAPITAL"
    draw_text(page, x + (w - text_w(cap, 1)) // 2, base - 9, cap, 1, PAPER)
    for i in range(2):  # frame
        page.hline(x - 1 + i * 0, y - 1, w + 2, INK, 1)
        page.hline(x - 1, y + h, w + 2, INK, 1)
        break


# ---------------------------------------------------------------- rich text

def rich_words(segments, scale):
    """Split styled segments into (word, bold, color) tokens."""
    out = []
    for text, bold, color in segments:
        for word in clean(text).split():
            out.append((word, bold, color))
    return out


def draw_rich(page, x, y, segments, scale, max_px, leading=1):
    """Wrapped mixed-style paragraph; returns the y just past it."""
    space_w = 6 * scale
    lines, cur, cur_w = [], [], 0
    for word, bold, color in rich_words(segments, scale):
        ww = text_w(word, scale, bold)
        add = ww if not cur else ww + space_w
        if cur and cur_w + add > max_px:
            lines.append(cur)
            cur, cur_w = [(word, bold, color)], ww
        else:
            cur.append((word, bold, color))
            cur_w += add
    if cur:
        lines.append(cur)
    for line in lines:
        lx = x
        for word, bold, color in line:
            draw_text(page, lx, y, word, scale, color, bold)
            lx += text_w(word, scale, bold) + space_w
        y += 7 * scale + leading
    return y


# ---------------------------------------------------------------- layout

import sys

MX = 28
CW = W - 2 * MX
COLW = 312
GUT = 16
BODY = (74, 68, 56)


def story_h(story, w):
    headline, summary, source = story
    hl = len(wrap(headline, 2, w, bold=True))
    sl = len(wrap(summary + " (" + source + ")", 1, w))
    return hl * 15 + sl * 8 + 4


def draw_story(page, x, y, w, story):
    headline, summary, source = story
    y = draw_block(page, x, y, headline, 2, INK, w, bold=True, leading=1)
    y = draw_block(page, x, y, summary + " (" + source + ")", 1, BODY, w,
                   leading=1)
    return y + 4


def brief_segments(brief):
    headline, summary, source = brief
    return [(headline, True, INK), (" — " + summary, False, BODY),
            (" (" + source + ")", False, RED)]


def rich_count(segments, scale, max_px):
    space_w = 6 * scale
    lines, cur_w, first = 1, 0, True
    for word, bold, _color in rich_words(segments, scale):
        ww = text_w(word, scale, bold)
        add = ww if first else ww + space_w
        if not first and cur_w + add > max_px:
            lines += 1
            cur_w = ww
        else:
            cur_w += add
        first = False
    return lines


def brief_h(brief, w):
    return rich_count(brief_segments(brief), 1, w) * 8 + 3


def draw_brief(page, x, y, w, brief):
    return draw_rich(page, x, y, brief_segments(brief), 1, w, leading=1) + 3


def draw_section_header(page, x, y, w, name):
    page.fill(x, y, w, 19, INK)
    draw_text(page, x + 8, y + 3, name, 2, PAPER, bold=True)
    return y + 22


def render():
    page = Page(W, H, PAPER)
    total = 1 + len(TOP) + sum(len(s) for _n, s in SECTIONS) + len(BRIEFS)

    # Masthead
    page.hline(MX, 12, CW, INK, 3)
    page.hline(MX, 18, CW, INK, 1)
    draw_globe(page, MX + 26, 47, 23, INK)
    title = "THE WORLD TODAY"
    draw_text(page, (W - text_w(title, 7, True)) // 2, 25, title, 7, INK,
              bold=True)
    vol = "VOL. 1 · NO. 21"
    draw_text(page, MX + CW - text_w(vol, 1), 44, vol, 1, MUTED)
    y = 82
    draw_text(page, MX, y + 3, "ONE DAY IN ONE PAGE", 1, MUTED, bold=True)
    date = "SATURDAY 21 NOVEMBER 2026"
    draw_text(page, (W - text_w(date, 2, True)) // 2, y, date, 2, INK,
              bold=True)
    right = "%d STORIES · 7 REGIONS" % total
    draw_text(page, MX + CW - text_w(right, 1, True), y + 3, right, 1, MUTED,
              bold=True)
    page.hline(MX, 102, CW, RED, 3)
    page.hline(MX, 108, CW, INK, 1)

    # Lead story, with the drawn night-sky panel beside its headline
    y = 116
    draw_text(page, MX, y, LEAD["kicker"], 2, RED, bold=True)
    hy = y + 18
    end_y = draw_block(page, MX, hy, LEAD["headline"], 3, INK, CW - 322,
                       bold=True, leading=2)
    draw_lead_art(page, MX + CW - 302, y, 302, end_y - y - 2)
    end_y = draw_block(page, MX, end_y + 4, LEAD["summary"], 2, INK, CW,
                       leading=2)
    draw_text(page, MX, end_y + 1, "SOURCES: " + LEAD["source"].upper(), 1,
              RED, bold=True)
    y = end_y + 12
    page.hline(MX, y, CW, INK, 1)
    y += 8

    # Top stories strip: four blocks under red rules
    bw = (CW - 3 * GUT) // 4
    strip_bottom = y
    for i, story in enumerate(TOP):
        bx = MX + i * (bw + GUT)
        page.hline(bx, y, bw, RED, 3)
        by = draw_block(page, bx, y + 7, story[0], 2, INK, bw, bold=True,
                        leading=1)
        by = draw_block(page, bx, by + 2, story[1] + " (" + story[2] + ")",
                        1, BODY, bw, leading=1)
        strip_bottom = max(strip_bottom, by)
    y = strip_bottom + 8
    page.hline(MX, y, CW, INK, 1)
    y += 8

    # The grid: sections flow down three columns
    bottom = 1002
    cols = [MX + i * (COLW + GUT) for i in range(3)]
    ci, cy = 0, y
    overflow = []
    for name, stories in list(SECTIONS) + [("IN BRIEF", None)]:
        briefs_mode = stories is None
        items = BRIEFS if briefs_mode else stories
        for idx, item in enumerate(items):
            ih = brief_h(item, COLW) if briefs_mode else story_h(item, COLW)
            need = ih + (22 if idx == 0 else 0)
            if cy + need > bottom:
                ci += 1
                cy = y
            if ci > 2:
                overflow.append(item)
                continue
            if idx == 0:
                cy = draw_section_header(page, cols[ci], cy, COLW, name)
            if briefs_mode:
                cy = draw_brief(page, cols[ci], cy, COLW, item)
            else:
                cy = draw_story(page, cols[ci], cy, COLW, item)

    page.hline(MX, 1006, CW, INK, 1)
    foot = ("EVERY STORY SOURCED AND DATED · DRAWN IN CODE BY MAIN.PY · "
            "NO PHOTOGRAPHS")
    draw_text(page, (W - text_w(foot, 1)) // 2, 1011, foot, 1, MUTED)
    return page, overflow


def main():
    page, overflow = render()
    data = png_bytes(W, H, page.px)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    try:
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, "entry.png")
        with open(path, "wb") as fh:
            fh.write(data)
    except OSError:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "entry.png")
        with open(path, "wb") as fh:
            fh.write(data)
    if overflow:
        print("warning: %d stories did not fit" % len(overflow),
              file=sys.stderr)


if __name__ == "__main__":
    main()
