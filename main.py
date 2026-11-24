#!/usr/bin/env python3
"""The Daily Sum - a deterministic one-page newspaper front page renderer.

Renders the 24 November 2026 front page as a 1024x1024 PNG using only the
Python standard library: a hand-built 5x7 bitmap font, a tiny software
rasteriser and a hand-rolled PNG encoder (zlib + struct). No randomness,
no clock, no network - two runs produce byte-identical output.
"""

import os
import struct
import zlib

W, H = 1024, 1024
MARGIN = 48
CONTENT_W = W - 2 * MARGIN
INK = (18, 18, 18)
PAPER = (250, 248, 240)  # warm newsprint
GREY = (90, 90, 90)

# ---------------------------------------------------------------------------
# 5x7 bitmap font. Each glyph is seven rows of five "1"/"0" cells.
# ---------------------------------------------------------------------------
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "a": ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    "b": ("10000", "10000", "10110", "11001", "10001", "10001", "11110"),
    "c": ("00000", "00000", "01110", "10001", "10000", "10001", "01110"),
    "d": ("00001", "00001", "01101", "10011", "10001", "10001", "01111"),
    "e": ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    "f": ("00110", "01001", "01000", "11110", "01000", "01000", "01000"),
    "g": ("00000", "01111", "10001", "10001", "01111", "00001", "01110"),
    "h": ("10000", "10000", "10110", "11001", "10001", "10001", "10001"),
    "i": ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    "j": ("00010", "00000", "00110", "00010", "00010", "10010", "01100"),
    "k": ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    "l": ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    "m": ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    "n": ("00000", "00000", "10110", "11001", "10001", "10001", "10001"),
    "o": ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    "p": ("00000", "00000", "10110", "11001", "10001", "11110", "10000"),
    "q": ("00000", "00000", "01101", "10011", "10001", "01111", "00001"),
    "r": ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    "s": ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    "t": ("01000", "01000", "11100", "01000", "01000", "01001", "00110"),
    "u": ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    "v": ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    "w": ("00000", "00000", "10001", "10101", "10101", "10101", "01010"),
    "x": ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    "y": ("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
    "z": ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "\u2014": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "\u00b7": ("00000", "00000", "01100", "01100", "00000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "+": ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    "=": ("00000", "00000", "01110", "00000", "01110", "00000", "00000"),
}

BLANK = ("00000", "00000", "00000", "00000", "00000", "00000", "00000")


def glyph_rows(ch):
    return FONT.get(ch, BLANK)


def text_width(text, scale):
    """Advance width of text at a given scale (6 units per glyph cell)."""
    if not text:
        return 0
    return len(text) * 6 * scale - scale


def wrap_text(text, scale, max_width):
    """Greedy word wrap; returns a list of lines that fit max_width."""
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        cur = ""
        for word in words:
            trial = word if not cur else cur + " " + word
            if text_width(trial, scale) <= max_width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
    return lines


# ---------------------------------------------------------------------------
# Tiny software rasteriser over an RGB bytearray.
# ---------------------------------------------------------------------------
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.buf = bytearray(w * h * 3)
        row = bytes(bg) * w
        for y in range(h):
            self.buf[y * w * 3:(y + 1) * w * 3] = row

    def rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.buf[i:i + (x1 - x0) * 3] = row

    def hline(self, x, y, w, color, thickness=1):
        self.rect(x, y, w, thickness, color)

    def draw_text(self, x, y, text, scale, color):
        cx = x
        for ch in text:
            rows = glyph_rows(ch)
            for r in range(7):
                bits = rows[r]
                for c in range(5):
                    if bits[c] == "1":
                        self.rect(cx + c * scale, y + r * scale,
                                  scale, scale, color)
            cx += 6 * scale
        return cx

    def draw_text_centered(self, cx, y, text, scale, color):
        x = cx - text_width(text, scale) // 2
        self.draw_text(x, y, text, scale, color)
        return x


# ---------------------------------------------------------------------------
# Hand-rolled PNG encoder (colour type 2, 8-bit, filter None per scanline).
# ---------------------------------------------------------------------------
def _chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return out


def write_png(canvas, path):
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)
        raw += canvas.buf[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)
    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", ihdr)
           + _chunk(b"IDAT", comp)
           + _chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


# ---------------------------------------------------------------------------
# Stories for Tuesday, 24 November 2026.
# ---------------------------------------------------------------------------
LEAD = (
    "NATO VOWS SPACE DEFENSE",
    "Alliance answers reports of a Russian nuclear-armed satellite",
)

