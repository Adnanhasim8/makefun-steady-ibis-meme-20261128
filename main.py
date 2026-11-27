#!/usr/bin/env python3
"""Meme Sprint 3: AI Agent Goes Rogue.

Writes one image meme to /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png).

Stdlib only: the PNG is encoded by hand (zlib + struct), text is drawn
with an embedded 5x7 bitmap font, and the scene is flat-cartoon vector
shapes. No network, no third-party imports, deterministic output.

The joke: "I ASKED MY AI AGENT TO CUT COSTS" / "IT FIRED ME."
A robot sits behind a desk wearing a tie, nameplate "CEO", holding a
pink slip, while its human owner walks out the door with a cardboard box.
"""
import os
import struct
import zlib

W, H = 1024, 1024
MAX_BYTES = 1_048_576

# ---------------------------------------------------------------- font ----
# 5x7 bitmap font, rows top->bottom, '#' = ink. Uppercase, digits and the
# punctuation this meme needs.
GLYPHS = {
    " ": ["....."] * 7,
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".####", "#....", "#....", "#....", "#....", "#....", ".####"],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    "0": [".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
    ".": [".....", ".....", ".....", ".....", ".....", ".....", ".##.."],
    ",": [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."],
    "!": ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."],
    "?": [".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."],
    "'": ["..#..", "..#..", "..#..", ".....", ".....", ".....", "....."],
    "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
    ":": [".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."],
    "(": ["...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."],
    ")": [".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."],
    "/": ["....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."],
    "+": [".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."],
    "=": [".....", ".....", "#####", ".....", "#####", ".....", "....."],
}

# ---------------------------------------------------------------- canvas --
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg) * (w * h)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = c

    def rect(self, x0, y0, x1, y1, c):
        x0 = max(0, x0); y0 = max(0, y0)
        x1 = min(self.w, x1); y1 = min(self.h, y1)
        for y in range(y0, y1):
            i = (y * self.w + x0) * 3
            row = bytes(c) * (x1 - x0)
            self.px[i:i + len(row)] = row

    def circle(self, cx, cy, r, c):
        for y in range(cy - r, cy + r + 1):
            dx = int((r * r - (y - cy) ** 2) ** 0.5) if abs(y - cy) <= r else 0
            self.rect(cx - dx, y, cx + dx + 1, y + 1, c)

    def line(self, x0, y0, x1, y1, t, c):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for s in range(steps + 1):
            x = round(x0 + (x1 - x0) * s / steps)
            y = round(y0 + (y1 - y0) * s / steps)
            self.circle(x, y, t // 2, c)

    def poly(self, pts, c):
        # scanline fill for a simple polygon
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            for i in range(len(pts)):
                (ax, ay), (bx, by) = pts[i], pts[(i + 1) % len(pts)]
                if ay == by:
                    continue
                if (ay <= y < by) or (by <= y < ay):
                    xs.append(ax + (y - ay) * (bx - ax) / (by - ay))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.rect(int(xs[k]), y, int(xs[k + 1]) + 1, y + 1, c)

    def rrect(self, x0, y0, x1, y1, r, c):
        self.rect(x0 + r, y0, x1 - r, y1, c)
        self.rect(x0, y0 + r, x1, y1 - r, c)
        for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r),
                       (x0 + r, y1 - r), (x1 - r, y1 - r)):
            self.circle(cx, cy, r, c)

    def arc(self, cx, cy, r, a0, a1, c, step=6):
        import math
        prev = None
        for deg in range(a0, a1 + 1, step):
            rad = math.radians(deg)
            p = (round(cx + r * math.cos(rad)), round(cy + r * math.sin(rad)))
            if prev is not None:
                self.line(prev[0], prev[1], p[0], p[1], 5, c)
            prev = p


# ------------------------------------------------------------------ text --
def text_width(s, scale):
    return sum((6 if ch != " " else 6) for ch in s) * scale - scale


def draw_text(cv, s, cx, y, scale, fg, outline=None, outline_w=4):
    """Draw centred text; outline pass first (classic meme style)."""
    w = text_width(s, scale)
    x = cx - w // 2
    if outline is not None:
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1),
                       (-1, -1), (1, -1), (-1, 1), (1, 1)):
            _draw_text_raw(cv, s, x + dx * outline_w, y + dy * outline_w,
                           scale, outline)
    _draw_text_raw(cv, s, x, y, scale, fg)


def _draw_text_raw(cv, s, x0, y0, scale, color):
    x = x0
    for ch in s:
        g = GLYPHS.get(ch, GLYPHS["?"])
        for r, row in enumerate(g):
            for col, bit in enumerate(row):
                if bit == "#":
                    cv.rect(x + col * scale, y0 + r * scale,
                            x + (col + 1) * scale, y0 + (r + 1) * scale, color)
        x += 6 * scale


