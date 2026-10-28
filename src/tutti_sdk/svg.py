"""Dependency-free SVG→PNG rasterizer, just capable enough for the login captcha
(``<path>`` elements with M/L/H/V/C/Q/Z commands, fills and strokes). Everything
renders black-on-white; the output is an 8-bit grayscale PNG."""

import itertools
import math
import re
import struct
import zlib

_CURVE_STEPS = 18
_INK = 0  # black
_PAPER = 255  # white

Point = tuple[float, float]
SubPath = tuple[list[Point], bool]  # (points, closed)


def _flatten_path(d: str) -> list[SubPath]:
    tokens = re.findall(r"[a-zA-Z]|-?\d*\.?\d+(?:[eE][+-]?\d+)?", d)
    subs: list[SubPath] = []
    cur: list[Point] | None = None
    cmd = ""
    cx = cy = sx = sy = 0.0
    i = 0

    def num() -> float:
        nonlocal i
        v = float(tokens[i])
        i += 1
        return v

    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
        rel = cmd.islower()
        c = cmd.upper()

        if c == "Z":
            if cur is not None:
                cur.append((sx, sy))
                subs.append((cur, True))
                cur = None
            cx, cy = sx, sy
            continue
        if c == "M":
            x, y = num(), num()
            if rel:
                x, y = x + cx, y + cy
            if cur:
                subs.append((cur, False))
            cur = [(x, y)]
            cx = sx = x
            cy = sy = y
            cmd = "l" if rel else "L"  # subsequent coords are implicit line-tos
            continue
        if cur is None:
            cur = [(cx, cy)]
        if c == "L":
            x, y = num(), num()
            if rel:
                x, y = x + cx, y + cy
            cur.append((x, y))
            cx, cy = x, y
        elif c == "H":
            x = num() + (cx if rel else 0)
            cur.append((x, cy))
            cx = x
        elif c == "V":
            y = num() + (cy if rel else 0)
            cur.append((cx, y))
            cy = y
        elif c == "C":
            x1, y1, x2, y2, x, y = (num() for _ in range(6))
            if rel:
                x1, y1, x2, y2, x, y = x1 + cx, y1 + cy, x2 + cx, y2 + cy, x + cx, y + cy
            for s in range(1, _CURVE_STEPS + 1):
                t = s / _CURVE_STEPS
                u = 1 - t
                cur.append(
                    (
                        u**3 * cx + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t**3 * x,
                        u**3 * cy + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t**3 * y,
                    )
                )
            cx, cy = x, y
        elif c == "Q":
            x1, y1, x, y = (num() for _ in range(4))
            if rel:
                x1, y1, x, y = x1 + cx, y1 + cy, x + cx, y + cy
            for s in range(1, _CURVE_STEPS + 1):
                t = s / _CURVE_STEPS
                u = 1 - t
                cur.append(
                    (
                        u * u * cx + 2 * u * t * x1 + t * t * x,
                        u * u * cy + 2 * u * t * y1 + t * t * y,
                    )
                )
            cx, cy = x, y
        else:
            break
    if cur:
        subs.append((cur, False))
    return subs