STORIES = [
    ("ZELENSKY URGES FOUR-PARTY TALKS",
     "Kyiv seeks a meeting with Russia, the US and Europe as soon as possible"),
    ("US BLACKLISTS MEGASPEED IN NVIDIA SPY CASE",
     "Singapore firm joins the Entity List over alleged chip espionage"),
    ("UN COURT RULES MYANMAR COMMITTED GENOCIDE",
     "World court judgment on the Rohingya atrocities"),
    ("CAR BOMB LEVELS BUILDINGS IN COLOMBIA",
     "Blast destroys buildings in Villavicencio"),
    ("SPACEX AND TESLA IN $3.5 TRILLION MERGER TALKS",
     "Five directors hash out details of a record tie-up"),
    ("DOZENS MISSING AS BOAT CAPSIZES OFF SENEGAL",
     "Migrant vessel overturns in the Atlantic"),
]

MASTHEAD = "THE DAILY SUM"
DATELINE = "Tuesday, 24 November 2026 \u00b7 The World in One Image"
FOOTER = ("Rendered by The Daily Sum \u00b7 "
          "Sources: world wires, 24 Nov 2026")


def draw_story(canvas, x, y, width, number, headline, summary):
    """Draw one numbered story block; returns the y just below it."""
    lines = wrap_text(str(number) + ". " + headline, 3, width)
    for line in lines:
        canvas.draw_text(x, y, line, 3, INK)
        y += 7 * 3 + 6
    y += 2
    for line in wrap_text(summary, 2, width):
        canvas.draw_text(x, y, line, 2, INK)
        y += 7 * 2 + 5
    return y


def build():
    canvas = Canvas(W, H, PAPER)

    # Thin frame around the whole page.
    canvas.hline(20, 20, W - 40, INK, 2)
    canvas.hline(20, H - 22, W - 40, INK, 2)
    canvas.rect(20, 20, 2, H - 40, INK)
    canvas.rect(W - 22, 20, 2, H - 40, INK)

    # Masthead, flanked by the issue number and the price.
    canvas.draw_text(MARGIN, 62, "No. 328", 2, GREY)
    price = "PRICE: FREE"
    canvas.draw_text(W - MARGIN - text_width(price, 2), 62, price, 2, GREY)
    canvas.draw_text_centered(W // 2, 40, MASTHEAD, 7, INK)
    canvas.hline(MARGIN, 116, CONTENT_W, INK, 4)
    canvas.hline(MARGIN, 124, CONTENT_W, INK, 1)

    # Dateline.
    canvas.draw_text_centered(W // 2, 142, DATELINE, 2, INK)
    canvas.hline(MARGIN, 168, CONTENT_W, INK, 1)

    # Lead story, full width.
    y = 196
    canvas.draw_text(MARGIN, y, "LEAD STORY", 2, GREY)
    y += 7 * 2 + 10
    lead_lines = wrap_text(LEAD[0], 4, CONTENT_W)
    for line in lead_lines:
        canvas.draw_text(MARGIN, y, line, 4, INK)
        y += 7 * 4 + 8
    y += 4
    for line in wrap_text(LEAD[1], 2, CONTENT_W):
        canvas.draw_text(MARGIN, y, line, 2, INK)
        y += 7 * 2 + 5
    y += 18
    canvas.hline(MARGIN, y, CONTENT_W, INK, 2)
    y += 20
    canvas.draw_text(MARGIN, y, "TOP STORIES", 2, GREY)
    y += 7 * 2 + 12

    # Remaining stories in two columns, three per column.
    col_w = (CONTENT_W - 32) // 2
    col_x = [MARGIN, MARGIN + col_w + 32]
    # Vertical divider between the columns, spanning the story grid.
    canvas.rect(W // 2 - 1, y, 2, 968 - 24 - y, GREY)
    for col in range(2):
        cy = y
        for i, story in enumerate(STORIES[col * 3:(col + 1) * 3]):
            cy = draw_story(canvas, col_x[col], cy, col_w,
                            col * 3 + i + 2, story[0], story[1])
            cy += 26

    # Footer.
    canvas.hline(MARGIN, 968, CONTENT_W, INK, 1)
    canvas.draw_text_centered(W // 2, 982, FOOTER, 2, GREY)

    return canvas


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if not out_dir:
        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "output")
    os.makedirs(out_dir, exist_ok=True)
    canvas = build()
    write_png(canvas, os.path.join(out_dir, "entry.png"))


if __name__ == "__main__":
    main()