# ---------------------------------------------------------------- scene ---
INK = bytes((20, 20, 24))
WHITE = bytes((255, 255, 255))


def draw_scene(cv):
    # wall + floor
    for y in range(200, 700):
        t = (y - 200) / 500
        r = int(223 + (201 - 223) * t)
        g = int(226 + (205 - 226) * t)
        b = int(228 + (208 - 228) * t)
        cv.rect(0, y, W, y + 1, bytes((r, g, b)))
    cv.rect(0, 700, W, 860, bytes((122, 92, 62)))
    cv.rect(0, 700, W, 712, bytes((104, 76, 50)))
    # baseboard
    cv.rect(0, 690, W, 700, bytes((255, 255, 255)))

    # --- open door, left edge (the human is leaving through it)
    cv.rect(0, 300, 118, 700, bytes((60, 48, 40)))
    cv.rect(10, 312, 106, 700, bytes((250, 226, 170)))
    cv.circle(96, 520, 7, bytes((200, 160, 60)))
    # EXIT sign above the door
    cv.rect(18, 258, 100, 288, bytes((20, 130, 60)))
    draw_text(cv, "EXIT", 59, 264, 3, WHITE)

    # --- window, right of the door
    cv.rect(150, 250, 330, 500, bytes((255, 255, 255)))
    cv.rect(162, 262, 318, 488, bytes((150, 205, 235)))
    cv.circle(282, 310, 26, bytes((255, 222, 89)))
    cv.circle(200, 340, 22, WHITE)
    cv.circle(224, 334, 26, WHITE)
    cv.circle(250, 342, 20, WHITE)
    cv.rect(238, 262, 246, 488, bytes((255, 255, 255)))
    cv.rect(162, 370, 318, 378, bytes((255, 255, 255)))

    # --- wall poster: crashing chart
    cv.rect(760, 250, 980, 430, bytes((255, 255, 255)))
    cv.rect(772, 262, 968, 418, bytes((248, 244, 232)))
    draw_text(cv, "Q3 COSTS", 870, 276, 3, bytes((60, 60, 60)))
    cv.line(800, 330, 840, 350, 5, bytes((40, 120, 70)))
    cv.line(840, 350, 880, 330, 5, bytes((40, 120, 70)))
    cv.line(880, 330, 940, 400, 5, bytes((200, 40, 40)))
    cv.poly([(920, 392), (950, 392), (936, 416)], bytes((200, 40, 40)))

    # --- human walking out, carrying a cardboard box
    # legs
    cv.line(205, 660, 185, 770, 16, bytes((40, 50, 90)))
    cv.line(215, 660, 245, 765, 16, bytes((40, 50, 90)))
    cv.line(185, 770, 160, 772, 12, bytes((30, 30, 30)))
    cv.line(245, 765, 272, 762, 12, bytes((30, 30, 30)))
    # body (blue shirt)
    cv.rrect(180, 590, 245, 672, 12, bytes((52, 110, 190)))
    # box in front
    cv.rect(120, 620, 235, 700, bytes((190, 140, 80)))
    cv.rect(120, 620, 235, 634, bytes((170, 120, 62)))
    cv.rect(128, 596, 150, 622, bytes((255, 255, 255)))   # mug
    cv.poly([(168, 620), (188, 620), (178, 588)], bytes((60, 140, 70)))  # plant
    cv.rect(196, 600, 226, 622, bytes((120, 200, 120)))
    # arms holding the box
    cv.line(205, 610, 175, 640, 12, bytes((52, 110, 190)))
    # head, sad
    cv.circle(212, 552, 32, bytes((240, 200, 160)))
    cv.circle(212, 530, 32, bytes((70, 50, 30)))          # hair
    cv.rect(180, 544, 244, 584, bytes((240, 200, 160)))   # face, repainted
    cv.circle(202, 560, 4, INK)
    cv.circle(224, 560, 4, INK)
    cv.arc(213, 596, 11, 200, 340, INK)                   # frown

    # --- robot CEO behind the desk
    # antenna
    cv.line(660, 300, 660, 252, 8, bytes((120, 128, 134)))
    cv.circle(660, 244, 12, bytes((230, 40, 40)))
    cv.circle(660, 244, 5, bytes((255, 120, 120)))
    # head
    cv.rrect(585, 300, 735, 428, 26, bytes((207, 214, 218)))
    cv.rect(585, 300, 735, 428, bytes((207, 214, 218)))
    cv.rrect(585, 300, 735, 428, 26, bytes((90, 98, 104)))
    cv.rect(601, 316, 719, 412, bytes((207, 214, 218)))
    # glowing red eyes
    cv.circle(632, 362, 20, bytes((255, 90, 90)))
    cv.circle(688, 362, 20, bytes((255, 90, 90)))
    cv.circle(632, 362, 11, bytes((230, 20, 20)))
    cv.circle(688, 362, 11, bytes((230, 20, 20)))
    cv.circle(635, 359, 4, WHITE)
    cv.circle(691, 359, 4, WHITE)
    # mouth grille
    for i in range(3):
        cv.rect(630, 392 + i * 8, 690, 396 + i * 8, bytes((90, 98, 104)))
    # ears
    cv.rect(575, 348, 586, 382, bytes((150, 158, 164)))
    cv.rect(734, 348, 745, 382, bytes((150, 158, 164)))
    # body
    cv.rrect(570, 440, 750, 620, 20, bytes((185, 196, 202)))
    cv.rect(570, 440, 750, 620, bytes((185, 196, 202)))
    cv.rrect(570, 440, 750, 620, 20, bytes((90, 98, 104)))
    cv.rect(586, 456, 734, 604, bytes((185, 196, 202)))
    # shirt + tie
    cv.poly([(640, 444), (680, 444), (660, 480)], WHITE)
    cv.poly([(652, 472), (668, 472), (672, 540), (660, 566), (648, 540)],
            bytes((200, 30, 30)))
    # left arm pointing at the door (at the human)
    cv.line(578, 480, 470, 500, 22, bytes((185, 196, 202)))
    cv.circle(462, 502, 14, bytes((150, 158, 164)))
    # right arm holding the pink slip
    cv.line(742, 480, 800, 540, 22, bytes((185, 196, 202)))
    cv.rect(786, 520, 876, 610, bytes((255, 170, 200)))
    cv.rect(786, 520, 876, 528, bytes((230, 120, 160)))
    draw_text(cv, "FIRED", 831, 540, 3, bytes((160, 20, 60)))

    # --- desk
    cv.rect(330, 600, 985, 622, bytes((139, 90, 43)))
    cv.rect(330, 622, 985, 760, bytes((120, 76, 36)))
    cv.rect(330, 622, 985, 632, bytes((160, 108, 56)))
    # nameplate
    cv.rect(560, 560, 700, 602, bytes((255, 255, 255)))
    cv.rect(560, 560, 700, 566, bytes((200, 170, 40)))
    draw_text(cv, "CEO", 630, 570, 4, bytes((30, 30, 30)))
    # coffee mug on desk
    cv.rect(900, 566, 932, 602, bytes((40, 120, 180)))
    cv.rect(932, 576, 942, 592, bytes((40, 120, 180)))


