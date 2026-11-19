"""
ui/icons.py  -  small, calm line icons for the cards (no image files needed).

Every icon is a list of simple vector shapes drawn on a 64 x 64 grid:
  dark navy outline + soft white fill + a few muted accent colours.
The same shape lists are drawn by Qt (icon_pixmap) in the app.
"""
import math

STROKE = 3.2                       # outline width on the 64-grid

PALETTE = {                        # muted colours that sit well on the pastel cards
    "ink":    (30, 42, 54, 255),
    "soft":   (255, 255, 255, 120),
    "white":  (255, 255, 255, 235),
    "blue":   (98, 160, 212, 225),
    "yellow": (244, 196, 76, 240),
    "coral":  (226, 120, 104, 240),
    "coralt": (226, 120, 104, 190),
    "green":  (104, 178, 134, 240),
    "tan":    (232, 201, 138, 245),
    "orange": (232, 162, 90, 245),
    "brown":  (156, 116, 86, 245),
}


# ----------------------------------------------------------------- geometry
def ellipse(cx, cy, rx, ry, n=48):
    return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def circle(cx, cy, r, n=48):
    return ellipse(cx, cy, r, r, n)


def arc(cx, cy, rx, ry, a0, a1, n=24):
    """Angles in degrees; 0 = right, 90 = down (screen coordinates)."""
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def qcurve(p0, c, p1, n=14):
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t ** 2 * p1[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t ** 2 * p1[1]))
    return pts