class _Raster:
    def __init__(self, w: int, h: int) -> None:
        self.w = w
        self.h = h
        self.buf = bytearray([_PAPER]) * (w * h)

    def fill(self, subs: list[SubPath]) -> None:
        """Scanline fill with the non-zero winding rule."""
        edges: list[tuple[float, float, float, float]] = []
        for pts, _ in subs:
            for (ax, ay), (bx, by) in itertools.pairwise(pts):
                edges.append((ax, ay, bx, by))
            if pts and pts[-1] != pts[0]:
                edges.append((*pts[-1], *pts[0]))
        for y in range(self.h):
            yc = y + 0.5
            xs: list[tuple[float, int]] = []
            for ax, ay, bx, by in edges:
                if (ay <= yc < by) or (by <= yc < ay):
                    xs.append((ax + (yc - ay) / (by - ay) * (bx - ax), 1 if by > ay else -1))
            xs.sort()
            wind = 0
            row = y * self.w
            for k in range(len(xs) - 1):
                wind += xs[k][1]
                if wind:
                    x0 = max(0, _round(xs[k][0]))
                    x1 = min(self.w, _round(xs[k + 1][0]))
                    if x1 > x0:
                        self.buf[row + x0 : row + x1] = bytes([_INK]) * (x1 - x0)

    def stroke(self, subs: list[SubPath], width: float) -> None:
        r = max(width / 2, 0.6)
        for pts, closed in subs:
            for a, b in itertools.pairwise(pts):
                self._segment(a, b, r)
            if closed and len(pts) > 1:
                self._segment(pts[-1], pts[0], r)

    def _segment(self, a: Point, b: Point, r: float) -> None:
        dx, dy = b[0] - a[0], b[1] - a[1]
        steps = max(1, math.ceil(math.hypot(dx, dy)))
        for s in range(steps + 1):
            t = s / steps
            self._disc(a[0] + dx * t, a[1] + dy * t, r)

    def _disc(self, cx: float, cy: float, r: float) -> None:
        r2 = r * r
        for y in range(max(0, math.floor(cy - r)), min(self.h - 1, math.ceil(cy + r)) + 1):
            ddy = (y + 0.5 - cy) ** 2
            if ddy > r2:
                continue
            # Pixels whose centre lies within the disc on this row.
            half = math.sqrt(r2 - ddy)
            x0 = max(0, math.ceil(cx - half - 0.5))
            x1 = min(self.w - 1, math.floor(cx + half - 0.5))
            if x1 >= x0:
                row = y * self.w
                self.buf[row + x0 : row + x1 + 1] = bytes([_INK]) * (x1 - x0 + 1)


def _round(x: float) -> int:
    # JS Math.round semantics (half rounds up), unlike Python's banker's rounding.
    return math.floor(x + 0.5)


def _downsample(src: _Raster, scale: int) -> tuple[int, int, bytearray]:
    w, h = src.w // scale, src.h // scale
    out = bytearray(w * h)
    n = scale * scale
    for y in range(h):
        rows = [
            src.buf[(y * scale + sy) * src.w : (y * scale + sy + 1) * src.w] for sy in range(scale)
        ]
        for x in range(w):
            total = sum(sum(row[x * scale : (x + 1) * scale]) for row in rows)
            out[y * w + x] = _round(total / n)
    return w, h, out


def _attrs(tag: str) -> dict[str, str]:
    return dict(re.findall(r'([\w-]+)\s*=\s*"([^"]*)"', tag))


def _paints(color: str | None) -> bool:
    # Missing fill defaults to black in SVG; only "none" disables painting.
    return color is None or color.strip().lower() != "none"


def render_svg_to_png(svg: str, scale: int = 3, supersample: int = 3) -> bytes:
    """Render a (captcha-style) SVG document to PNG bytes.

    ``scale`` is relative to the SVG viewBox (150×50 at 3 ⇒ 450×150);
    ``supersample`` is the anti-aliasing factor.
    """
    svg_tag = re.search(r"<svg\b[^>]*>", svg, re.IGNORECASE)
    sa = _attrs(svg_tag.group(0) if svg_tag else "")
    vw = vh = 0.0
    if "viewBox" in sa:
        parts = [float(p) for p in re.split(r"[ ,]+", sa["viewBox"].strip())]
        vw, vh = parts[2], parts[3]
    vw = vw or _float(sa.get("width")) or 150
    vh = vh or _float(sa.get("height")) or 50

    final_w, final_h = _round(vw * scale), _round(vh * scale)
    raster = _Raster(final_w * supersample, final_h * supersample)
    kx = final_w * supersample / vw
    ky = final_h * supersample / vh

    for tag in re.findall(r"<path\b[^>]*>", svg, re.IGNORECASE):
        a = _attrs(tag)
        if not a.get("d"):
            continue
        subs = [
            ([(x * kx, y * ky) for x, y in pts], closed) for pts, closed in _flatten_path(a["d"])
        ]
        if _paints(a.get("fill")):
            raster.fill(subs)
        if "stroke" in a and _paints(a["stroke"]):
            raster.stroke(subs, (_float(a.get("stroke-width")) or 1) * (kx + ky) / 2)

    w, h, gray = _downsample(raster, supersample)
    return _encode_png(w, h, gray)


def _float(s: str | None) -> float:
    if not s:
        return 0.0
    m = re.match(r"\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?", s)
    return float(m.group(0)) if m else 0.0


def _encode_png(w: int, h: int, gray: bytearray) -> bytes:
    raw = b"".join(b"\x00" + bytes(gray[y * w : (y + 1) * w]) for y in range(h))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)  # 8-bit grayscale
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