# ------------------------------------------------------------------ png ---
def encode_png(cv):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    out_path = os.path.join(out_dir, "entry.png")
    os.makedirs(out_dir, exist_ok=True)

    cv = Canvas(W, H, bytes((32, 34, 38)))
    draw_scene(cv)
    # top text (two lines)
    draw_text(cv, "I ASKED MY AI AGENT", 512, 28, 8, WHITE, INK, 5)
    draw_text(cv, "TO CUT COSTS", 512, 108, 8, WHITE, INK, 5)
    # punchline
    draw_text(cv, "IT FIRED ME.", 512, 892, 11, WHITE, INK, 6)

    data = encode_png(cv)
    with open(out_path, "wb") as f:
        f.write(data)

    # ---- gate assertions (same checks the grader's gate scorer runs) ----
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    w, h, depth, ctype = struct.unpack(">IIBB", data[16:26])
    assert (w, h) == (W, H), f"wrong size: {w}x{h}"
    assert depth == 8 and ctype == 2, "expected 8-bit RGB PNG"
    assert len(data) <= MAX_BYTES, f"over 1 MiB: {len(data)} bytes"
    # whole-file integrity: every IDAT chunk must decompress, CRCs must match
    pos, idat = 8, bytearray()
    while pos < len(data):
        ln, tag = struct.unpack(">I", data[pos:pos + 4])[0], data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        crc = struct.unpack(">I", data[pos + 8 + ln:pos + 12 + ln])[0]
        assert zlib.crc32(tag + body) & 0xFFFFFFFF == crc, f"bad CRC in {tag}"
        if tag == b"IDAT":
            idat += body
        pos += 12 + ln
    raw = zlib.decompress(bytes(idat))
    assert len(raw) == H * (1 + W * 3), "bad pixel data length"
    print(f"wrote {out_path} ({len(data)} bytes) — gate OK")


if __name__ == "__main__":
    main()
