#!/usr/bin/env python3
"""news-image-20261126-b: draw one 1024x1024 PNG summing up the world news of
Thursday 26 November 2026. Pure standard library: a small framebuffer, a 5x7
bitmap font, filled continent polygons for a stylised world map, and a 36-story
grid across 11 regions. Deterministic: same bytes on every run.
Run:  MAKEFUN_OUTPUT_DIR=out python3 main.py   (writes out/entry.png)
"""
import hashlib
import os
import struct
import sys
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
BG = (13, 27, 46)
PANEL = (24, 44, 68)
PANEL_EDGE = (64, 98, 138)
GOLD = (214, 178, 60)
GOLD_DIM = (170, 140, 55)
WHITE = (238, 240, 238)
MUTED = (148, 164, 180)
OCEAN = (17, 45, 70)
LAND = (122, 156, 112)
LAND_EDGE = (88, 120, 84)
DOT = (224, 62, 48)
DOT_RING = (255, 255, 255)
GRID_LINE = (48, 76, 108)

REGION_COLORS = {
    "MIDEAST": (235, 120, 80),
    "N.AMERICA": (110, 180, 235),
    "MARKETS": (235, 205, 90),
    "EUROPE": (150, 170, 235),
    "E.ASIA": (235, 150, 190),
    "S.ASIA": (255, 170, 60),
    "SE.ASIA": (120, 220, 180),
    "AFRICA": (230, 200, 130),
    "S.AMERICA": (160, 220, 110),
    "SCIENCE": (190, 150, 235),
    "TECH": (110, 210, 220),
}