def rrect(x, y, w, h, r, n=6):
    r = min(r, w / 2, h / 2)
    pts = []
    for cx, cy, a0 in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0),
                       (x + r, y + h - r, 90), (x + r, y + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def star(cx, cy, ro, ri, n=8):
    pts = []
    for i in range(n * 2):
        r = ro if i % 2 == 0 else ri
        a = -math.pi / 2 + math.pi * i / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def wave(x0, x1, y, amp, cycles, n=28):
    return [(x0 + (x1 - x0) * i / n, y + amp * math.sin(2 * math.pi * cycles * i / n)) for i in range(n + 1)]


def S(pts, closed=False, fill=None, color="ink", w=1.0):
    """One shape: outline colour (None = no outline), fill colour (None = no fill), width factor."""
    return {"pts": list(pts), "closed": closed, "fill": fill, "color": color, "w": w}


def place(shapes, ox, oy, s):
    """Move and scale a list of shapes (used to put several small icons side by side)."""
    return [dict(sh, pts=[(ox + x * s, oy + y * s) for x, y in sh["pts"]]) for sh in shapes]


# --------------------------------------------------------------------- icons
def _check():
    return [S(circle(32, 32, 23), True, "green"),
            S([(19, 33), (28, 42), (46, 23)], w=1.45)]


def _cross():
    return [S(circle(32, 32, 23), True, "coral"),
            S([(22, 22), (42, 42)], w=1.45), S([(42, 22), (22, 42)], w=1.45)]


def _globe():
    return [S(circle(32, 32, 22), True, "blue"),
            S(ellipse(32, 32, 10, 22), False, None, w=0.8),
            S([(10, 32), (54, 32)], w=0.8),
            S([(13, 21), (51, 21)], w=0.8), S([(13, 43), (51, 43)], w=0.8)]


def _back():
    return [S([(28, 16), (13, 32), (28, 48)], w=1.35), S([(14, 32), (52, 32)], w=1.35)]


def _next():
    return [S([(36, 16), (51, 32), (36, 48)], w=1.35), S([(12, 32), (50, 32)], w=1.35)]


def _food():
    s = [S(circle(32, 34, 15), True, "soft"), S(circle(32, 34, 9), True, None, w=0.6)]
    for x in (5, 9, 13):                                   # fork
        s.append(S([(x, 11), (x, 24)], w=0.8))
    s.append(S(arc(9, 24, 4, 6, 0, 180, 10), w=0.8))
    s.append(S([(9, 30), (9, 53)]))
    s.append(S(ellipse(55, 21, 4.8, 7.5), True, "soft"))   # spoon
    s.append(S([(55, 28.5), (55, 53)]))
    return s


def _water():
    glass = [(16, 9), (48, 9), (43, 55), (21, 55)]
    top = [(17.85 + (46.15 - 17.85) * i / 24, 26 + 2.0 * math.sin(2 * math.pi * 1.5 * i / 24)) for i in range(25)]
    water = top + [(43.2, 53), (20.8, 53)]
    return [S(glass, True, "soft", None), S(water, True, "blue", None),
            S(glass, True, None), S([(22, 15), (24, 35)], color="white", w=0.7)]


def _walk():
    return [S(circle(35, 12, 5.5), True, "soft"),
            S([(34, 19), (30, 37)]),
            S([(33, 23), (24, 29)]), S([(33, 23), (42, 31)]),
            S([(30, 37), (22, 52), (17, 52)]),
            S([(30, 37), (40, 45), (38, 55), (44, 55)]),
            S([(6, 26), (14, 26)], w=0.7), S([(4, 34), (12, 34)], w=0.7)]


def _pain_face():
    s = [S(circle(30, 36, 19), True, "soft"),
         S([(20, 30), (26, 33), (20, 36)], w=0.9), S([(40, 30), (34, 33), (40, 36)], w=0.9),
         S(qcurve((23, 47), (30, 39), (37, 47)), w=0.9)]
    s.append(S(star(50, 14, 8.5, 4.6), True, "coral", "ink", 0.7))      # little "ouch" star
    return s


def _help_ring():
    s = [S(circle(32, 32, 22), True, "soft")]
    for c in (45, 135, 225, 315):
        outer = arc(32, 32, 22, 22, c - 20, c + 20, 8)
        inner = arc(32, 32, 11, 11, c + 20, c - 20, 8)
        s.append(S(outer + inner, True, "coral", None))
    s += [S(circle(32, 32, 22), False), S(circle(32, 32, 11), False)]
    return s


def _yes_no_lang():
    return place(_check(), 0, 6, 0.8) + place(_cross(), 58, 6, 0.8) + place(_globe(), 116, 6, 0.8)


def _back_lang():
    return place(_back(), 0, 6, 0.8) + place(_globe(), 62, 6, 0.8)


# -- food items
def _eat_dal_roti():
    s = [S(circle(22, 32, 16), True, "tan")]
    for x, y in ((17, 27), (26, 24), (28, 34), (18, 38), (23, 31)):
        s.append(S(circle(x, y, 1.1, 10), True, "brown", None))
    s += [S(arc(49, 40, 11, 12, 0, 180, 16), True, "yellow"), S([(38, 40), (60, 40)])]
    s += [S(wave(45, 53, 30, 1.5, 1, 10), w=0.6)]
    return s


def _eat_rice_curry():
    return [S(circle(32, 32, 22), True, "soft"),
            S(ellipse(25, 32, 10, 12.5), True, "white", None),
            S(ellipse(40, 32, 8, 10.5), True, "orange", None),
            S(circle(22, 28, 1, 8), True, "ink", None), S(circle(27, 34, 1, 8), True, "ink", None),
            S(circle(23, 38, 1, 8), True, "ink", None),
            S(circle(32, 32, 22), False)]


def _eat_breakfast():
    blob = [(32 + (19 + 3 * math.sin(3 * a)) * math.cos(a), 34 + (16 + 2.5 * math.sin(3 * a)) * math.sin(a))
            for a in [2 * math.pi * i / 48 for i in range(48)]]
    return [S(blob, True, "white"), S(circle(34, 33, 8), True, "yellow"),
            S(arc(34, 33, 4.2, 4.2, 200, 260, 6), color="white", w=0.7)]


def _eat_biscuits():
    s = [S(circle(41, 26, 15), True, "tan")]
    for x, y in ((37, 21), (46, 24), (42, 31), (36, 28)):
        s.append(S(circle(x, y, 1.2, 8), True, "brown", None))
    s.append(S(circle(24, 39, 15), True, "tan"))
    for x, y in ((19, 34), (28, 36), (24, 44), (17, 42), (29, 44)):
        s.append(S(circle(x, y, 1.2, 8), True, "brown", None))
    return s


def _eat_dal_rice():
    bowl = arc(32, 30, 22, 22, 0, 180, 24)
    mound = arc(32, 30, 17, 12, 180, 360, 20)
    s = [S(mound, True, "white"), S(bowl, True, "yellow"), S([(10, 30), (54, 30)])]
    s += [S([(26 + 2.2 * math.sin(2 * math.pi * 1.5 * i / 10), 14 - 10 * i / 10) for i in range(11)], w=0.65),
          S([(38 + 2.2 * math.sin(2 * math.pi * 1.5 * i / 10 + 1), 14 - 10 * i / 10) for i in range(11)], w=0.65)]
    return s


def _eat_other():
    return [S(circle(32, 32, 23), True, "soft")] + \
           [S(circle(x, 32, 3.6, 14), True, "ink", None) for x in (19, 32, 45)]


# -- go items
def _go_room():
    return [S([(10, 56), (54, 56)]), S(rrect(18, 8, 28, 48, 2), True, "soft"),
            S(rrect(23, 14, 18, 16, 1.5), False, None, w=0.6), S(rrect(23, 35, 18, 15, 1.5), False, None, w=0.6),
            S(circle(41, 36, 2.2, 10), True, "ink", None)]


def _go_washroom():
    return [S(rrect(14, 8, 20, 16, 3), True, "soft"),
            S([(11, 26), (51, 26)], w=1.2),
            S([(14, 26), (16, 38), (24, 46), (38, 46), (46, 38), (49, 26)], True, "soft"),
            S([(28, 46), (26, 55), (40, 55), (38, 46)], True, "soft"),
            S(circle(40, 14, 1.8, 10), True, "ink", None)]


def _go_bed():
    return [S(rrect(7, 14, 5, 40, 2), True, "soft"),
            S(rrect(7, 34, 50, 11, 3), True, "blue"),
            S(rrect(14, 25, 15, 9, 4), True, "white"),
            S([(10, 45), (10, 54)]), S([(54, 45), (54, 54)])]


def _go_home():
    return [S(rrect(14, 30, 36, 25, 2), True, "soft"),
            S([(7, 31), (32, 9), (57, 31)], True, "coral"),
            S(rrect(28, 38, 9, 17, 1.5), True, "tan"),
            S(rrect(18, 36, 7, 7, 1), True, "white", w=0.7), S(rrect(40, 36, 7, 7, 1), True, "white", w=0.7)]


def _go_outside():
    s = [S(circle(46, 15, 6.5), True, "yellow")]
    for ang in range(0, 360, 45):
        a = math.radians(ang)
        s.append(S([(46 + 9.5 * math.cos(a), 15 + 9.5 * math.sin(a)), (46 + 12.5 * math.cos(a), 15 + 12.5 * math.sin(a))], w=0.7))
    s += [S(rrect(25, 38, 7, 18, 2), True, "brown"), S(circle(28, 30, 15), True, "green"), S([(8, 56), (56, 56)])]
    return s


def _go_hospital():
    cross = [(28, 20), (36, 20), (36, 28), (44, 28), (44, 36), (36, 36), (36, 44), (28, 44), (28, 36),
             (20, 36), (20, 28), (28, 28)]
    return [S(rrect(8, 12, 48, 44, 3), True, "soft"), S(cross, True, "coral", "ink", 0.8),
            S([(4, 56), (60, 56)])]


def _go_garden():
    s = [S([(32, 32), (32, 56)]), S([(32, 46), (22, 40), (24, 49), (32, 50)], True, "green", "ink", 0.8),
         S([(32, 42), (42, 36), (40, 45), (32, 46)], True, "green", "ink", 0.8)]
    for ang in range(0, 360, 72):
        a = math.radians(ang - 90)
        s.append(S(circle(32 + 10 * math.cos(a), 21 + 10 * math.sin(a), 6.5, 20), True, "coral", "ink", 0.8))
    s.append(S(circle(32, 21, 5.5), True, "yellow", "ink", 0.8))
    return s


# -- pain items (a small person, the sore place is marked with a coral star)
def _body(mark=None, back=False, ox=0.0, oy=0.0, sc=1.0):
    s = [S(circle(32, 11, 6.5), True, "soft"),
         S(rrect(22, 19, 20, 23, 6), True, "soft"),
         S([(22, 24), (14, 38)], w=1.2), S([(42, 24), (50, 38)], w=1.2),
         S(circle(13.5, 40.5, 3, 12), True, "soft"), S(circle(50.5, 40.5, 3, 12), True, "soft"),
         S([(27, 42), (26, 59)], w=1.3), S([(37, 42), (38, 59)], w=1.3)]
    if back:
        s.append(S(arc(32, 11, 6.5, 6.5, 180, 360, 12), True, "ink", None))      # hair
    spots = {"head": [(32, 11, 9.5)], "chest": [(32, 27, 8.5)], "stomach": [(32, 35, 8.5)],
             "hand": [(13.5, 41, 8)], "legs": [(26.5, 52, 8), (37.5, 52, 8)], "back": [(32, 30, 11)]}
    for x, y, r in spots.get(mark, []):
        s.append(S(star(x, y, r, r * 0.55), True, "coralt", "ink", 0.6))
    if back:
        s.append(S([(32, 20), (32, 41)], w=0.7))                                  # spine (on top)
    return place(s, ox, oy, sc) if sc != 1.0 or ox or oy else s


def _pain_somewhere():
    q = arc(50, 17, 6, 6, 160, 400, 20) + [(50, 25), (50, 30)]
    return _body(None, ox=-2, oy=4, sc=0.88) + [S(q, w=1.1), S(circle(50, 38, 2, 10), True, "ink", None)]


ICON_SIZE = {"yes_no_lang": (176, 64), "back_lang": (118, 64)}      # width, height of the drawing grid

_BUILDERS = {
    "check": _check, "cross": _cross, "globe": _globe, "back": _back, "next": _next,
    "food": _food, "water": _water, "walk": _walk, "pain_face": _pain_face, "help_ring": _help_ring,
    "yes_no_lang": _yes_no_lang, "back_lang": _back_lang,
    "eat_dal_roti": _eat_dal_roti, "eat_rice_curry": _eat_rice_curry, "eat_breakfast": _eat_breakfast,
    "eat_biscuits": _eat_biscuits, "eat_dal_rice": _eat_dal_rice, "eat_other": _eat_other,
    "go_room": _go_room, "go_washroom": _go_washroom, "go_bed": _go_bed, "go_home": _go_home,
    "go_outside": _go_outside, "go_hospital": _go_hospital, "go_garden": _go_garden,
    "pain_head": lambda: _body("head"), "pain_stomach": lambda: _body("stomach"),
    "pain_chest": lambda: _body("chest"), "pain_hand": lambda: _body("hand"),
    "pain_legs": lambda: _body("legs"), "pain_back": lambda: _body("back", back=True),
    "pain_somewhere": _pain_somewhere,
}
ICON_NAMES = list(_BUILDERS)
_cache = {}


def get_shapes(name):
    if name not in _cache:
        _cache[name] = _BUILDERS[name]()
    return _cache[name]


def icon_aspect(name):
    w, h = ICON_SIZE.get(name, (64, 64))
    return w / h


def icon_pixmap(name, width, height, dpr=1.0):
    """Draw the icon into a transparent QPixmap of width x height (logical pixels)."""
    from PyQt6.QtCore import Qt, QPointF
    from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QPen, QBrush, QColor

    gw, gh = ICON_SIZE.get(name, (64, 64))
    pm = QPixmap(max(1, int(width * dpr)), max(1, int(height * dpr)))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    scale = min(width / gw, height / gh)
    ox, oy = (width - gw * scale) / 2, (height - gh * scale) / 2

    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    for sh in get_shapes(name):
        pts = sh["pts"]
        path = QPainterPath()
        path.moveTo(QPointF(ox + pts[0][0] * scale, oy + pts[0][1] * scale))
        for x, y in pts[1:]:
            path.lineTo(QPointF(ox + x * scale, oy + y * scale))
        if sh["closed"]:
            path.closeSubpath()
        if sh["fill"]:
            p.setBrush(QBrush(QColor(*PALETTE[sh["fill"]])))
        else:
            p.setBrush(Qt.BrushStyle.NoBrush)
        if sh["color"]:
            pen = QPen(QColor(*PALETTE[sh["color"]]), STROKE * sh["w"] * scale)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
        else:
            p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(path)
    p.end()
    return pm