# ---------------------------------------------------------------- 5x7 font
# Each glyph is 7 rows of 5 bits ("#" on, "." off). Uppercase + digits +
# the punctuation the strings below use.
FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
    "3": ["11111", "00010", "00100", "00010", "00001", "10001", "01110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    ",": ["00000", "00000", "00000", "00000", "01100", "00100", "01000"],
    ":": ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
    "'": ["00100", "00100", "01000", "00000", "00000", "00000", "00000"],
    "-": ["00000", "00000", "00000", "01110", "00000", "00000", "00000"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    "%": ["11001", "11010", "00010", "00100", "01000", "01011", "10011"],
    "$": ["00100", "01111", "10100", "01110", "00101", "11110", "00100"],
    "(": ["00010", "00100", "01000", "01000", "01000", "00100", "00010"],
    ")": ["01000", "00100", "00010", "00010", "00010", "00100", "01000"],
    "&": ["01100", "10010", "10100", "01000", "10101", "10010", "01101"],
    "!": ["00100", "00100", "00100", "00100", "00100", "00000", "00100"],
    "?": ["01110", "10001", "00001", "00110", "00100", "00000", "00100"],
    "+": ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
    "=": ["00000", "00000", "11111", "00000", "11111", "00000", "00000"],
    "*": ["00000", "00100", "10101", "01110", "10101", "00100", "00000"],
}

# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = c

    def rect(self, x0, y0, x1, y1, c):
        for y in range(max(0, y0), min(self.h, y1)):
            base = (y * self.w + max(0, x0)) * 3
            for x in range(max(0, x0), min(self.w, x1)):
                self.px[base], self.px[base + 1], self.px[base + 2] = c
                base += 3

    def hline(self, x0, x1, y, c):
        for x in range(max(0, x0), min(self.w, x1)):
            self.set(x, y, c)

    def vline(self, x, y0, y1, c):
        for y in range(max(0, y0), min(self.h, y1)):
            self.set(x, y, c)

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def polyline(self, pts, c):
        for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
            self.line(ax, ay, bx, by, c)

    def fill_poly(self, pts, c):
        # Even-odd scanline fill.
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
                if ay == by:
                    continue
                if (ay <= y < by) or (by <= y < ay):
                    t = (y - ay) / (by - ay)
                    xs.append(ax + t * (bx - ax))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                for x in range(int(xs[j]) + 1, int(xs[j + 1]) + 1):
                    self.set(x, y, c)

    def circle(self, cx, cy, r, c, fill=True):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                d = (x - cx) ** 2 + (y - cy) ** 2
                if fill and d <= r * r:
                    self.set(x, y, c)
                elif not fill and r * r - 2 * r <= d <= r * r:
                    self.set(x, y, c)

    def text(self, x, y, s, scale, c):
        cx = x
        for ch in s:
            g = FONT.get(ch, FONT[" "])
            for row, bits in enumerate(g):
                for col, bit in enumerate(bits):
                    if bit == "1":
                        self.rect(cx + col * scale, y + row * scale,
                                  cx + (col + 1) * scale, y + (row + 1) * scale, c)
            cx += 6 * scale

    def text_w(self, s, scale):
        return len(s) * 6 * scale - scale

    def text_center(self, y, s, scale, c):
        self.text((self.w - self.text_w(s, scale)) // 2, y, s, scale, c)


# ---------------------------------------------------------------- map data
# Rough continent outlines as (lon, lat) pairs, equirectangular.
CONTINENTS = [
    # North America
    [(-168, 66), (-150, 70), (-135, 69), (-125, 71), (-110, 73), (-95, 80),
     (-85, 70), (-78, 62), (-68, 58), (-60, 55), (-55, 47), (-60, 44),
     (-70, 42), (-75, 35), (-80, 26), (-84, 30), (-90, 21), (-97, 16),
     (-104, 20), (-112, 28), (-120, 34), (-125, 42), (-125, 49),
     (-135, 58), (-150, 60), (-165, 60)],
    # Greenland
    [(-58, 64), (-48, 60), (-40, 68), (-30, 74), (-38, 79), (-55, 78), (-60, 73)],
    # South America
    [(-80, 9), (-74, 11), (-62, 10), (-52, 5), (-50, 0), (-44, -3),
     (-35, -8), (-39, -15), (-41, -22), (-48, -28), (-54, -34),
     (-62, -41), (-66, -47), (-69, -53), (-73, -50), (-73, -40),
     (-72, -30), (-70, -20), (-77, -12), (-80, -4), (-81, 3)],
    # Africa
    [(-17, 15), (-13, 27), (-6, 33), (0, 36), (10, 37), (20, 32),
     (30, 31), (35, 28), (39, 21), (43, 12), (51, 11), (48, 3),
     (40, -6), (39, -15), (35, -22), (30, -29), (26, -34), (19, -35),
     (16, -28), (13, -18), (9, 4), (-4, 5), (-13, 8), (-17, 15)],
    # Europe
    [(-10, 36), (-9, 43), (-2, 48), (0, 51), (4, 53), (8, 57),
     (10, 59), (13, 56), (19, 55), (24, 58), (28, 59), (24, 62),
     (21, 65), (18, 69), (14, 70), (8, 63), (5, 59), (5, 57),
     (0, 50), (-4, 48), (-8, 44), (-10, 39)],
    # Asia (mainland)
    [(28, 41), (30, 45), (30, 52), (33, 58), (40, 64), (50, 68),
     (60, 69), (70, 72), (85, 75), (100, 77), (115, 76), (130, 72),
     (145, 72), (160, 70), (170, 67), (178, 65), (170, 60), (162, 57),
     (156, 52), (142, 50), (140, 42), (135, 35), (129, 33), (127, 35),
     (122, 39), (120, 31), (112, 22), (108, 18), (105, 10), (101, 7),
     (98, 10), (95, 16), (91, 22), (86, 20), (80, 15), (77, 8),
     (74, 13), (70, 20), (66, 25), (61, 25), (56, 26), (52, 28),
     (48, 30), (44, 29), (39, 31), (36, 36), (33, 36), (30, 36),
     (28, 38)],
    # South-East Asian islands
    [(95, 5), (98, 2), (101, -2), (105, -5), (110, -7), (115, -8),
     (120, -10), (125, -9), (130, -4), (135, -3), (140, -7), (141, -3),
     (136, -1), (131, 0), (126, 1), (121, 2), (116, 3), (111, 2),
     (106, 4), (101, 6), (97, 7)],
    # Australia
    [(114, -22), (114, -31), (118, -35), (124, -33), (130, -32), (136, -35),
     (140, -38), (146, -39), (150, -37), (153, -27), (150, -22),
     (146, -19), (142, -11), (137, -12), (132, -12), (126, -14),
     (122, -17), (118, -20), (114, -22)],
    # Britain
    [(-5, 50), (-3, 53), (-5, 56), (-4, 58), (-2, 58), (0, 54), (-1, 51), (-4, 50)],
    # Japan
    [(130, 31), (132, 33), (135, 34), (137, 35), (139, 37), (141, 40),
     (143, 43), (145, 44), (143, 44), (141, 41), (139, 38), (136, 36),
     (133, 34), (131, 32)],
    # New Zealand
    [(167, -45), (169, -43), (172, -41), (175, -38), (177, -38),
     (176, -40), (174, -42), (171, -44), (168, -46)],
]

# Hotspots plotted on the map: (lon, lat, label, label dx, label dy).
HOTSPOTS = [
    (47, 25, "RIYADH", 6, -10),
    (56, 26, "HORMUZ", 6, 6),
    (34, 31, "GAZA", -34, -10),
    (30, 50, "KYIV", -30, -10),
    (121, 25, "TAIPEI", 6, -10),
    (77, 28, "DELHI", 6, 6),
    (37, -1, "NAIROBI", 6, -10),
    (3, 6, "LAGOS", 6, 6),
    (-48, -16, "BRASILIA", -52, -10),
    (116, 40, "BEIJING", 6, -10),
]

MAP = {"x0": 28, "y0": 108, "x1": 996, "y1": 296}


def project(lon, lat):
    x = MAP["x0"] + (lon + 180.0) / 360.0 * (MAP["x1"] - MAP["x0"])
    y = MAP["y0"] + (83.0 - lat) / 139.0 * (MAP["y1"] - MAP["y0"])
    return int(round(x)), int(round(y))


# ---------------------------------------------------------------- stories
# 36 stories, each (region, line 1, line 2). Every line <= 25 chars.
STORIES = [
    ("MIDEAST", "HOUTHIS CLAIM STRIKE", "ON SAUDI REFINERY"),
    ("MIDEAST", "TWO TANKERS HIT MINES", "IN STRAIT OF HORMUZ"),
    ("MIDEAST", "ISRAELI STRIKE KILLS", "HAMAS OFFICIAL IN GAZA"),
    ("N.AMERICA", "US UNVEILS TARIFFS ON", "14 TRADING PARTNERS"),
    ("MARKETS", "DOW ERASES 1,000-POINT", "PLUNGE TO CLOSE HIGHER"),
    ("MARKETS", "NASDAQ -0.6% AS NVIDIA", "FALLS 4% IN AI ROUT"),
    ("MARKETS", "FED: MODEST GROWTH,", "STUBBORN PRICE PRESSURE"),
    ("N.AMERICA", "THANKSGIVING NFL", "TRIPLE-HEADER KICKS OFF"),
    ("EUROPE", "RUSSIA: NEARLY 500,000", "WAR DEAD, OWN FIGURES"),
    ("EUROPE", "RUSSIA APPROVES $600BN+", "MILITARY BUDGET TO 2029"),
    ("EUROPE", "NORWAY COURT VOIDS", "DISPUTED OIL LICENCES"),
    ("EUROPE", "EU HUNTS NEW ECB CHIEF", "AS LAGARDE RESIGNS"),
    ("EUROPE", "ROMA 2-2 PSG ENDS", "PARIS WINNING RUN"),
    ("E.ASIA", "TAIWAN STOCKS PLUNGE", "1,927 POINTS IN A DAY"),
    ("E.ASIA", "US PROPOSES 15% TARIFF", "ON TAIWAN GOODS"),
    ("E.ASIA", "PAKISTANI ASTRONAUT JOINS", "CHINA SHENZHOU-24 CREW"),
    ("E.ASIA", "XI GRAFT PROBE HITS", "SHANGHAI RISING STAR"),
    ("E.ASIA", "N. KOREA EXPELS SWISS", "DIPLOMAT IN SANCTIONS ROW"),
    ("S.ASIA", "INDIA MARKS CONSTITUTION", "DAY, 18 YRS SINCE 26/11"),
    ("S.ASIA", "INDIA GIVES NEPAL", "RS 15,000-CRORE PACKAGE"),
    ("S.ASIA", "GUKESH VS SINDAROV IN", "WORLD CHESS TITLE MATCH"),
    ("S.ASIA", "SOORYAVANSHI, 15, HITS", "RECORD 204 OFF 53 BALLS"),
    ("S.ASIA", "BANGLADESH LIFTS GARMENT", "WAGE BY 36%"),
    ("SE.ASIA", "DUTERTE TRIAL: ICC TO", "CALL ABOUT 100 WITNESSES"),
    ("SE.ASIA", "MANILA ENVOY PRESENTS", "CREDENTIALS TO KIM JONG UN"),
    ("AFRICA", "KENYA'S LAST EBOLA", "PATIENT DISCHARGED"),
    ("AFRICA", "DRC EBOLA TOLL PASSES", "5,300 DEAD"),
    ("AFRICA", "GHANA UNVEILS HERITAGE", "BANKNOTES HONOR NKRUMAH"),
    ("AFRICA", "NIGERIA STARTS BUILDING", "ITS OWN NAVAL SHIPS"),
    ("AFRICA", "S. AFRICA BEAT PAKISTAN", "BY 8 WICKETS IN 2ND TEST"),
    ("AFRICA", "ECOWAS APPROVES PLAN FOR", "REGIONAL FORCE BY 2027"),
    ("S.AMERICA", "COLOMBIA POLICE FREE 20", "HOSTAGES AFTER 17 HOURS"),
    ("S.AMERICA", "BRAZIL MOSQUITO RELEASE", "CUTS VIRAL CASES 68%"),
    ("SCIENCE", "HERA PROBE NEARS ASTEROID", "HIT TO TEST DEFENCES"),
    ("TECH", "US TIGHTENS REMOTE ACCESS", "TO AI CHIPS ABROAD"),
    ("MARKETS", "BITCOIN SLIPS TO $59,258", "AS ETHER FALLS TO $1,661"),
]


def draw_map(cv):
    cv.rect(MAP["x0"], MAP["y0"], MAP["x1"], MAP["y1"], OCEAN)
    # faint graticule
    for lon in range(-150, 181, 30):
        x, _ = project(lon, 0)
        cv.vline(x, MAP["y0"], MAP["y1"], (26, 60, 90))
    for lat in (60, 30, 0, -30):
        _, y = project(0, lat)
        cv.hline(MAP["x0"], MAP["x1"], y, (26, 60, 90))
    for poly in CONTINENTS:
        pts = [project(lon, lat) for lon, lat in poly]
        cv.fill_poly(pts, LAND)
        cv.polyline(pts, LAND_EDGE)
    for lon, lat, label, dx, dy in HOTSPOTS:
        x, y = project(lon, lat)
        cv.circle(x, y, 5, DOT_RING, fill=False)
        cv.circle(x, y, 3, DOT)
        cv.text(x + dx, y + dy, label, 1, WHITE)
    cv.text(MAP["x0"] + 6, MAP["y1"] - 12, "HOTSPOTS: RED DOTS", 1, MUTED)


def draw_header(cv):
    cv.text_center(12, "THE WORLD IN ONE DAY", 3, WHITE)
    cv.text_center(46, "THURSDAY 26 NOVEMBER 2026", 4, GOLD)
    cv.text_center(82, "36 STORIES - 11 REGIONS - ONE DAY OF NEWS", 1, GOLD_DIM)
    cv.hline(28, 996, 100, GOLD)
    cv.hline(28, 996, 101, GOLD)


def draw_grid(cv):
    x0, y0 = 24, 306
    col_w, row_h, gap_x, gap_y = 318, 54, 10, 3
    for i, (region, l1, l2) in enumerate(STORIES):
        col, row = i % 3, i // 3
        x = x0 + col * (col_w + gap_x)
        y = y0 + row * (row_h + gap_y)
        cv.rect(x, y, x + col_w, y + row_h, PANEL)
        cv.hline(x, x + col_w, y, PANEL_EDGE)
        cv.hline(x, x + col_w, y + row_h - 1, PANEL_EDGE)
        cv.vline(x, y, y + row_h, PANEL_EDGE)
        cv.vline(x + col_w - 1, y, y + row_h, PANEL_EDGE)
        cv.text(x + 8, y + 5, "%02d  %s" % (i + 1, region), 1, REGION_COLORS[region])
        cv.text(x + 8, y + 17, l1, 2, WHITE)
        cv.text(x + 8, y + 33, l2, 2, WHITE)


def draw_footer(cv):
    cv.text_center(994,
                   "ALL EVENTS HAPPENED OR WERE FIRST REPORTED ON 26 NOVEMBER 2026", 1, MUTED)


def render():
    cv = Canvas(W, H, BG)
    draw_header(cv)
    draw_map(cv)
    draw_grid(cv)
    draw_footer(cv)
    return cv.px


# ---------------------------------------------------------------- PNG out
def png_bytes(rgb):
    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    idat = zlib.compress(bytes(raw), 9)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError:
        out_dir = "out"
        os.makedirs(out_dir, exist_ok=True)
    data = png_bytes(render())
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print("WROTE %s %d bytes sha256=%s"
          % (path, len(data), hashlib.sha256(data).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
