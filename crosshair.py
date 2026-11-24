"""Reticle - lightweight crosshair overlay that runs from the Windows system tray
Coded by FlxR  -  Discord: fs.d  (see LICENSE.txt)
Install:  pip install pystray pillow
Run:      pythonw crosshair.py
Hotkeys:  F8 show/hide  |  F9 / F10 switch presets  |  Ctrl+Alt+Arrows nudge (all rebindable: Settings > Hotkeys)
"""
import atexit, hashlib, subprocess, urllib.request, webbrowser, struct, time, base64, math, ctypes, ctypes.wintypes as wt, io, json, os, queue, re, sys, threading, winreg, zlib
import tkinter as tk
from tkinter import filedialog
import pystray
from pystray import Menu as M, MenuItem as I
from PIL import Image, ImageChops, ImageDraw, ImageStat, ImageTk
try:
    from PIL import ImageGrab  # reads the background color around the crosshair (adaptive color)
except Exception:
    ImageGrab = None
try:
    import cv2  # optional: needed for mp4/webm. GIF works without it
except Exception:
    cv2 = None

K32 = ctypes.WinDLL("kernel32", use_last_error=True)
U32 = ctypes.windll.user32
K32.CreateMutexW(None, False, "CrosshairTrayApp")
if ctypes.get_last_error() == 183:  # another instance is already running
    sys.exit(0)
U32.GetForegroundWindow.restype = ctypes.c_void_p
U32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(wt.DWORD)]
K32.OpenProcess.restype = ctypes.c_void_p
K32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
K32.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
K32.CloseHandle.argtypes = [ctypes.c_void_p]
U32.GetParent.restype = ctypes.c_void_p
U32.GetParent.argtypes = [ctypes.c_void_p]
U32.GetWindowLongW.restype = ctypes.c_long
U32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
U32.SetWindowLongW.restype = ctypes.c_long
U32.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
try:  # dark tray menus
    ctypes.windll.uxtheme[135](2)
    ctypes.windll.uxtheme[136]()
except Exception:
    pass

VERSION = "30"   # raise this on every release (numbers and dots only: 31, 32 ... or 30.1)
GITHUB_REPO = "FlxR0000/Reticle"   # "owner/repo" whose latest Release is checked for updates ("" = updates off)
BASE = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "Crosshair")
PRE = os.path.join(BASE, "presets")
os.makedirs(PRE, exist_ok=True)
CFG = os.path.join(BASE, "crosshair.json")
import logging
logging.basicConfig(filename=os.path.join(BASE, "crosshair.log"), level=logging.WARNING,
                    format="%(asctime)s %(message)s")
sys.excepthook = lambda *a: logging.error("crash", exc_info=a)
OWN = os.path.basename(sys.executable).lower()

BG, PANEL, BTN, FG, ACC, MUTE = "#0f0a0b", "#171011", "#271a1c", "#e4d9d9", "#a8202c", "#85767a"
ACC_HI, EDGE = "#c22a38", "#3a2428"   # hover red / subtle borders
KEY = "#010101"
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
CELLK = re.compile(r"^\d{1,2},\d{1,2}$")
RS = getattr(Image, "Resampling", Image).LANCZOS
ARMS = {"cross": [(1, 0), (-1, 0), (0, 1), (0, -1)],
        "tcross": [(1, 0), (-1, 0), (0, 1)],
        "x": [(.7071, .7071), (-.7071, .7071), (.7071, -.7071), (-.7071, -.7071)]}
ARMS["ringx"] = ARMS["cross"]
POLY = {"square": [(-1, -1), (1, -1), (1, 1), (-1, 1)],
        "diamond": [(0, -1), (1, 0), (0, 1), (-1, 0)],
        "triangle": [(0, -1), (.866, .5), (-.866, .5)]}
SHAPES = [("Cross", "cross"), ("T cross", "tcross"), ("X", "x"), ("Cross + circle", "ringx"),
          ("Circle", "circle"), ("Square", "square"), ("Diamond", "diamond"), ("Triangle", "triangle"),
          ("Chevron ^", "chevron"), ("Dot", "dot")]
COLORS = [("Green", "#00ff6a"), ("Red", "#ff2d2d"), ("Cyan", "#00e5ff"),
          ("Yellow", "#ffe600"), ("White", "#ffffff"), ("Pink", "#ff3df2")]
MENU_COLORS = COLORS + [("Orange", "#ff8a00"), ("Purple", "#7c4dff"), ("Blue", "#2d6bff"),
                        ("Black", "#000000")]
PK = ["shape", "color", "outline_color", "length", "thick", "gap", "dot", "dot_size", "outline",
      "opacity", "cells", "grid_n", "cell", "show_shape", "paint_color", "img", "img_size", "ix", "iy",
      "rot", "dot_color", "img_op", "img_rot",
      "img2", "img2_size", "i2x", "i2y", "img2_op", "img2_rot",
      "img_fh", "img_fv", "img2_fh", "img2_fv", "img_tint", "img2_tint",
      "vid", "vid_size", "vx", "vy", "vid_op", "vid_black"]
RNG = {"length": (1, 60), "thick": (1, 20), "gap": (0, 60), "dot_size": (1, 20), "outline": (0, 6),
       "cell": (1, 12), "grid_n": (9, 41), "img_size": (8, 512), "ix": (-3000, 3000), "iy": (-3000, 3000),
       "rot": (0, 359), "img_op": (10, 100), "img_rot": (0, 359),
       "img2_size": (8, 512), "i2x": (-3000, 3000), "i2y": (-3000, 3000), "img2_op": (10, 100), "img2_rot": (0, 359),
       "img_fh": (0, 1), "img_fv": (0, 1), "img2_fh": (0, 1), "img2_fv": (0, 1),
       "vid_size": (16, 1024), "vx": (-3000, 3000), "vy": (-3000, 3000), "vid_op": (10, 100)}
DEF = dict(shape="cross", color="#00ff6a", outline_color="#000000", length=10, thick=2, gap=4,
           dot=True, dot_size=2, outline=1, opacity=1.0, cells={}, grid_n=21, cell=4,
           paint_color="#ff2d55", show_shape=True, img="", img_size=48, ix=0, iy=0,
           rot=0, dot_color="", img_op=100, img_rot=0,
           img2="", img2_size=48, i2x=0, i2y=0, img2_op=100, img2_rot=0,
           img_fh=0, img_fv=0, img2_fh=0, img2_fv=0, img_tint="", img2_tint="",
           vid="", vid_size=256, vx=0, vy=0, vid_op=100, vid_black=False)
SLOTS = (dict(img="img", size="img_size", x="ix", y="iy", op="img_op", rot="img_rot", fh="img_fh", fv="img_fv", tint="img_tint"),
         dict(img="img2", size="img2_size", x="i2x", y="i2y", op="img2_op", rot="img2_rot", fh="img2_fh", fv="img2_fv", tint="img2_tint"))
EXTRA = dict(visible=True, dx=0, dy=0, mon=0, spread=0, bind="", ads="", cur="",
             gmap={}, my_colors=[], hide_outside=False, vid="", vid_size=256, vx=0, vy=0, vid_op=100, vid_black=False, splash=True,
             keys={}, gres={}, res_orig={}, res_set={}, res_off={}, res_revert=False, adapt=False, autoupd=True)
# vid stores base64-encoded GIF/video data (prefixed "VID1:") or legacy file path


# ---------- helpers (no UI) ----------
def clean(d):
    """Sanitize any preset coming from a file or code so a malformed one cannot break the app"""
    o = {}
    if not isinstance(d, dict):
        return o
    for k in PK:
        v = d.get(k)
        if v is None:
            continue
        if k in RNG:
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                o[k] = int(max(RNG[k][0], min(RNG[k][1], v)))
        elif k in ("color", "outline_color", "paint_color"):
            if isinstance(v, str) and HEX.match(v):
                o[k] = v
        elif k == "dot_color":
            if isinstance(v, str) and (v == "" or HEX.match(v)):
                o[k] = v
        elif k in ("img_tint", "img2_tint"):
            if isinstance(v, str) and (v in ("", "gray") or HEX.match(v)):
                o[k] = v
        elif k == "shape":
            if v in ARMS or v in POLY or v in ("circle", "chevron", "dot"):
                o[k] = v
        elif k in ("dot", "show_shape"):
            o[k] = bool(v)
        elif k == "opacity":
            if isinstance(v, (int, float)):
                o[k] = max(.1, min(1.0, float(v)))
        elif k in ("img", "img2"):
            if isinstance(v, str) and len(v) < 3000000:
                o[k] = v
        elif k == "vid":
            # Accept embedded base64 (VID1:...), a file path string, or empty
            if isinstance(v, str) and len(v) < 20000000:   # 20 MB cap
                o[k] = v
        elif k == "vid_black":
            o[k] = bool(v)
        elif k == "cells" and isinstance(v, dict):
            o[k] = {a: c for a, c in list(v.items())[:2000]
                    if isinstance(a, str) and CELLK.match(a) and isinstance(c, str) and HEX.match(c)}
    return o


def parse_color(t):
    """Accepts #ff8800 / ff8800 / #f80 / 255,136,0 / rgb(255,136,0) and returns #rrggbb or None"""
    if not isinstance(t, str):
        return None
    t = t.strip().lower().strip("\"'")
    m = re.fullmatch(r"#?([0-9a-f]{6})", t)
    if m:
        return "#" + m.group(1)
    m = re.fullmatch(r"#?([0-9a-f])([0-9a-f])([0-9a-f])", t)
    if m:
        return "#" + "".join(c * 2 for c in m.groups())
    m = re.fullmatch(r"(?:rgb\()?\s*(\d{1,3})\s*[, ]\s*(\d{1,3})\s*[, ]\s*(\d{1,3})\s*\)?", t)
    if m and all(int(x) <= 255 for x in m.groups()):
        return "#%02x%02x%02x" % tuple(int(x) for x in m.groups())
    return None


RES_RE = re.compile(r"^\s*(\d{3,5})\s*[x×*,\s]\s*(\d{3,5})\s*(?:[@\s]\s*(\d{2,3})\s*(?:hz)?)?\s*$", re.I)


def parse_res(t):
    """'1280x960' / '1280 960' / '1920×1080@144' -> (w, h, hz or None), else None"""
    m = RES_RE.match(t) if isinstance(t, str) else None
    if not m:
        return None
    w, h = int(m.group(1)), int(m.group(2))
    hz = int(m.group(3)) if m.group(3) else None
    if not (320 <= w <= 16384 and 240 <= h <= 16384) or (hz is not None and not 24 <= hz <= 1000):
        return None
    return w, h, hz


def res_text(w, h, hz=None):
    return f"{w}×{h}" + (f" @ {hz} Hz" if hz else "")


def res_key(w, h, hz=None):
    return f"{w}x{h}" + (f"@{hz}" if hz else "")


def enc(d):
    raw = json.dumps(d, separators=(",", ":")).encode()
    return "CH1:" + base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode()


def dec(s):
    s = s.strip()
    if not s.startswith("CH1:"):
        raise ValueError
    return json.loads(zlib.decompress(base64.urlsafe_b64decode(s[4:])))


B62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
SHAPE_L = [v for _, v in SHAPES]
CODE_COLORS = ["#00ff6a", "#ff2d2d", "#00e5ff", "#ffe600", "#ffffff", "#ff3df2", "#ff8a00", "#7c4dff",
               "#2d6bff", "#000000", "#b6ff00", "#00b894", "#ffb300", "#ff0066", "#8a8a8a", "#1e3cff"]
OPS = (.1, .2, .3, .5, .7, .85, 1.0)
RAD = (len(SHAPE_L), 16, 30, 12, 21, 7, 2, 8, 24, 2, 7)


def _near(c, pal):
    r = [int(c[i:i + 2], 16) for i in (1, 3, 5)]
    return min(range(len(pal)), key=lambda i: sum((a - int(pal[i][j:j + 2], 16)) ** 2 for a, j in zip(r, (1, 3, 5))))


def short_enc(d):
    """6-character code for the base shape (no hand drawing, no images)"""
    vals = [SHAPE_L.index(d["shape"]) if d["shape"] in SHAPE_L else 0,
            _near(d["color"], CODE_COLORS),
            max(0, min(29, round(d["length"] / 2) - 1)),
            max(0, min(11, d["thick"] - 1)),
            max(0, min(20, round(d["gap"] / 2))),
            max(0, min(6, d["outline"])),
            1 if d["dot"] else 0,
            max(0, min(7, d["dot_size"] - 1)),
            round(d["rot"] / 15) % 24,
            1 if sum(int(d["outline_color"][i:i + 2], 16) for i in (1, 3, 5)) > 380 else 0,
            min(range(len(OPS)), key=lambda i: abs(OPS[i] - d["opacity"]))]
    n = 0
    for v, r in zip(vals, RAD):
        n = n * r + v
    out = ""
    for _ in range(6):
        n, m = divmod(n, 62)
        out = B62[m] + out
    return out


def short_dec(code):
    n = 0
    for ch in code:
        n = n * 62 + B62.index(ch)
    vals = []
    for r in reversed(RAD):
        n, v = divmod(n, r)
        vals.append(v)
    if n:
        raise ValueError
    sh, co, le, th, ga, ou, do, ds, ro, oc, op = vals[::-1]
    return dict(shape=SHAPE_L[sh], color=CODE_COLORS[co], length=2 * (le + 1), thick=th + 1, gap=2 * ga,
                outline=ou, dot=bool(do), dot_size=ds + 1, rot=ro * 15,
                outline_color="#ffffff" if oc else "#000000", opacity=OPS[op])


def _shrink(b64, size):
    """Shrink the image to its display size and compress as WebP (much smaller than PNG)"""
    im = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGBA")
    k = size / max(im.size)
    if k < 1:
        im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), RS)
    b = io.BytesIO()
    try:
        im.save(b, "WEBP", quality=85, method=6)
    except Exception:
        b = io.BytesIO()
        im.save(b, "PNG", optimize=True)
    return b.getvalue()


def enc2(d):
    """Full code (CH2): shape + hand drawing + both images, as one pasteable string"""
    meta, blobs = dict(d), []
    for k, sk in (("img", "img_size"), ("img2", "img2_size")):
        blobs.append(_shrink(d[k], d[sk]) if d.get(k) else b"")
        meta[k] = ""
    mz = zlib.compress(json.dumps(meta, separators=(",", ":")).encode(), 9)
    out = struct.pack(">I", len(mz)) + mz
    for b in blobs:
        out += struct.pack(">I", len(b)) + b
    return "CH2:" + base64.urlsafe_b64encode(out).decode()


def dec2(s):
    raw = base64.urlsafe_b64decode(s.strip()[4:])
    n = struct.unpack(">I", raw[:4])[0]
    d = json.loads(zlib.decompressobj().decompress(raw[4:4 + n], 5000000))
    pos = 4 + n
    for k in ("img", "img2"):
        ln = struct.unpack(">I", raw[pos:pos + 4])[0]
        blob = raw[pos + 4:pos + 4 + ln]
        pos += 4 + ln
        if blob:
            im = Image.open(io.BytesIO(blob))
            if im.width * im.height > 4000000:
                raise ValueError
            im = im.convert("RGBA")
            im.thumbnail((512, 512), RS)
            b = io.BytesIO()
            im.save(b, "PNG")
            d[k] = base64.b64encode(b.getvalue()).decode()
    return d


def line_pts(x0, y0, x1, y1):
    pts, dx, dy = [], abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            return pts
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def flood(cells, n, x, y):
    tgt, seen, st = cells.get(f"{x},{y}"), set(), [(x, y)]
    while st:
        a, b = st.pop()
        if (a, b) in seen or not (0 <= a < n and 0 <= b < n) or cells.get(f"{a},{b}") != tgt:
            continue
        seen.add((a, b))
        st += [(a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)]
    return seen


# ---------- settings ----------
C = {**DEF, **EXTRA}
try:
    _d = json.load(open(CFG, encoding="utf-8"))
    C.update(clean(_d))
    for _k, _v in EXTRA.items():
        if _k in _d and type(_d[_k]) is type(_v):
            C[_k] = _d[_k]
except Exception:
    pass

_gm = C.get("gmap")
C["gmap"] = {k: v for k, v in _gm.items() if isinstance(k, str) and isinstance(v, str)} if isinstance(_gm, dict) else {}
_gr = C.get("gres")
C["gres"] = {k: v for k, v in _gr.items() if isinstance(k, str) and isinstance(v, str) and parse_res(v)} if isinstance(_gr, dict) else {}
for _k in ("res_orig", "res_set"):
    _v = C.get(_k)
    C[_k] = {d_: [int(x) for x in m_] for d_, m_ in _v.items()
             if isinstance(d_, str) and isinstance(m_, list) and len(m_) == 3 and all(isinstance(x, int) for x in m_)} if isinstance(_v, dict) else {}
_v = C.get("res_off")
C["res_off"] = {k: [int(o_[0]), int(o_[1])] for k, o_ in _v.items()
                if isinstance(k, str) and isinstance(o_, list) and len(o_) == 2 and all(isinstance(x, int) for x in o_)} if isinstance(_v, dict) else {}
LASTEXE = [""]

# ---------- hotkey definitions ----------
DEFAULT_KEYS = dict(toggle="F8", prev="F9", next="F10", left="Ctrl+Alt+Left", right="Ctrl+Alt+Right",
                    up="Ctrl+Alt+Up", down="Ctrl+Alt+Down", slot="Ctrl+Alt")
KEY_LABELS = dict(toggle="Show / hide", prev="Previous preset", next="Next preset", left="Nudge left",
                  right="Nudge right", up="Nudge up", down="Nudge down")
MODS = {"Alt": 1, "Ctrl": 2, "Shift": 4, "Win": 8}
VK_NAME = {0x25: "Left", 0x26: "Up", 0x27: "Right", 0x28: "Down", 0x20: "Space", 0x0D: "Enter", 0x09: "Tab",
           0x24: "Home", 0x23: "End", 0x21: "PageUp", 0x22: "PageDown", 0x2D: "Insert", 0x2E: "Delete",
           0x08: "Backspace"}
VK_NAME.update({0x70 + i: f"F{i + 1}" for i in range(24)})
VK_NAME.update({c: chr(c) for c in list(range(0x30, 0x3A)) + list(range(0x41, 0x5B))})
NAME_VK = {v: k for k, v in VK_NAME.items()}


def parse_key(sv):
    """'Ctrl+Alt+Left' -> (mod_flags, vk) or None"""
    if not isinstance(sv, str):
        return None
    parts = [p.strip() for p in sv.split("+")]
    if not parts or parts[-1] not in NAME_VK or any(p not in MODS for p in parts[:-1]):
        return None
    return sum(MODS[p] for p in set(parts[:-1])), NAME_VK[parts[-1]]


def parse_mods(sv):
    if not isinstance(sv, str) or not sv:
        return None
    parts = [p.strip() for p in sv.split("+")]
    return sum(MODS[p] for p in set(parts)) if all(p in MODS for p in parts) else None


def build_combos(keys):
    """list of (id, mod, vk, action, label) for every hotkey; ids 1-7 fixed actions, 11-19 preset slots"""
    out = []
    for i, a in enumerate(("toggle", "prev", "next", "left", "right", "up", "down"), 1):
        mv = parse_key(keys[a])
        out.append((i, mv[0], mv[1], a, f"{KEY_LABELS[a]} ({keys[a]})"))
    sm = parse_mods(keys["slot"])
    for n in range(9):
        out.append((11 + n, sm, 0x31 + n, f"slot{n}", f"{keys['slot']}+{n + 1}"))
    return out


def keys_valid(keys):
    try:
        c = build_combos(keys)
    except Exception:
        return False
    pairs = [(m, v) for _i, m, v, _a, _l in c]
    return len(set(pairs)) == len(pairs) and all(m is not None for m, _ in pairs)


_k = C.get("keys")
C["keys"] = {**DEFAULT_KEYS, **{a: v for a, v in (_k.items() if isinstance(_k, dict) else [])
                                if a in DEFAULT_KEYS and isinstance(v, str)}}
if not keys_valid(C["keys"]):
    C["keys"] = dict(DEFAULT_KEYS)

q = queue.Queue()
post = q.put

# ---------- windows ----------
root = tk.Tk()
root.report_callback_exception = lambda *a: logging.error("tk callback", exc_info=a)
root.overrideredirect(True)
root.attributes("-topmost", True)
root.config(bg=KEY)
root.attributes("-transparentcolor", KEY)
cv = tk.Canvas(root, bg=KEY, highlightthickness=0, bd=0)
cv.pack()
for _k, _v in {"*Background": PANEL, "*Foreground": FG, "*Button.background": BTN, "*Button.foreground": FG,
               "*Button.activeBackground": ACC_HI, "*Button.activeForeground": "#fff", "*Button.relief": "flat",
               "*Button.cursor": "hand2", "*Button.highlightThickness": 0, "*Font": ("Segoe UI", 10),
               "*Entry.highlightThickness": 1, "*Entry.highlightBackground": EDGE, "*Entry.highlightColor": ACC,
               "*Button.bd": 0, "*Button.padX": 10, "*Button.pady": 4, "*Entry.background": BTN,
               "*Entry.foreground": FG, "*Entry.insertBackground": FG, "*Entry.relief": "flat",
               "*Checkbutton.selectColor": BTN, "*Checkbutton.activeBackground": PANEL,
               "*Checkbutton.activeForeground": FG, "*Spinbox.background": BTN, "*Spinbox.foreground": FG,
               "*Spinbox.buttonBackground": BTN, "*Scale.troughColor": BTN, "*Scale.highlightThickness": 0,
               "*Scale.activeBackground": ACC_HI, "*Scale.background": PANEL}.items():
    root.option_add(_k, _v)

imgw = tk.Toplevel(root)
imgw.overrideredirect(True)
imgw.attributes("-topmost", True)
imgw.config(bg=KEY)
imgw.attributes("-transparentcolor", KEY)
ilab = tk.Label(imgw, bd=0, bg=KEY)
ilab.pack()
imgw.withdraw()
imgw2 = tk.Toplevel(root)
imgw2.overrideredirect(True)
imgw2.attributes("-topmost", True)
imgw2.config(bg=KEY)
imgw2.attributes("-transparentcolor", KEY)
ilab2 = tk.Label(imgw2, bd=0, bg=KEY)
ilab2.pack()
imgw2.withdraw()
IW = ((imgw, ilab), (imgw2, ilab2))

vidw = tk.Toplevel(root)
vidw.overrideredirect(True)
vidw.attributes("-topmost", True)
vidw.config(bg=KEY)
vidw.attributes("-transparentcolor", KEY)
vlab = tk.Label(vidw, bd=0, bg=KEY)
vlab.pack()
vidw.withdraw()

MON, MON_DEV, CT, IC = [None], [None], {"img": False, "img2": False, "vid": False}, [[None, None], [None, None]]
PREVIEW = [False]   # hover preview in the settings window: force the crosshair visible
LMB, RMB, BOUND, TICK, SV = [False], [False], [True], [0], [None]


def clickthrough(win):
    win.update_idletasks()
    h = U32.GetParent(win.winfo_id()) or win.winfo_id()
    U32.SetWindowLongW(h, -20, U32.GetWindowLongW(h, -20) | 0x80000 | 0x20 | 0x80)


class MONINFOEXW(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT), ("rcWork", wt.RECT), ("dwFlags", wt.DWORD),
                ("szDevice", wt.WCHAR * 32)]


_UM = ctypes.WinDLL("user32")   # private handle: its argtypes never clash with the ones set elsewhere
_UM.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]


def mons(refresh=False):
    if MON[0] is None or refresh:
        r = []
        CB = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(wt.RECT), ctypes.c_void_p)

        def cb(h, dc, rc, d):
            x = rc.contents
            mi = MONINFOEXW()
            mi.cbSize = ctypes.sizeof(MONINFOEXW)
            dev = mi.szDevice if _UM.GetMonitorInfoW(h, ctypes.addressof(mi)) else ""
            r.append(((x.left, x.top, x.right - x.left, x.bottom - x.top), dev))
            return 1
        U32.EnumDisplayMonitors(None, None, CB(cb), 0)
        r.sort(key=lambda m: (m[0][:2] != (0, 0), m[0][0], m[0][1]))
        MON[0] = [m[0] for m in r] or [(0, 0, root.winfo_screenwidth(), root.winfo_screenheight())]
        MON_DEV[0] = [m[1] for m in r] or [""]
    return MON[0]


def mon_rect():
    m = mons()
    return m[min(C["mon"], len(m) - 1)]


def fg_exe():
    try:
        pid = wt.DWORD()
        U32.GetWindowThreadProcessId(U32.GetForegroundWindow(), ctypes.byref(pid))
        h = K32.OpenProcess(0x1000, False, pid.value)
        if not h:
            return ""
        buf, n = ctypes.create_unicode_buffer(520), wt.DWORD(520)
        K32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n))
        K32.CloseHandle(h)
        return os.path.normcase(os.path.normpath(buf.value))
    except Exception:
        return ""


def is_own(p):
    return os.path.basename(p) == OWN


def has_sep(k):
    return "\\" in k or "/" in k


def same_exe(p, k):
    """k is a full path (exact match) or a legacy bare name like 'game.exe' (matches any folder)"""
    return bool(k) and (p == k or (not has_sep(k) and os.path.basename(p) == k))


def link_for(p):
    """preset name linked to the running exe path: exact full-path link first, then legacy name link"""
    v = C["gmap"].get(p)
    if v:
        return v
    for k, v in C["gmap"].items():
        if same_exe(p, k):
            return v
    return None


def preset_data(name):
    try:
        d = clean(json.load(open(os.path.join(PRE, name + ".json"), encoding="utf-8")))
    except Exception:
        return None
    return {**{k: DEF[k] for k in PK}, **d}


def cross_half(v):
    half = int((v["gap"] + v["length"]) * 1.5) + v["thick"] + v["outline"] + v["dot_size"] + 4
    if v["cells"]:
        half = max(half, v["grid_n"] * v["cell"] // 2 + 3)
    return half


AD = {"req": None, "bg": None, "alt": False, "col": None}
T_LOW, T_HIGH = 150, 200  # similarity limits (redmean distance): below LOW = looks like the background, above HIGH = clear


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _comp(h):
    return "#%02x%02x%02x" % tuple(255 - c for c in _rgb(h))


def _cdist(a, b):
    rm = (a[0] + b[0]) / 2
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return math.sqrt((2 + rm / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rm) / 256) * db * db)


def adapt_request():
    """(main thread) where to sample: a ring of pixels just outside the crosshair window"""
    v = view(True)
    mx0, my0, mw, mh = mon_rect()
    AD["req"] = (mx0 + mw // 2 + C["dx"], my0 + mh // 2 + C["dy"], cross_half(v) + 3, 14)


def adapt_worker():
    """background thread: grabs the small area and averages the ring (never touches the UI)"""
    while True:
        time.sleep(0.1)
        r, AD["req"] = AD["req"], None
        if r is None:
            continue
        cx, cy, inner, pad = r
        R_ = inner + pad
        box = (cx - R_, cy - R_, cx + R_, cy + R_)
        try:
            try:
                im = ImageGrab.grab(bbox=box, all_screens=True)
            except TypeError:
                im = ImageGrab.grab(bbox=box)
            mask = Image.new("L", im.size, 255)
            ImageDraw.Draw(mask).rectangle((pad, pad, im.width - pad - 1, im.height - pad - 1), fill=0)
            bg = tuple(ImageStat.Stat(im.convert("RGB"), mask).mean)
        except Exception:
            logging.exception("adapt grab")
            continue
        post(lambda bg=bg: adapt_apply(bg))


def adapt_apply(bg):
    if not C["adapt"]:
        return
    old = AD["bg"]
    AD["bg"] = bg if old is None else tuple(o * .6 + n * .4 for o, n in zip(old, bg))  # smoothing: no flicker
    base = view(True)["color"]
    d = _cdist(_rgb(base), AD["bg"])
    if AD["alt"]:
        if d > T_HIGH:
            AD["alt"] = False
    elif d < T_LOW:
        AD["alt"] = True
    col = None
    if AD["alt"]:
        cands = [_comp(base), "#ffffff", "#000000"]
        col = next((c for c in cands if _cdist(_rgb(c), AD["bg"]) >= T_HIGH), None) \
            or max(cands, key=lambda c: _cdist(_rgb(c), AD["bg"]))
    if col != AD["col"]:
        AD["col"] = col
        draw()


def view(raw=False):
    v = dict(C)
    if RMB[0] and C["ads"]:
        d = preset_data(C["ads"])
        if d:
            v.update(d)
    if LMB[0] and C["spread"]:
        v["gap"] += C["spread"]
    if not raw and C["adapt"] and AD["col"]:
        v["color"] = AD["col"]
    return v


def load_img(v, i=0):
    S = SLOTS[i]
    if not v[S["img"]]:
        return None
    key = (hash(v[S["img"]]), v[S["size"]], v[S["rot"]], v[S["fh"]], v[S["fv"]], v[S["tint"]])
    if IC[i][0] != key:
        try:
            im = Image.open(io.BytesIO(base64.b64decode(v[S["img"]]))).convert("RGBA")
            if v[S["fh"]]:
                im = im.transpose(getattr(Image, "Transpose", Image).FLIP_LEFT_RIGHT)
            if v[S["fv"]]:
                im = im.transpose(getattr(Image, "Transpose", Image).FLIP_TOP_BOTTOM)
            if v[S["rot"]]:
                im = im.rotate(-v[S["rot"]], expand=True, resample=Image.BICUBIC)
            tt = v[S["tint"]]
            if tt:
                a = im.getchannel("A")
                if tt == "gray":
                    g = im.convert("L")
                    im = Image.merge("RGBA", (g, g, g, a))
                else:
                    im = Image.new("RGBA", im.size, tuple(int(tt[i:i + 2], 16) for i in (1, 3, 5)) + (255,))
                    im.putalpha(a)
            k = v[S["size"]] / max(im.size)
            im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), RS)
            bg = Image.new("RGB", im.size, (1, 1, 1))
            bg.paste(im.convert("RGB"), mask=im.getchannel("A").point(lambda p: 255 if p >= 128 else 0))
            IC[i] = [key, ImageTk.PhotoImage(bg)]
        except Exception:
            logging.exception("load_img slot %d", i)
            return None
    return IC[i][1]


def gate():
    """Is the crosshair restricted to specific game windows?"""
    return bool(C["bind"] or (C["hide_outside"] and C["gmap"]))


def shown():
    return PREVIEW[0] or (C["visible"] and (not gate() or BOUND[0]))


def _vid_is_b64(v):
    return isinstance(v, str) and v.startswith("VID1:")

def _vid_to_bytes(v):
    """Decode VID1:<base64> → bytes"""
    return base64.b64decode(v[5:])

def _vid_from_bytes(data, ext=".gif"):
    """Encode raw bytes → VID1:<base64> string"""
    return "VID1:" + base64.b64encode(data).decode()


class Src:
    """Video source: GIF via Pillow, every other format via OpenCV.
    Accepts either a file path (legacy) or a VID1:<base64> string."""

    def __init__(s, path_or_b64):
        s.i, s.cap = 0, None
        if _vid_is_b64(path_or_b64):
            # Embedded data — always treated as GIF (only GIFs get embedded)
            s.gif = True
            s.im = Image.open(io.BytesIO(_vid_to_bytes(path_or_b64)))
            s.n = getattr(s.im, "n_frames", 1)
        else:
            path = path_or_b64
            s.gif = path.lower().endswith(".gif")
            if s.gif:
                s.im = Image.open(path)
                s.n = getattr(s.im, "n_frames", 1)
            else:
                if cv2 is None:
                    raise RuntimeError("opencv")
                s.cap = cv2.VideoCapture(path)
                if not s.cap.isOpened():
                    raise RuntimeError("open")
                s.dl = min(100, max(8, 1000 / (s.cap.get(cv2.CAP_PROP_FPS) or 30)))

    def read(s, size):
        if s.gif:
            s.im.seek(s.i)
            s.i = (s.i + 1) % s.n
            fr = s.im.convert("RGBA")
            k = size / max(fr.size)
            fr = fr.resize((max(1, round(fr.width * k)), max(1, round(fr.height * k))), RS)
            return fr, max(20, s.im.info.get("duration", 100) or 100)
        ok, f = s.cap.read()
        if not ok:
            s.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, f = s.cap.read()
            if not ok:
                raise RuntimeError("read")
        h, w = f.shape[:2]
        k = size / max(w, h)
        f = cv2.resize(f, (max(1, round(w * k)), max(1, round(h * k))),
                       interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_LINEAR)
        return Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)).convert("RGBA"), s.dl

    def close(s):
        try:
            if s.cap:
                s.cap.release()
        except Exception:
            pass


VP = {"src": None, "path": "", "job": None, "geo": None, "vis": False, "n": 0}


def vid_hide():
    if VP["job"]:
        root.after_cancel(VP["job"])
        VP["job"] = None
    vidw.withdraw()
    VP["vis"] = False


def vid_close():
    vid_hide()
    if VP["src"]:
        VP["src"].close()
    VP.update(src=None, path="", geo=None)


def vid_tick():
    VP["job"] = None
    t0 = time.time()
    try:
        fr, dl = VP["src"].read(max(16, min(1920, C["vid_size"])))
        mask = fr.getchannel("A").point(lambda p: 255 if p >= 128 else 0)
        if C["vid_black"]:
            mask = ImageChops.multiply(mask, fr.convert("L").point(lambda p: 255 if p > 30 else 0))
        bg = Image.new("RGB", fr.size, (1, 1, 1))
        bg.paste(fr.convert("RGB"), mask=mask)
        ph = ImageTk.PhotoImage(bg)
        vlab.config(image=ph)
        vlab.image = ph
        w, h = ph.width(), ph.height()
        mx0, my0, mw, mh = mon_rect()
        geo = f"{w}x{h}+{mx0 + mw // 2 - w // 2 + C['vx']}+{my0 + mh // 2 - h // 2 + C['vy']}"
        if geo != VP["geo"]:
            vidw.geometry(geo)
            VP["geo"] = geo
        vidw.attributes("-alpha", C["vid_op"] / 100)
        VP["n"] += 1
        if not VP["vis"] or VP["n"] % 50 == 0:
            vidw.deiconify()
            vidw.attributes("-topmost", True)
            VP["vis"] = True
        if not CT["vid"]:
            clickthrough(vidw)
            CT["vid"] = True
        wait = max(5, int(dl - (time.time() - t0) * 1000))
        VP["job"] = root.after(wait, vid_tick)
    except Exception:
        logging.exception("video")
        vid_close()
        C["vid"] = ""
        toast("Video stopped: playback error")


def vid_sync():
    if not C["vid"] or not shown():
        vid_hide()
        return
    if VP["path"] != C["vid"]:
        vid_close()
        try:
            VP["src"] = Src(C["vid"])
            VP["path"] = C["vid"]
        except Exception as ex:
            logging.exception("video open")
            C["vid"] = ""
            toast("opencv is required to play video (GIF works without it)" if str(ex) == "opencv" else "Could not open the video")
            return
    VP["geo"] = None
    if not VP["job"]:
        vid_tick()


def paint(can, v, cx, cy):
    """Draw the crosshair (hand drawing + shape + dot) centered at cx, cy on any canvas"""
    l, t, g, o, ds = v["length"], v["thick"], v["gap"], v["outline"], v["dot_size"]
    k, h = v["cell"], v["grid_n"] // 2
    for key, c in v["cells"].items():
        x, y = map(int, key.split(","))
        x0, y0 = cx + (x - h) * k - k // 2, cy + (y - h) * k - k // 2
        can.create_rectangle(x0, y0, x0 + k - 1, y0 + k - 1, fill=c, outline=c)
    passes = [(v["outline_color"], o), (v["color"], 0)] if o else [(v["color"], 0)]
    if not v["show_shape"]:
        passes = []
    ang = math.radians(v["rot"])
    ca, sa = math.cos(ang), math.sin(ang)

    def R(x, y):
        return cx + x * ca - y * sa, cy + x * sa + y * ca
    dcol = v["dot_color"]
    for col, e in passes:
        w = t + 2 * e
        for ux, uy in ARMS.get(v["shape"], []):
            a0, a1 = g - e, g + l + e
            x0_, y0_ = R(ux * a0, uy * a0)
            x1_, y1_ = R(ux * a1, uy * a1)
            can.create_line(x0_, y0_, x1_, y1_, fill=col, width=w, capstyle="butt")
        sh = v["shape"]
        if sh == "ringx" and g > 0:
            can.create_oval(cx - g, cy - g, cx + g, cy + g, outline=col, width=w)
        elif sh == "circle":
            can.create_oval(cx - l, cy - l, cx + l, cy + l, outline=col, width=w)
        elif sh in POLY:
            pts = [c for px, py in POLY[sh] for c in R(px * l, py * l)]
            can.create_polygon(*pts, outline=col, fill="", width=w, joinstyle="miter")
        elif sh == "chevron":
            pts = [c for px, py in ((-l, l * .6), (0, -l * .6), (l, l * .6)) for c in R(px, py)]
            can.create_line(*pts, fill=col, width=w, joinstyle="miter", capstyle="butt")
        if v["dot"] or sh == "dot":
            r = ds + e
            dc = (dcol or col) if e == 0 else col
            can.create_oval(cx - r, cy - r, cx + r, cy + r, fill=dc, outline=dc)


LA = {}   # last values pushed to each overlay window; re-sending identical window attributes every frame
#          (alpha / deiconify / topmost) makes layered windows flicker or vanish while they are being dragged


def win_set(win, key, name, val):
    if LA.get((key, name)) != val:
        win.attributes(name, val)
        LA[(key, name)] = val


def win_show(win, key):
    if LA.get((key, "vis")) is not True:
        win.deiconify()
        win.attributes("-topmost", True)
        LA[(key, "vis")] = True


def win_hide(win, key):
    if LA.get((key, "vis")) is not False:
        win.withdraw()
        LA[(key, "vis")] = False
        LA.pop((key, "geo"), None)


def win_geo(win, key, geo):
    if LA.get((key, "geo")) != geo:
        win.geometry(geo)
        LA[(key, "geo")] = geo


def draw():
    v = view()
    mx0, my0, mw, mh = mon_rect()
    mcx, mcy = mx0 + mw // 2, my0 + mh // 2
    cv.delete("all")
    half = cross_half(v)
    W = half * 2 + 1
    cx = cy = half
    win_geo(root, "xh", f"{W}x{W}+{mcx - half + C['dx']}+{mcy - half + C['dy']}")
    cv.config(width=W, height=W)
    win_set(root, "xh", "-alpha", v["opacity"])
    paint(cv, v, cx, cy)
    on = shown()
    if on:
        win_show(root, "xh")
    else:
        win_hide(root, "xh")
    for i, S in enumerate(SLOTS):
        win, lab = IW[i]
        key = "img" if i == 0 else "img2"
        ph = load_img(v, i) if on else None
        if ph:
            if getattr(lab, "image", None) is not ph:
                lab.config(image=ph)
                lab.image = ph
            w, hh = ph.width(), ph.height()
            win_geo(win, key, f"{w}x{hh}+{mcx - w // 2 + v[S['x']]}+{mcy - hh // 2 + v[S['y']]}")
            win_set(win, key, "-alpha", v[S["op"]] / 100)
            win_show(win, key)
            if not CT[key]:
                clickthrough(win)
                CT[key] = True
        else:
            win_hide(win, key)
    vid_sync()


def tray_img():
    """Tray icon = the current crosshair shape in dark red with a darker outline (warm grey when hidden)"""
    im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col, edge = ("#b3182a", "#2a0509") if shown() else ("#5f5154", "#1c1517")
    sh, g, l, t = C["shape"], C["gap"], max(1, C["length"]), C["thick"]
    arms = sh in ARMS
    ext = max(g + l, 1) if arms else l
    k = min(3.0, (26 if arms or sh == "circle" else 19) / ext)
    g2, l2, tw = g * k, l * k, max(3, min(10, round(t * k)))
    ca, sa = math.cos(math.radians(C["rot"])), math.sin(math.radians(C["rot"]))

    def R(x, y):
        return (32 + x * ca - y * sa, 32 + x * sa + y * ca)
    for c, e in ((edge, 3), (col, 0)):
        w = tw + 2 * e
        for ux, uy in ARMS.get(sh, []):
            d.line([R(ux * (g2 - e), uy * (g2 - e)), R(ux * (g2 + l2 + e), uy * (g2 + l2 + e))], fill=c, width=w)
        if sh == "ringx" and g2 > 1:
            d.ellipse((32 - g2, 32 - g2, 32 + g2, 32 + g2), outline=c, width=w)
        elif sh == "circle":
            d.ellipse((32 - l2, 32 - l2, 32 + l2, 32 + l2), outline=c, width=w)
        elif sh in POLY:
            pts = [R(px * l2, py * l2) for px, py in POLY[sh]]
            d.line(pts + [pts[0], pts[1]], fill=c, width=w, joint="curve")
        elif sh == "chevron":
            d.line([R(-l2, l2 * .6), R(0, -l2 * .6), R(l2, l2 * .6)], fill=c, width=w, joint="curve")
        if C["dot"] or sh == "dot":
            r = min(9, max(2, C["dot_size"] * k)) + e
            d.ellipse((32 - r, 32 - r, 32 + r, 32 + r), fill=c)
    return im


def save():
    try:
        json.dump(C, open(CFG, "w", encoding="utf-8"))
    except OSError:
        logging.exception("save")


def save_soon():
    if SV[0]:
        root.after_cancel(SV[0])
    SV[0] = root.after(600, save)


def apply():
    mons(True)
    draw()
    save()
    icon.icon = tray_img()
    icon.title = "Reticle - %s - %s" % (C["cur"] or "no preset", "visible" if shown() else "hidden")
    icon.update_menu()


def toast(msg, ms=1600):
    t = tk.Toplevel(root)
    t.overrideredirect(True)
    t.attributes("-topmost", True)
    t.configure(bg=ACC)
    tk.Label(t, text=msg, bg=BTN, fg=FG, font=("Segoe UI", 12), padx=16, pady=8).pack(padx=1, pady=1)
    t.update_idletasks()
    x, y, w, h = mon_rect()
    t.geometry(f"+{x + w // 2 - t.winfo_width() // 2}+{y + h - 140}")
    clickthrough(t)
    t.after(ms, t.destroy)


def mk(title):
    d = tk.Toplevel(root)
    d.title(title)
    d.attributes("-topmost", True)
    d.configure(bg=PANEL)
    d.update_idletasks()
    try:
        h = U32.GetParent(d.winfo_id()) or d.winfo_id()
        dw = ctypes.windll.dwmapi.DwmSetWindowAttribute
        dw(h, 20, ctypes.byref(ctypes.c_int(1)), 4)                # dark title bar
        dw(h, 35, ctypes.byref(ctypes.c_int(0x111017)), 4)         # caption color (Win11) = panel
        dw(h, 34, ctypes.byref(ctypes.c_int(0x2c20a8)), 4)         # border color (Win11) = accent
    except Exception:
        pass
    return d


def ask_text(title, prompt, initial=""):
    d = mk(title)
    d.resizable(False, False)
    tk.Label(d, text=prompt).pack(padx=16, pady=(16, 6))
    e = tk.Entry(d, width=28, justify="left")
    e.pack(padx=16, ipady=4)
    if initial:
        e.insert(0, initial)
        e.select_range(0, "end")
    e.focus_force()
    out = [None]

    def ok(*_):
        out[0] = e.get()
        d.destroy()
    e.bind("<Return>", ok)
    e.bind("<Escape>", lambda _e: d.destroy())
    b = tk.Frame(d)
    b.pack(pady=14)
    tk.Button(b, text="Save", command=ok, bg=ACC, fg="#fff").pack(side="left", padx=4)
    tk.Button(b, text="Cancel", command=d.destroy).pack(side="left", padx=4)
    d.grab_set()
    d.wait_window()
    return out[0]


def ask_save_discard(name):
    """Returns 'save', 'discard' or None (cancel)"""
    d = mk("Unsaved changes")
    d.resizable(False, False)
    tk.Label(d, text=f"Preset \"{name}\" has unsaved changes.\nSave them before switching?").pack(padx=18, pady=(16, 8))
    out = [None]

    def pick(v):
        out[0] = v
        d.destroy()
    b = tk.Frame(d)
    b.pack(pady=14)
    tk.Button(b, text="Save", command=lambda: pick("save"), bg=ACC, fg="#fff").pack(side="left", padx=4)
    tk.Button(b, text="Discard", command=lambda: pick("discard")).pack(side="left", padx=4)
    tk.Button(b, text="Cancel", command=d.destroy).pack(side="left", padx=4)
    d.bind("<Escape>", lambda _e: d.destroy())
    d.grab_set()
    d.focus_force()
    d.wait_window()
    return out[0]


def ask_yes_no(title, text, yes="Yes"):
    d = mk(title)
    d.resizable(False, False)
    tk.Label(d, text=text, justify="left").pack(padx=18, pady=(16, 8))
    out = [False]

    def pick(v):
        out[0] = v
        d.destroy()
    b = tk.Frame(d)
    b.pack(pady=14)
    tk.Button(b, text=yes, command=lambda: pick(True), bg=ACC, fg="#fff").pack(side="left", padx=4)
    tk.Button(b, text="Not now", command=d.destroy).pack(side="left", padx=4)
    d.bind("<Escape>", lambda _e: d.destroy())
    d.grab_set()
    d.focus_force()
    d.wait_window()
    return out[0]


def capture_key(title, hint):
    """Modal window: press the new shortcut. Returns 'Ctrl+Alt+Left' style text, or None (Esc / closed)."""
    d = mk(title)
    d.resizable(False, False)
    tk.Label(d, text=hint, justify="center").pack(padx=22, pady=(18, 6))
    msg = tk.Label(d, text="Esc = cancel", fg=MUTE)
    msg.pack(pady=(0, 16))
    out = [None]
    skip = {0x10, 0x11, 0x12, 0x5B, 0x5C, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0x14}

    def press(e):
        vk = e.keycode
        if vk == 0x1B:
            d.destroy()
            return "break"
        if vk in skip:
            return "break"
        name = VK_NAME.get(vk)
        if not name:
            msg.config(text="That key is not supported - try another", fg=ACC_HI)
            return "break"
        gk = U32.GetAsyncKeyState
        mods = [n for n, v in (("Ctrl", 0x11), ("Alt", 0x12), ("Shift", 0x10)) if gk(v) & 0x8000]
        if gk(0x5B) & 0x8000 or gk(0x5C) & 0x8000:
            mods.append("Win")
        out[0] = "+".join(mods + [name])
        d.destroy()
        return "break"
    d.bind("<KeyPress>", press)
    d.bind("<F10>", press)
    d.grab_set()
    d.focus_force()
    d.wait_window()
    return out[0]


def eyedropper():
    """Eyedropper: click any point on the screen to pick its color (Esc = cancel)"""
    x0, y0 = U32.GetSystemMetrics(76), U32.GetSystemMetrics(77)
    w, h = U32.GetSystemMetrics(78), U32.GetSystemMetrics(79)
    o = tk.Toplevel(root)
    o.overrideredirect(True)
    o.attributes("-topmost", True)
    o.attributes("-alpha", 0.01)
    o.geometry(f"{w}x{h}+{x0}+{y0}")
    o.configure(bg="#000", cursor="crosshair")
    out = [None]

    def click(e):
        pt = wt.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        o.withdraw()
        o.update()
        time.sleep(0.08)
        u, g_ = ctypes.windll.user32, ctypes.windll.gdi32
        u.GetDC.restype = ctypes.c_void_p
        g_.GetPixel.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        u.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        dc = u.GetDC(None)
        px = g_.GetPixel(dc, pt.x, pt.y)
        u.ReleaseDC(None, dc)
        if px != -1:
            out[0] = "#%02x%02x%02x" % (px & 255, (px >> 8) & 255, (px >> 16) & 255)
        o.destroy()
    o.bind("<Button-1>", click)
    o.bind("<Button-3>", lambda _e: o.destroy())
    o.bind("<Escape>", lambda _e: o.destroy())
    o.focus_force()
    o.grab_set()
    o.wait_window()
    return out[0]


def clip_color():
    try:
        return parse_color(root.clipboard_get())
    except Exception:
        return None


def pick_color(init):
    """Free color picker: RGB sliders - type/paste a code (#hex or rgb) - Windows palette - screen eyedropper - saved colors"""
    from tkinter import colorchooser
    d = mk("Pick a color")
    d.resizable(False, False)
    init = parse_color(init) or "#ffffff"
    rgb = [int(init[i:i + 2], 16) for i in (1, 3, 5)]
    vs = [tk.IntVar(value=x) for x in rgb]
    hv, out = tk.StringVar(), [None]
    prev = tk.Label(d, height=2)
    prev.pack(fill="x", padx=14, pady=(14, 6))

    def cur():
        return "#%02x%02x%02x" % tuple(x.get() for x in vs)

    def upd(*_):
        prev.config(bg=cur())
        hv.set(cur())

    def setc(c, rewrite=True):
        c = parse_color(c)
        if c:
            for x, i in zip(vs, (1, 3, 5)):
                x.set(int(c[i:i + 2], 16))
            prev.config(bg=c)
            if rewrite:
                hv.set(c)
            return True
        return False
    for n, x in zip("RGB", vs):
        r = tk.Frame(d)
        r.pack(padx=14)
        tk.Label(r, text=n, width=2).pack(side="left")
        tk.Scale(r, from_=0, to=255, orient="horizontal", variable=x, command=upd, length=220,
                 showvalue=True, bd=0, bg=PANEL, fg=FG).pack(side="left")
    sw = tk.Frame(d)
    sw.pack(pady=6)
    for c in [c for _, c in MENU_COLORS]:
        tk.Button(sw, bg=c, width=2, padx=0, pady=0, command=lambda c=c: setc(c)).pack(side="left", padx=2)
    tk.Label(d, text="My colors (right-click = delete)", fg=MUTE, bg=PANEL).pack()
    mf = tk.Frame(d)
    mf.pack(pady=4)

    def rebuild():
        for w_ in mf.winfo_children():
            w_.destroy()
        for c in C["my_colors"]:
            b_ = tk.Button(mf, bg=c, width=2, padx=0, pady=0, command=lambda c=c: setc(c))
            b_.pack(side="left", padx=2)
            b_.bind("<Button-3>", lambda _e, c=c: (C["my_colors"].remove(c), save(), rebuild()))
        if not C["my_colors"]:
            tk.Label(mf, text="Empty - click \"+ Save color\"", fg=MUTE, bg=PANEL).pack()

    def save_my():
        c = cur()
        if c not in C["my_colors"]:
            C["my_colors"] = (C["my_colors"] + [c])[-16:]
            save()
            rebuild()

    e = tk.Entry(d, textvariable=hv, width=14, justify="center")
    e.pack(pady=4, ipady=3)
    e.bind("<Return>", lambda _e: (setc(hv.get()) or upd()))
    e.bind("<KeyRelease>", lambda _e: setc(hv.get(), False) and None)

    def paste():
        if not setc(clip_color() or ""):
            toast("Clipboard has no color code (example: #ff8800)")

    def sysdlg():
        r = colorchooser.askcolor(color=cur(), parent=d, title="Color palette")
        if r and r[1]:
            setc(r[1])

    def drop():
        d.withdraw()
        c = eyedropper()
        d.deiconify()
        d.grab_set()
        if c:
            setc(c)
    tools = tk.Frame(d)
    tools.pack(pady=4)
    for t_, f_ in (("Paste code", paste), ("Windows palette", sysdlg), ("Eyedropper", drop), ("+ Save color", save_my)):
        tk.Button(tools, text=t_, command=f_, bg=BTN, fg=FG).pack(side="left", padx=3)

    def ok():
        c = parse_color(hv.get()) or cur()
        out[0] = c
        d.destroy()
    b = tk.Frame(d)
    b.pack(pady=12)
    tk.Button(b, text="OK", command=ok, bg=ACC, fg="#fff").pack(side="left", padx=4)
    tk.Button(b, text="Cancel", command=d.destroy).pack(side="left", padx=4)
    rebuild()
    upd()
    d.grab_set()
    d.wait_window()
    return out[0]


PLACING = [None]
SIZE_LIM = {"img_size": (8, 512), "img2_size": (8, 512), "vid_size": (16, 1024)}


def place(kind):
    """Move mode: drag with the mouse (live preview) - arrows for fine nudging - wheel resizes - Enter = done - Esc = cancel"""
    if PLACING[0] is not None and PLACING[0].winfo_exists():
        PLACING[0].lift()
        return
    kx, ky, ks = {"img": ("ix", "iy", "img_size"), "img2": ("i2x", "i2y", "img2_size"),
                  "vid": ("vx", "vy", "vid_size")}.get(kind, ("dx", "dy", None))
    orig = (C[kx], C[ky], C[ks] if ks else None)
    mx0, my0, mw, mh = mon_rect()
    p = tk.Toplevel(root)
    PLACING[0] = p
    p.overrideredirect(True)
    p.attributes("-topmost", True)
    p.attributes("-alpha", 0.01)   # almost invisible catcher: it must NOT dim or hide the thing being moved
    p.geometry(f"{mw}x{mh}+{mx0}+{my0}")
    c = tk.Canvas(p, bg="#000", highlightthickness=0, cursor="fleur")
    c.pack(fill="both", expand=True)
    hint = "Drag with the mouse to move   •   Arrows = fine nudge (Shift = 10)"
    if ks:
        hint += "   •   Mouse wheel = resize"
    hw = tk.Toplevel(root)   # small control panel (separate window so the catcher above can stay see-through)
    hw.overrideredirect(True)
    hw.attributes("-topmost", True)
    hw.configure(bg=ACC)
    hb = tk.Frame(hw, bg=PANEL)
    hb.pack(padx=2, pady=2)
    tk.Label(hb, text=hint, font=("Segoe UI", 13), padx=16, pady=6).pack()
    tk.Label(hb, text="Enter or double-click = done   •   Esc or right-click = cancel", fg=MUTE).pack()
    st = {"sx": 0, "sy": 0, "ox": 0, "oy": 0, "t": 0.0, "dragging": False}

    def _cursor_pos():
        pt = wt.POINT()
        U32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def live(force=False):
        if force or time.time() - st["t"] > 0.008:
            st["t"] = time.time()
            draw()

    def close(keep):
        if not keep:
            C[kx], C[ky] = orig[0], orig[1]
            if ks:
                C[ks] = orig[2]
        PLACING[0] = None
        hw.destroy()
        p.destroy()
        apply()

    def press(e):
        cx, cy = _cursor_pos()
        st.update(sx=cx, sy=cy, ox=C[kx], oy=C[ky], dragging=True)

    def drag(e):
        if not st["dragging"]:
            return
        cx, cy = _cursor_pos()
        C[kx] = max(-3000, min(3000, st["ox"] + cx - st["sx"]))
        C[ky] = max(-3000, min(3000, st["oy"] + cy - st["sy"]))
        live()

    def release(e):
        if st["dragging"]:
            cx, cy = _cursor_pos()
            C[kx] = max(-3000, min(3000, st["ox"] + cx - st["sx"]))
            C[ky] = max(-3000, min(3000, st["oy"] + cy - st["sy"]))
            st["dragging"] = False
        live(True)

    def nudge(dx, dy):
        def f(e):
            k = 10 if e.state & 1 else 1
            C[kx] += dx * k
            C[ky] += dy * k
            live(True)
        return f

    def wheel(e):
        if ks:
            lo, hi = SIZE_LIM[ks]
            cur = C[ks]
            new = round(cur * 1.1) if e.delta > 0 else round(cur / 1.1)
            if new == cur:
                new += 1 if e.delta > 0 else -1
            C[ks] = max(lo, min(hi, new))
            live(True)

    c.bind("<Button-1>", press)
    c.bind("<B1-Motion>", drag)
    c.bind("<ButtonRelease-1>", release)
    c.bind("<Double-Button-1>", lambda e: close(True))
    c.bind("<Button-3>", lambda e: close(False))
    c.bind("<MouseWheel>", wheel)
    for key, dx, dy in (("Left", -1, 0), ("Right", 1, 0), ("Up", 0, -1), ("Down", 0, 1)):
        p.bind(f"<{key}>", nudge(dx, dy))
        p.bind(f"<Shift-{key}>", nudge(dx, dy))
    p.bind("<Return>", lambda e: close(True))
    p.bind("<Escape>", lambda e: close(False))
    bf = tk.Frame(hb, bg=PANEL)
    bf.pack(pady=8)
    tk.Button(bf, text="Done ✓", command=lambda: close(True), bg=ACC, fg="#fff").pack(side="left", padx=4)
    tk.Button(bf, text="Cancel", command=lambda: close(False)).pack(side="left", padx=4)
    hw.update_idletasks()
    hw.geometry(f"+{mx0 + mw // 2 - hw.winfo_reqwidth() // 2}+{my0 + 30}")
    for key, dx, dy in (("Left", -1, 0), ("Right", 1, 0), ("Up", 0, -1), ("Down", 0, 1)):
        hw.bind(f"<{key}>", nudge(dx, dy))
        hw.bind(f"<Shift-{key}>", nudge(dx, dy))
    hw.bind("<Return>", lambda e: close(True))
    hw.bind("<Escape>", lambda e: close(False))
    p.focus_force()
    c.focus_set()


# ---------- saved presets ----------
def names():
    try:
        return sorted(f[:-5] for f in os.listdir(PRE) if f.endswith(".json"))
    except OSError:
        return []


def current_data():
    return {k: C[k] for k in PK}


def save_named(n, data):
    json.dump(data, open(os.path.join(PRE, n + ".json"), "w", encoding="utf-8"))
    C["cur"] = n


def save_preset(*_):
    def f():
        n = ask_text("Save preset", "Preset name:")
        n = "".join(c for c in (n or "") if c.isalnum() or c in " -_").strip()
        if n:
            save_named(n, current_data())
            apply()
            toast("Saved: " + n)
    post(f)


def is_dirty():
    """Was the current preset edited without saving?"""
    n = C["cur"]
    if not n or n not in names():
        return False
    d = preset_data(n)
    return d is not None and any(d[k] != C[k] for k in PK)


def save_changes(*_):
    def f():
        if C["cur"] in names():
            save_named(C["cur"], current_data())
            apply()
            toast("Changes saved to: " + C["cur"])
    post(f)


def load_now(n, ask=True):
    d = preset_data(n)
    if d:
        lost = n != C["cur"] and is_dirty()
        if lost and ask:
            r = ask_save_discard(C["cur"])
            if r is None:
                return
            if r == "save":
                save_named(C["cur"], current_data())
                lost = False
        C.update(d)
        C["cur"] = n
        apply()
        toast(n + ("   (unsaved changes to the previous preset were discarded)" if lost else ""), 2200 if lost else 1600)


def load_nth(i):
    ns = names()
    if i < len(ns):
        load_now(ns[i])


def rename_preset(*_):
    def f():
        old = C["cur"]
        if old not in names():
            toast("Save the preset first")
            return
        n = ask_text("Rename", "New name:")
        n = "".join(c for c in (n or "") if c.isalnum() or c in " -_").strip()
        if not n or n == old:
            return
        if n in names():
            toast("A preset with that name already exists")
            return
        os.replace(os.path.join(PRE, old + ".json"), os.path.join(PRE, n + ".json"))
        C["cur"] = n
        C["gmap"] = {e: (n if v == old else v) for e, v in C["gmap"].items()}
        if C["ads"] == old:
            C["ads"] = n
        apply()
        toast(f"{old}  ->  {n}")
    post(f)


def load_preset(n):
    return lambda *_: post(lambda: load_now(n))


def step_preset(d):
    ns = names()
    if ns:
        i = ns.index(C["cur"]) if C["cur"] in ns else -1
        load_now(ns[(i + d) % len(ns)])


def delete_preset(n):
    def f():
        try:
            os.remove(os.path.join(PRE, n + ".json"))
        except OSError:
            pass
        C["gmap"] = {e: v for e, v in C["gmap"].items() if v != n}
        if C["ads"] == n:
            C["ads"] = ""
        if C["cur"] == n:
            C["cur"] = ""
        apply()
    return lambda *_: post(f)


def import_preset(*_):
    def f():
        p = filedialog.askopenfilename(parent=root, filetypes=[("Crosshair", "*.json")])
        if p:
            n = os.path.splitext(os.path.basename(p))[0]
            try:
                save_named(n, {**{k: DEF[k] for k in PK}, **clean(json.load(open(p, encoding="utf-8")))})
            except Exception:
                toast("Invalid file")
                return
            load_now(n)
    post(f)


# ---------- .reticle share format ----------
RETICLE_MAGIC = b"RETICLE1"   # 8-byte magic header

def export_reticle(path, name, data):
    """Write a .reticle file: magic + zlib-compressed JSON {name, preset}"""
    payload = json.dumps({"name": name, "preset": data}, separators=(",", ":")).encode()
    with open(path, "wb") as fh:
        fh.write(RETICLE_MAGIC)
        fh.write(zlib.compress(payload, 9))


def import_reticle_data(path):
    """Read a .reticle file → (name, preset_dict) or raise ValueError"""
    with open(path, "rb") as fh:
        raw = fh.read()
    if not raw.startswith(RETICLE_MAGIC):
        raise ValueError("not a .reticle file")
    obj = json.loads(zlib.decompress(raw[len(RETICLE_MAGIC):]))
    name = "".join(c for c in str(obj.get("name", "preset")) if c.isalnum() or c in " -_").strip() or "preset"
    preset = {**{k: DEF[k] for k in PK}, **clean(obj.get("preset", {}))}
    return name, preset


def share_preset(*_):
    """Export current preset (name + settings + embedded images) as a .reticle file"""
    def f():
        n = C["cur"]
        if not n:
            toast("Save the preset first (Presets > Save as new...)", 3000)
            return
        data = current_data()
        default = re.sub(r'[^\w \-]', '', n).strip() or "preset"
        p = filedialog.asksaveasfilename(
            parent=root,
            title="Share preset as…",
            defaultextension=".reticle",
            initialfile=default,
            filetypes=[("Reticle preset", "*.reticle")])
        if not p:
            return
        try:
            export_reticle(p, n, data)
            size_kb = os.path.getsize(p) // 1024 or 1
            toast(f"Saved: {os.path.basename(p)}  ({size_kb} KB)", 2600)
        except Exception:
            logging.exception("share_preset")
            toast("Could not save the file")
    post(f)


def open_reticle_file(path):
    """Import a .reticle file (called at startup via argv or at runtime)"""
    def f():
        try:
            n, preset = import_reticle_data(path)
        except Exception:
            toast("Invalid .reticle file")
            return
        # If a preset with the same name already exists, ask
        if n in names():
            existing = preset_data(n)
            if existing and existing != preset:
                r = ask_save_discard(f'"{n}" already exists — overwrite it?')
                if r is None:
                    return
                if r == "discard":   # user chose not to overwrite → pick new name
                    new_n = ask_text("Import preset", "Name for the imported preset:")
                    new_n = "".join(c for c in (new_n or "") if c.isalnum() or c in " -_").strip()
                    if not new_n:
                        return
                    n = new_n
        save_named(n, preset)
        load_now(n, ask=False)
        toast(f"Imported: {n}", 2200)
    post(f)


def import_reticle(*_):
    """Menu action: open file dialog to import a .reticle file"""
    def f():
        p = filedialog.askopenfilename(
            parent=root,
            title="Import .reticle preset",
            filetypes=[("Reticle preset", "*.reticle"), ("All files", "*.*")])
        if p:
            open_reticle_file(p)
    post(f)


def register_file_assoc():
    """Register .reticle extension in HKCU so double-click opens Reticle (best-effort, silent on failure)"""
    try:
        exe = sys.executable if getattr(sys, "frozen", False) else sys.executable
        cmd = f'"{exe}" "{os.path.abspath(__file__)}" "%1"'
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.reticle") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "ReticlePreset")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\ReticlePreset") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "Reticle Preset")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              r"Software\Classes\ReticlePreset\shell\open\command") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, cmd)
        # Notify Windows shell to refresh icons / associations
        try:
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
        except Exception:
            pass
    except Exception:
        logging.exception("register_file_assoc")


def copy_code(*_):
    """Picks automatically: 6 chars for the shape only, full code if there is a hand drawing or images"""
    def f():
        d = current_data()
        if d["cells"] or d["img"] or d["img2"]:
            code = enc2(d)
            msg = f"Full code copied (drawing + images) - {len(code) // 1024 + 1} KB"
        else:
            code = short_enc(d)
            msg = f"Code copied: {code}"
        root.clipboard_clear()
        root.clipboard_append(code)
        root.update()
        toast(msg, 2600)
    post(f)


def copy_short_code(*_):
    def f():
        code = short_enc(current_data())
        root.clipboard_clear()
        root.clipboard_append(code)
        root.update()
        toast(f"Shape-only code copied: {code}", 2600)
    post(f)


def paste_code(*_):
    def f():
        try:
            t = root.clipboard_get().strip()
            if t.startswith("CH2:"):
                d = {**{k: DEF[k] for k in PK}, **clean(dec2(t))}
            elif re.fullmatch(r"[0-9A-Za-z]{6}", t):
                d = {**{k: DEF[k] for k in PK}, **clean(short_dec(t))}
            else:
                d = {**{k: DEF[k] for k in PK}, **clean(dec(t))}
        except Exception:
            toast("Invalid code")
            return
        C.update(d)
        apply()
        n = ask_text("Save preset", "Name for this preset (or leave empty):")
        n = "".join(c for c in (n or "") if c.isalnum() or c in " -_").strip()
        if n:
            save_named(n, d)
            apply()
    post(f)


def listing(fn):
    def gen():
        ns = names()
        if not ns:
            return (I("No presets", lambda *_: None, enabled=False),)
        return tuple(I(n, fn(n)) for n in ns)
    return M(gen)


def ads_menu():
    return (I("None", lambda *_: post(lambda: (C.update(ads=""), apply())),
              checked=lambda i: not C["ads"], radio=True),) + tuple(
        I(n, lambda *_, n=n: post(lambda: (C.update(ads=n), apply())),
          checked=lambda i, n=n: C["ads"] == n, radio=True) for n in names())


# ---------- image ----------
def add_image(i=0):
    S = SLOTS[i]

    def go(*_):
        def f():
            p = filedialog.askopenfilename(parent=root, filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.webp")])
            if not p:
                return
            try:
                im = Image.open(p).convert("RGBA")
                im.thumbnail((512, 512), RS)
                b = io.BytesIO()
                im.save(b, "PNG")
                C[S["img"]] = base64.b64encode(b.getvalue()).decode()
            except Exception:
                toast("Could not open the image")
                return
            C[S["x"]] = C[S["y"]] = 0
            apply()
            place("img" if i == 0 else "img2")
        post(f)
    return go


def set_as_crosshair(i=0):
    """Load an image and immediately center it as the crosshair (hide built-in shape, reset offset to 0,0)"""
    S = SLOTS[i]

    def go(*_):
        def f():
            p = filedialog.askopenfilename(parent=root,
                                           title="Choose crosshair image",
                                           filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.webp")])
            if not p:
                return
            try:
                im = Image.open(p).convert("RGBA")
                im.thumbnail((512, 512), RS)
                b = io.BytesIO()
                im.save(b, "PNG")
                C[S["img"]] = base64.b64encode(b.getvalue()).decode()
            except Exception:
                toast("Could not open the image")
                return
            # Center the image, hide built-in shape so the image IS the crosshair
            C[S["x"]] = C[S["y"]] = 0
            C["show_shape"] = False
            apply()
            toast("Image set as crosshair — built-in shape hidden", 2200)
        post(f)
    return go


def remove_image(i=0):
    return lambda *_: post(lambda: (C.update({SLOTS[i]["img"]: ""}), apply()))


def add_video(*_):
    def f():
        p = filedialog.askopenfilename(parent=root, filetypes=[
            ("Video / GIF", "*.mp4 *.webm *.mkv *.avi *.mov *.m4v *.gif"), ("All", "*.*")])
        if not p:
            return
        is_gif = p.lower().endswith(".gif")
        try:
            src = Src(p)
            src.close()
        except Exception as ex:
            toast("opencv is required to play video (GIF works without it)" if str(ex) == "opencv" else "Could not open the video")
            return
        if is_gif:
            # Embed GIF as base64 so it's saved inside the preset
            try:
                with open(p, "rb") as fh:
                    raw = fh.read()
                if len(raw) > 8 * 1024 * 1024:   # 8 MB cap — large GIFs stay as path
                    toast("GIF is too large to embed (>8 MB) — stored as file path", 2600)
                    C["vid"] = p
                else:
                    C["vid"] = _vid_from_bytes(raw)
            except Exception:
                C["vid"] = p
        else:
            # Non-GIF video stays as file path (too large to embed)
            C["vid"] = p
        C["vx"], C["vy"] = 0, 0
        apply()
        place("vid")
    post(f)


def remove_video(*_):
    def f():
        C["vid"] = ""
        vid_close()
        apply()
    post(f)


# ---------- drawing editor ----------
ed = None


def open_editor():
    global ed
    if ed is not None and ed.winfo_exists():
        ed.lift()
        return
    ed = w = mk("Draw your crosshair")
    PX = 16
    mx, my = tk.BooleanVar(value=True), tk.BooleanVar(value=True)
    st = {"tool": "paint", "start": None, "last": None, "right": False}
    hist, ids, tb = [], {}, {}
    bar = tk.Frame(w)
    bar.pack(fill="x", padx=8, pady=(8, 2))
    bar2 = tk.Frame(w)
    bar2.pack(fill="x", padx=8, pady=2)
    cvs = tk.Canvas(w, bg=BG, highlightthickness=0)
    cvs.pack(padx=8, pady=4)
    tk.Label(w, text="Right-click = eraser   •   Ctrl+Z = undo", fg=MUTE).pack(pady=(0, 8))

    def bgc(x, y):
        return C["cells"].get(f"{x},{y}") or ("#1e1315" if (x + y) % 2 else "#190f11")

    def build():
        n = C["grid_n"]
        cvs.delete("all")
        ids.clear()
        cvs.config(width=n * PX, height=n * PX)
        for y in range(n):
            for x in range(n):
                ids[(x, y)] = cvs.create_rectangle(x * PX, y * PX, (x + 1) * PX, (y + 1) * PX,
                                                   outline="#2d1d20", fill=bgc(x, y))
        m = n // 2
        cvs.create_rectangle(m * PX + 1, m * PX + 1, (m + 1) * PX - 1, (m + 1) * PX - 1, outline=ACC, width=2)

    def sym(pts):
        n, s = C["grid_n"], set(pts)
        if mx.get():
            s |= {(n - 1 - a, b) for a, b in s}
        if my.get():
            s |= {(a, n - 1 - b) for a, b in s}
        return s

    def setcells(pts, erase):
        n = C["grid_n"]
        for a, b in sym(pts):
            if 0 <= a < n and 0 <= b < n:
                if erase:
                    C["cells"].pop(f"{a},{b}", None)
                else:
                    C["cells"][f"{a},{b}"] = C["paint_color"]
                cvs.itemconfig(ids[(a, b)], fill=bgc(a, b))
        draw()

    def snap():
        hist.append(dict(C["cells"]))
        del hist[:-60]

    def cell(e):
        n = C["grid_n"]
        return max(0, min(n - 1, e.x // PX)), max(0, min(n - 1, e.y // PX))

    def press(e, right):
        snap()
        x, y = cell(e)
        st.update(start=(x, y), last=(x, y), right=right)
        t = "erase" if right else st["tool"]
        if t in ("paint", "erase"):
            setcells({(x, y)}, t == "erase")
        elif t == "fill":
            setcells(flood(C["cells"], C["grid_n"], x, y), False)

    def drag(e):
        x, y = cell(e)
        t = "erase" if st["right"] else st["tool"]
        if t in ("paint", "erase") and st["last"]:
            setcells(line_pts(*st["last"], x, y), t == "erase")
            st["last"] = (x, y)
        elif t == "line" and st["start"]:
            cvs.delete("pv")
            for a, b in sym(line_pts(*st["start"], x, y)):
                cvs.create_rectangle(a * PX, b * PX, (a + 1) * PX, (b + 1) * PX, fill=C["paint_color"],
                                     outline="", tags="pv")

    def release(e):
        x, y = cell(e)
        if st["tool"] == "line" and not st["right"] and st["start"]:
            cvs.delete("pv")
            setcells(line_pts(*st["start"], x, y), False)
        st["start"] = st["last"] = None
        apply()

    def undo(*_):
        if hist:
            C["cells"] = hist.pop()
            build()
            apply()

    def settool(t):
        st["tool"] = t
        for k, b in tb.items():
            b.config(bg=ACC if k == t else BTN)

    def pick():
        c = pick_color(C["paint_color"])
        if c:
            C["paint_color"] = c
            cb.config(bg=c, fg="#000" if sum(int(c[i:i + 2], 16) for i in (1, 3, 5)) > 380 else "#fff")

    def clear():
        snap()
        C["cells"] = {}
        build()
        apply()

    def resize():
        C["grid_n"] = int(sp.get())
        C["cells"] = {}
        hist.clear()
        build()
        apply()

    for k, txt in (("paint", "Paint"), ("erase", "Erase"), ("line", "Line"), ("fill", "Fill")):
        tb[k] = tk.Button(bar, text=txt, command=lambda k=k: settool(k))
        tb[k].pack(side="left", padx=2)
    cb = tk.Button(bar2, text="Color", bg=C["paint_color"], command=pick)
    cb.pack(side="left", padx=2)
    tk.Button(bar2, text="Undo", command=undo).pack(side="left", padx=2)
    tk.Button(bar2, text="Clear all", command=clear).pack(side="left", padx=2)
    tk.Checkbutton(bar2, text="Mirror H", variable=mx).pack(side="left")
    tk.Checkbutton(bar2, text="Mirror V", variable=my).pack(side="left")
    sp = tk.Spinbox(bar2, values=(11, 15, 21, 31, 41), width=3, command=resize)
    sp.delete(0, "end")
    sp.insert(0, C["grid_n"])
    sp.pack(side="right")
    tk.Label(bar2, text="Grid").pack(side="right")
    cvs.bind("<Button-1>", lambda e: press(e, False))
    cvs.bind("<Button-3>", lambda e: press(e, True))
    cvs.bind("<B1-Motion>", drag)
    cvs.bind("<B3-Motion>", drag)
    cvs.bind("<ButtonRelease-1>", release)
    cvs.bind("<ButtonRelease-3>", release)
    w.bind("<Control-z>", undo)
    settool("paint")
    build()


# ---------- rest of the menu ----------
def setv(k, v):
    return lambda *_: post(lambda: (C.update({k: v}), apply()))


def flip(k):
    return lambda *_: post(lambda: (C.update({k: not C[k]}), apply()))


def flip_img(k):
    return lambda *_: post(lambda: (C.update({k: 0 if C[k] else 1}), apply()))



# ---------- display resolution ----------
class DEVMODEW(ctypes.Structure):
    _fields_ = [("dmDeviceName", wt.WCHAR * 32), ("dmSpecVersion", wt.WORD), ("dmDriverVersion", wt.WORD),
                ("dmSize", wt.WORD), ("dmDriverExtra", wt.WORD), ("dmFields", wt.DWORD),
                ("dmPositionX", ctypes.c_long), ("dmPositionY", ctypes.c_long),
                ("dmDisplayOrientation", wt.DWORD), ("dmDisplayFixedOutput", wt.DWORD),
                ("dmColor", ctypes.c_short), ("dmDuplex", ctypes.c_short), ("dmYResolution", ctypes.c_short),
                ("dmTTOption", ctypes.c_short), ("dmCollate", ctypes.c_short), ("dmFormName", wt.WCHAR * 32),
                ("dmLogPixels", wt.WORD), ("dmBitsPerPel", wt.DWORD), ("dmPelsWidth", wt.DWORD),
                ("dmPelsHeight", wt.DWORD), ("dmDisplayFlags", wt.DWORD), ("dmDisplayFrequency", wt.DWORD),
                ("dmICMMethod", wt.DWORD), ("dmICMIntent", wt.DWORD), ("dmMediaType", wt.DWORD),
                ("dmDitherType", wt.DWORD), ("dmReserved1", wt.DWORD), ("dmReserved2", wt.DWORD),
                ("dmPanningWidth", wt.DWORD), ("dmPanningHeight", wt.DWORD)]


_UM.EnumDisplaySettingsW.argtypes = [wt.LPCWSTR, wt.DWORD, ctypes.POINTER(DEVMODEW)]
_UM.EnumDisplaySettingsW.restype = wt.BOOL
_UM.EnumDisplaySettingsExW.argtypes = [wt.LPCWSTR, wt.DWORD, ctypes.POINTER(DEVMODEW), wt.DWORD]
_UM.EnumDisplaySettingsExW.restype = wt.BOOL
_UM.ChangeDisplaySettingsExW.argtypes = [wt.LPCWSTR, ctypes.POINTER(DEVMODEW), ctypes.c_void_p, wt.DWORD, ctypes.c_void_p]
_UM.ChangeDisplaySettingsExW.restype = ctypes.c_long
CDS_ERR = {1: "Windows needs a restart for that mode", -1: "The display driver refused the change",
           -2: "That resolution is not supported by this monitor / graphics driver", -3: "Could not write the setting",
           -4: "Bad flags", -5: "Bad parameters", -6: "Not possible in this multi-monitor setup"}
RES_ORIG = {}          # device -> (w, h, hz) it had before Reticle changed it
RES_BY_GAME = [False]  # the current change came from a per-game link
GAME_LEAVE = [0.0]


def dev_name():
    mons()
    n = min(C["mon"], len(MON_DEV[0]) - 1)
    return MON_DEV[0][n]


def cur_mode(dev):
    dm = DEVMODEW()
    dm.dmSize = ctypes.sizeof(DEVMODEW)
    if not _UM.EnumDisplaySettingsW(dev or None, 0xFFFFFFFF, ctypes.byref(dm)):
        return None
    return dm.dmPelsWidth, dm.dmPelsHeight, dm.dmDisplayFrequency


def _enum(dev, raw=False):
    """Every DEVMODE the driver offers. raw=True also returns modes the monitor does not report (EDS_RAWMODE)."""
    out, i = [], 0
    while i < 6000:
        dm = DEVMODEW()
        dm.dmSize = ctypes.sizeof(DEVMODEW)
        if not _UM.EnumDisplaySettingsExW(dev or None, i, ctypes.byref(dm), 2 if raw else 0):
            break
        i += 1
        if dm.dmBitsPerPel >= 24 and dm.dmPelsWidth >= 640:
            out.append(dm)
    return out


def mode_list(dev, raw=False):
    """(w, h, hz) the monitor / driver offers, biggest first. raw=True: ONLY the extra driver-reported modes."""
    base = {(d.dmPelsWidth, d.dmPelsHeight, d.dmDisplayFrequency) for d in _enum(dev)}
    if raw:
        base = {(d.dmPelsWidth, d.dmPelsHeight, d.dmDisplayFrequency) for d in _enum(dev, True)} - base
    return sorted(base, key=lambda m: (-m[0] * m[1], -m[0], -m[2]))


def _pick(dms, w, h, hz, cur_hz):
    c = [d for d in dms if d.dmPelsWidth == w and d.dmPelsHeight == h]
    if hz:
        c = [d for d in c if d.dmDisplayFrequency == hz]
    if not c:
        return None
    same = [d for d in c if d.dmDisplayFrequency == cur_hz]     # keep the refresh rate when possible
    return same[0] if same and not hz else max(c, key=lambda d: d.dmDisplayFrequency)


def _near_sizes(dev, w, h):
    """a few supported sizes closest to the one that failed (same shape first)"""
    sizes = sorted({(d.dmPelsWidth, d.dmPelsHeight) for d in _enum(dev)})
    sizes.sort(key=lambda m: (abs(m[0] / m[1] - w / h) > .05, abs(m[0] * m[1] - w * h)))
    return ", ".join(f"{a}×{b}" for a, b in sizes[:6])


def set_mode(dev, w, h, hz=None, test=False):
    """Returns (ok, message). With test=True nothing is changed, it only checks the mode is accepted.
    Order: a mode the monitor reports -> a driver-only mode (unsafe flag) -> GPU-stretched copy of the current mode."""
    cur = DEVMODEW()
    cur.dmSize = ctypes.sizeof(DEVMODEW)
    if not _UM.EnumDisplaySettingsW(dev or None, 0xFFFFFFFF, ctypes.byref(cur)):
        return False, "Could not read the current display mode"
    base = 0x2 if test else 0
    rc = -2

    def go(dm, flags):
        dm.dmPositionX, dm.dmPositionY = cur.dmPositionX, cur.dmPositionY   # never move the monitor
        dm.dmFields |= 0x20                                                   # DM_POSITION
        return _UM.ChangeDisplaySettingsExW(dev or None, ctypes.byref(dm), None, flags | base, None)
    for raw in (False, True):
        dm = _pick(_enum(dev, raw), w, h, hz, cur.dmDisplayFrequency)
        if dm is None:
            continue
        rc = go(dm, 0x100 if raw else 0)             # 0x100 = CDS_ENABLE_UNSAFE_MODES
        if rc == 0:
            return True, ""
        logging.warning("mode %sx%s@%s raw=%s -> rc %s", w, h, hz, raw, rc)
    st = DEVMODEW()                                  # last resort: current mode + new size, stretched by the GPU
    ctypes.memmove(ctypes.byref(st), ctypes.byref(cur), ctypes.sizeof(DEVMODEW))
    st.dmPelsWidth, st.dmPelsHeight = w, h
    st.dmFields |= 0x80000 | 0x100000 | 0x20000000    # PELSWIDTH | PELSHEIGHT | DISPLAYFIXEDOUTPUT
    st.dmDisplayFixedOutput = 1                       # DMDFO_STRETCH
    if hz:
        st.dmDisplayFrequency = hz
        st.dmFields |= 0x400000
    rc2 = go(st, 0x100)
    if rc2 == 0:
        return True, ""
    logging.warning("mode %sx%s stretched -> rc %s", w, h, rc2)
    msg = CDS_ERR.get(rc if rc != -2 else rc2, f"Windows error {rc2}")
    if rc in (-2, -1) or rc2 in (-2, -1):
        msg += f"\nSupported sizes near it: {_near_sizes(dev, w, h)}"
    return False, msg


def cur_text():
    m = cur_mode(dev_name())
    return res_text(*m) if m else "unknown"


def _swap_offsets(old, new):
    """Remember the crosshair offset per resolution; a resolution seen for the first time starts centered"""
    C["res_off"][f"{old[0]}x{old[1]}"] = [C["dx"], C["dy"]]
    o = C["res_off"].get(f"{new[0]}x{new[1]}") or [0, 0]
    C["dx"], C["dy"] = o


def screen_refresh():
    """Re-read monitors and re-place every overlay window (they can end up anywhere after a mode switch)"""
    try:
        mons(True)
        LA.clear()
        draw()
        keep_top()
    except Exception:
        logging.exception("screen_refresh")


def change_res(w, h, hz=None, by_game=False):
    """Switch the selected monitor. Returns the previous (w, h, hz) on success, else None."""
    dev, old = dev_name(), None
    old = cur_mode(dev)
    if not old:
        toast("Could not read the current resolution", 3000)
        return None
    ok, msg = set_mode(dev, w, h, hz)
    if not ok:
        toast("Resolution not changed: " + msg, 7000)
        return None
    new = cur_mode(dev) or (w, h, hz or old[2])
    if dev not in RES_ORIG:
        RES_ORIG[dev] = old
        C["res_orig"][dev] = list(old)
    if tuple(new) == tuple(RES_ORIG[dev]):
        RES_ORIG.pop(dev, None)
        C["res_orig"].pop(dev, None)
        C["res_set"].pop(dev, None)
    else:
        C["res_set"][dev] = list(new)
    RES_BY_GAME[0] = by_game
    _swap_offsets(old, new)
    save()
    screen_refresh()
    root.after(700, screen_refresh)     # the desktop settles a moment after the switch
    root.after(2200, screen_refresh)
    return old


def restore_res(final=False):
    """Put every monitor we changed back to its original resolution"""
    for dev, o in list(RES_ORIG.items()):
        cur = cur_mode(dev)
        ok, _m = set_mode(dev, *o)
        if ok:
            if cur:
                _swap_offsets(cur, o)
            RES_ORIG.pop(dev, None)
            C["res_orig"].pop(dev, None)
            C["res_set"].pop(dev, None)
    RES_BY_GAME[0] = False
    try:
        save()
        if not final:
            screen_refresh()
            root.after(700, screen_refresh)
            toast("Original resolution restored" if not RES_ORIG else "Could not restore every monitor", 2500)
    except Exception:
        logging.exception("restore_res")


def recover_res():
    """After a crash / kill: if the screen is still in the mode we set, put the original back"""
    for dev, o in list(C["res_orig"].items()):
        cur, s_ = cur_mode(dev), C["res_set"].get(dev)
        if cur and s_ and tuple(s_) == tuple(cur) and tuple(o) != tuple(cur):
            ok, _m = set_mode(dev, *o)
            if ok:
                _swap_offsets(cur, o)
                toast("Restored your resolution (the last session ended unexpectedly)", 3500)
        C["res_orig"].pop(dev, None)
        C["res_set"].pop(dev, None)
    save()


atexit.register(lambda: restore_res(final=True))


def confirm_keep(old, secs=10):
    """Like Windows: keep the new resolution or it goes back by itself (protects from a black screen)"""
    d = mk("Keep this resolution?")
    d.resizable(False, False)
    st = {"n": secs, "keep": False}
    lab = tk.Label(d, text="", justify="center")
    lab.pack(padx=24, pady=(18, 8))

    def tick():
        if not d.winfo_exists():
            return
        if st["n"] <= 0:
            d.destroy()
            return
        lab.config(text=f"Keep {cur_text()}?\nGoing back to {res_text(*old)} in {st['n']} s")
        st["n"] -= 1
        d.after(1000, tick)

    def keep():
        st["keep"] = True
        d.destroy()
    b = tk.Frame(d)
    b.pack(pady=(4, 16))
    tk.Button(b, text="Keep", command=keep, bg=ACC, fg="#fff", width=10).pack(side="left", padx=4)
    tk.Button(b, text="Go back", command=d.destroy, width=10).pack(side="left", padx=4)
    d.bind("<Escape>", lambda _e: d.destroy())
    tick()
    d.update_idletasks()
    x, y, w_, h_ = mon_rect()
    d.geometry(f"+{x + w_ // 2 - d.winfo_reqwidth() // 2}+{y + h_ // 2 - d.winfo_reqheight() // 2}")
    d.grab_set()
    d.focus_force()
    d.wait_window()
    return st["keep"]


def set_res_ui(w, h, hz=None, confirm=True):
    """Manual change from a menu / the settings window"""
    cur = cur_mode(dev_name())
    if cur and (w, h) == tuple(cur[:2]) and (hz is None or hz == cur[2]):
        toast("Already at " + res_text(*cur))
        return True
    old = change_res(w, h, hz)
    if old is None:
        return False
    if confirm and not confirm_keep(old):
        change_res(*old)
        toast("Went back to " + res_text(*old), 2500)
        return False
    toast("Resolution: " + cur_text(), 2000)
    return True


def res_prompt(done=None):
    cur = cur_mode(dev_name())
    t = ask_text("Set resolution", "Type width x height   (optional @Hz)\ne.g.  1280x960   or   1920x1080@144",
                 res_key(*cur[:2]) if cur else "")
    if t is None:
        return
    p = parse_res(t)
    if not p:
        toast("Type it like 1280x960", 2500)
        return
    set_res_ui(*p)
    if done:
        done()


def res_for(p):
    """resolution string linked to the running exe: exact full path first, then a bare-name link"""
    v = C["gres"].get(p)
    if v:
        return v
    for k, v in C["gres"].items():
        if same_exe(p, k):
            return v
    return None


def game_res(e):
    """Called when a different program comes to the front"""
    r_ = res_for(e)
    p = parse_res(r_) if r_ else None
    if p:
        GAME_LEAVE[0] = 0.0
        cur = cur_mode(dev_name())
        if cur and tuple(cur[:2]) == p[:2] and (not p[2] or p[2] == cur[2]):
            return
        if change_res(p[0], p[1], p[2], by_game=True):
            toast(f"{os.path.basename(e)}: {res_text(*p[:2])}", 2200)
    elif C["res_revert"] and RES_BY_GAME[0] and RES_ORIG:
        GAME_LEAVE[0] = time.time()


def pick_exe(kind, cb):
    """kind: 'open' (switch to the game window) | 'file' (file dialog) | 'type'. Calls cb(exe_key)."""
    if kind == "open":
        toast("Switch to the game window now (4 seconds)", 3500)

        def grab():
            e = fg_exe()
            if e and not is_own(e):
                cb(e)
            else:
                toast("Could not detect the window, try again")
        root.after(4000, grab)
        return
    if kind == "file":
        p = filedialog.askopenfilename(parent=root, title="Choose the game's .exe file",
                                       filetypes=[("Game executable", "*.exe"), ("All files", "*.*")])
        e = os.path.normcase(os.path.normpath(p)) if p else ""
    else:
        e = (ask_text("Link to game", "Full path to the game .exe\n(or just a name like valorant.exe to match any folder):") or "").strip().strip('"')
        e = os.path.normcase(os.path.normpath(e)) if has_sep(e) else e.lower()
    if not e:
        return
    if not re.fullmatch(r"[\w .()-]{1,60}\.exe", os.path.basename(e)):
        toast("Enter a full path or a name ending in .exe")
        return
    cb(e)


def link_game_res(kind, done=None):
    def f():
        def got(e):
            cur = cur_mode(dev_name())
            t = ask_text("Game resolution", f"Resolution to use for {os.path.basename(e)}\n(e.g. 1280x960  or  1920x1080@144):",
                         C["gres"].get(e) or (res_key(*cur[:2]) if cur else ""))
            if t is None:
                return
            p = parse_res(t)
            if not p:
                toast("Type it like 1280x960", 2500)
                return
            C["gres"][e] = res_key(*p)
            apply()
            toast(f"{os.path.basename(e)}  ->  {res_text(*p)}", 2500)
            if done:
                done()
        pick_exe(kind, got)
    post(f)


def gres_menu():
    if not C["gres"]:
        return (I("No game resolutions yet", lambda *_: None, enabled=False),)
    return tuple(I(f"{e if has_sep(e) else e + '  (any folder)'}  ->  {parse_res(v) and res_text(*parse_res(v))}   (click to remove)",
                   lambda *_, e=e: post(lambda: (C["gres"].pop(e, None), apply())))
                 for e, v in sorted(C["gres"].items()))


def res_modes_menu():
    def gen():
        dev = dev_name()
        seen = []
        for w, h, _hz in mode_list(dev) + mode_list(dev, True):
            if (w, h) not in seen:
                seen.append((w, h))
        if not seen:
            return (I("No modes found", lambda *_: None, enabled=False),)
        std = {(m[0], m[1]) for m in mode_list(dev)}
        return tuple(I(res_text(w, h) + ("" if (w, h) in std else "  *"), lambda *_, w=w, h=h: post(lambda: set_res_ui(w, h)),
                       checked=lambda i, w=w, h=h: (cur_mode(dev_name()) or (0, 0))[:2] == (w, h), radio=True)
                     for w, h in seen)
    return M(gen)


def res_hz_menu():
    def gen():
        dev = dev_name()
        cur = cur_mode(dev)
        hzs = sorted({m[2] for m in mode_list(dev) if cur and m[:2] == tuple(cur[:2])}, reverse=True)
        if not hzs:
            return (I("-", lambda *_: None, enabled=False),)
        return tuple(I(f"{hz} Hz", lambda *_, hz=hz: post(lambda: set_res_ui(cur[0], cur[1], hz, confirm=False)),
                       checked=lambda i, hz=hz: (cur_mode(dev_name()) or (0, 0, 0))[2] == hz, radio=True) for hz in hzs)
    return M(gen)


res_menu = M(
    I(lambda i: "Now: " + cur_text() + f"   (monitor {C['mon'] + 1})", lambda *_: None, enabled=False),
    I("Set resolution... (type it)", lambda *_: post(res_prompt)),
    I("Supported resolutions", res_modes_menu()),
    I("Refresh rate", res_hz_menu()),
    I(lambda i: "Restore original (" + (res_text(*RES_ORIG[dev_name()]) if dev_name() in RES_ORIG else "") + ")",
      lambda *_: post(restore_res), visible=lambda i: dev_name() in RES_ORIG),
    M.SEPARATOR,
    I("Per-game resolution", M(
        I("Link to an open game...", lambda *_: link_game_res("open")),
        I("Link by choosing the game file (.exe)...", lambda *_: link_game_res("file")),
        I("Link by typing the path or name (exe)...", lambda *_: link_game_res("type")),
        M.SEPARATOR,
        I("Linked games", M(gres_menu)),
    )),
    I("Go back when I leave the game", flip("res_revert"), checked=lambda i: C["res_revert"]),
)


def screen_preview(on):
    """Hover preview: dim the screen and show the REAL crosshair at its real size and place"""
    try:
        _screen_preview(on)
    except Exception:
        logging.exception("screen_preview")
        PREVIEW[0] = False


def _screen_preview(on):
    if on and PVW[0] is None:
        x, y, w_, h_ = mon_rect()
        b = tk.Toplevel(root)
        b.overrideredirect(True)
        b.attributes("-topmost", True)
        b.attributes("-alpha", 0.62)
        b.configure(bg="#000")
        b.geometry(f"{w_}x{h_}+{x}+{y}")
        c = tk.Canvas(b, bg="#000", highlightthickness=0)
        c.pack(fill="both", expand=True)
        cx, cy = w_ // 2, h_ // 2
        c.create_line(cx, 0, cx, h_, fill="#4a1018")
        c.create_line(0, cy, w_, cy, fill="#4a1018")
        c.create_text(cx, 36, fill="#d9b4b8", font=("Segoe UI", 14),
                      text=f"Screen preview   {w_}×{h_}   (real size, centre = crosshair origin)")
        clickthrough(b)
        PVW[0] = b
        PREVIEW[0] = True
        draw()
        keep_top()
    elif not on and PVW[0] is not None:
        try:
            PVW[0].destroy()
        except Exception:
            pass
        PVW[0] = None
        PREVIEW[0] = False
        draw()


PVW = [None]


U32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]


def to_top(win):
    """Raise one of our windows above the overlay windows"""
    try:
        h = U32.GetParent(win.winfo_id()) or win.winfo_id()
        U32.SetWindowPos(h, ctypes.c_void_p(-1), 0, 0, 0, 0, 0x13)
    except Exception:
        pass


def keep_top():
    """Re-assert always-on-top for our overlay windows (games / the move overlay can push them down)"""
    for win in (root, imgw, imgw2, vidw):
        try:
            if win.state() == "normal":
                h = U32.GetParent(win.winfo_id()) or win.winfo_id()
                U32.SetWindowPos(h, ctypes.c_void_p(-1), 0, 0, 0, 0, 0x13)   # TOPMOST | NOMOVE | NOSIZE | NOACTIVATE
        except Exception:
            pass


def splash(text="RETICLE", hold=1600):
    """Program name in dark red, centered on the screen, fades out by itself"""
    try:
        t = tk.Toplevel(root)
        t.overrideredirect(True)
        t.attributes("-topmost", True)
        t.config(bg=KEY)
        t.attributes("-transparentcolor", KEY)
        tk.Label(t, text=text, font=("Segoe UI", 72, "bold"), fg="#8b0f1f", bg=KEY).pack(padx=10, pady=10)
        t.update_idletasks()
        x, y, w, h = mon_rect()
        t.geometry(f"+{x + w // 2 - t.winfo_width() // 2}+{y + h // 2 - t.winfo_height() // 2}")
        clickthrough(t)

        def fade(a=1.0):
            try:
                if a <= 0:
                    t.destroy()
                    return
                t.attributes("-alpha", a)
                t.after(30, lambda: fade(a - .06))
            except Exception:
                pass
        t.after(hold, fade)
    except Exception:
        logging.exception("splash")


def _toggle():
    C.update(visible=not C["visible"])
    apply()
    if C["visible"] and gate() and not BOUND[0]:
        toast("Crosshair is ON but hidden: the linked game is not the active window", 3500)


def toggle(*_):
    post(_toggle)


def copy_discord(*_):
    def f():
        root.clipboard_clear()
        root.clipboard_append("fs.d")
        root.update()
        toast("Discord copied: fs.d")
    post(f)


def custom_color(k="color"):
    def f(*_):
        def g():
            c = pick_color(C[k] or C["color"])
            if c:
                C[k] = c
                apply()
        post(g)
    return f


def paste_color(k):
    def f(*_):
        def g():
            c = clip_color()
            if not c:
                t = ask_text("Paste color", "Type or paste a color code (#ff8800 or 255,136,0)")
                c = parse_color(t or "")
            if c:
                C[k] = c
                apply()
            elif t is not None:
                toast("Color code not recognized")
        post(g)
    return f


def my_colors_menu(k):
    def gen():
        if not C["my_colors"]:
            return (I("No saved colors yet (use \"Custom color\")", lambda *_: None, enabled=False),)
        return tuple(I(c, setv(k, c), checked=lambda i, c=c: C[k] == c, radio=True) for c in C["my_colors"])
    return M(gen)


def color_menu(k, empty=None, extra=()):
    items = []
    if empty:
        items.append(I(empty, setv(k, ""), checked=lambda i: not C[k], radio=True))
    items += [I(n, setv(k, v), checked=lambda i, v=v: C[k] == v, radio=True) for n, v in extra]
    items += [I(n, setv(k, v), checked=lambda i, v=v: C[k] == v, radio=True) for n, v in MENU_COLORS]
    return M(*items, M.SEPARATOR, I("Saved colors", my_colors_menu(k)),
             I("Custom color (any color)...", custom_color(k)),
             I("Paste color code from clipboard", paste_color(k)))


def radio(k, values, fmt=str):
    return M(*[I(fmt(v), setv(k, v), checked=lambda i, k=k, v=v: C[k] == v, radio=True) for v in values])


def bind_game(*_):
    def f():
        toast("Switch to the game window now (4 seconds)", 3500)

        def grab():
            e = fg_exe()
            if e and not is_own(e):
                C["bind"] = e
                BOUND[0] = True
                apply()
                toast("Bound to " + e, 3000)
            else:
                toast("Could not detect the window, try again")
        root.after(4000, grab)
    post(f)


def map_game(*_):
    def f():
        n = C["cur"]
        if n not in names():
            toast("Save the preset first (Presets > Save as new...)", 3000)
            return
        toast(f"Switch to the game window now (4 seconds) - preset: {n}", 3500)

        def grab():
            e = fg_exe()
            if e and not is_own(e):
                C["gmap"][e] = n
                apply()
                toast(f"{e}  <-  {n}")
            else:
                toast("Could not detect the window, try again")
        root.after(4000, grab)
    post(f)


def map_game_manual(*_):
    def f():
        n = C["cur"]
        if n not in names():
            toast("Save the preset first (Presets > Save as new...)", 3000)
            return
        e = (ask_text("Link to game", "Full path to the game .exe\n(or just a name like valorant.exe to match any folder):") or "").strip().strip('"')
        e = os.path.normcase(os.path.normpath(e)) if has_sep(e) else e.lower()
        if not re.fullmatch(r"[\w .()-]{1,60}\.exe", os.path.basename(e)):
            toast("Enter a full path or a name ending in .exe")
            return
        C["gmap"][e] = n
        apply()
        toast(f"{e}  <-  {n}")
    post(f)


def map_game_file(*_):
    def f():
        n = C["cur"]
        if n not in names():
            toast("Save the preset first (Presets > Save as new...)", 3000)
            return
        p = filedialog.askopenfilename(parent=root, title="Choose the game's .exe file",
                                       filetypes=[("Game executable", "*.exe"), ("All files", "*.*")])
        if not p:
            return
        e = os.path.normcase(os.path.normpath(p))
        if not re.fullmatch(r"[\w .()-]{1,60}\.exe", os.path.basename(e)):
            toast("Please choose an .exe file")
            return
        C["gmap"][e] = n
        apply()
        toast(f"{os.path.basename(e)}  <-  {n}\n{e}", 3500)
    post(f)


def gmap_menu():
    if not C["gmap"]:
        return (I("No links", lambda *_: None, enabled=False),)
    return tuple(I(f"{e if has_sep(e) else e + '  (any folder)'}  ←  {n}   (click to remove)", lambda *_, e=e: post(lambda: (C["gmap"].pop(e, None), apply())))
                 for e, n in sorted(C["gmap"].items()))


UPD = {"info": None, "busy": False}


def _ver(x):
    return tuple(int(p) for p in x.split("."))


def check_update(manual=False):
    """Asks GitHub for the latest Release (background thread). If it is newer, an "Update available" item shows up"""
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", GITHUB_REPO):
        if manual:
            post(lambda: toast("GITHUB_REPO is not set in crosshair.py", 3000))
        return

    def work():
        try:
            req = urllib.request.Request(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                                         headers={"User-Agent": "Reticle/" + VERSION})
            with urllib.request.urlopen(req, timeout=8) as r:
                m = json.loads(r.read(500000).decode("utf-8"))
            v = str(m.get("tag_name", "")).lstrip("vV")
            if not re.fullmatch(r"\d+(\.\d+){0,3}", v):
                raise ValueError("tag")
            assets = [x for x in m.get("assets", []) if str(x.get("name", "")).lower().endswith(".exe")]
            if not assets:
                raise ValueError("no exe")
            a = next((x for x in assets if x["name"].lower() == "reticle.exe"), assets[0])
            u = a.get("browser_download_url", "")
            if not u.startswith(f"https://github.com/{GITHUB_REPO}/"):
                raise ValueError("url")
            d = str(a.get("digest") or "").lower().replace("sha256:", "")
            h = d if re.fullmatch(r"[0-9a-f]{64}", d) else ""
            notes = str(m.get("body") or "")[:400]
        except Exception:
            logging.exception("update check")
            if manual:
                post(lambda: toast("Could not check for updates (no internet, or no Release yet)", 3000))
            return
        if _ver(v) > _ver(VERSION):
            def show():
                new = not UPD["info"] or UPD["info"]["version"] != v
                UPD["info"] = dict(version=v, url=u, sha256=h, notes=notes)
                icon.update_menu()
                if new or manual:
                    toast(f"Update {v} available - open the tray menu and click the update item", 4000)
            post(show)
        elif manual:
            post(lambda: toast(f"You are on the latest version ({VERSION})", 2500))
    threading.Thread(target=work, daemon=True).start()


def _download_and_swap(i):
    exe = sys.executable
    new, bat = exe + ".new", exe + ".update.bat"
    try:
        h = hashlib.sha256()
        req = urllib.request.Request(i["url"], headers={"User-Agent": "Reticle/" + VERSION})
        n = 0
        with urllib.request.urlopen(req, timeout=30) as r, open(new, "wb") as f:
            while True:
                b = r.read(1 << 16)
                if not b:
                    break
                n += len(b)
                if n > 300000000:
                    raise ValueError("too big")
                h.update(b)
                f.write(b)
        if i["sha256"] and h.hexdigest() != i["sha256"]:
            raise ValueError("hash mismatch")
        with open(bat, "w", encoding="utf-8") as f:
            f.write("@echo off\r\nchcp 65001 >nul\r\nset /a n=0\r\n:retry\r\nset /a n+=1\r\n"
                    "if %n% gtr 40 exit /b 1\r\nping 127.0.0.1 -n 2 >nul\r\n"
                    f'move /y "{new}" "{exe}" >nul 2>&1\r\nif errorlevel 1 goto retry\r\n'
                    f'start "" "{exe}"\r\n(goto) 2>nul & del "%~f0"\r\n')
        env = {k: v for k, v in os.environ.items() if k != "_MEIPASS2"}
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        subprocess.Popen(["cmd", "/c", bat], env=env, creationflags=0x08000000, close_fds=True)
        post(lambda: (restore_res(final=True), icon.stop(), root.destroy()))
    except Exception:
        logging.exception("update install")
        try:
            os.remove(new)
        except OSError:
            pass
        UPD["busy"] = False
        post(lambda: toast("Update failed (internet or file permissions). Try again", 3500))


def install_update(*_):
    def f():
        i = UPD["info"]
        if not i or UPD["busy"]:
            return
        if not getattr(sys, "frozen", False):
            webbrowser.open(i["url"])  # running from .py: download by hand
            return
        if not ask_yes_no("Update Reticle", f"Update to version {i['version']}?\n\n{i['notes']}\n\n"
                          "Reticle will close and start again by itself.", "Update"):
            return
        UPD["busy"] = True
        toast("Downloading the update...", 3000)
        threading.Thread(target=_download_and_swap, args=(i,), daemon=True).start()
    post(f)


def upd_loop():
    if C["autoupd"]:
        check_update()
    root.after(6 * 3600 * 1000, upd_loop)


def autostart_on():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as k:
            winreg.QueryValueEx(k, "Crosshair")
            return True
    except OSError:
        return False


def toggle_autostart(*_):
    cmd = (f'"{sys.executable}"' if getattr(sys, "frozen", False) else
           f'"{sys.executable.replace("python.exe", "pythonw.exe")}" "{os.path.abspath(__file__)}"')
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run",
                            0, winreg.KEY_SET_VALUE) as k:
            if autostart_on():
                winreg.DeleteValue(k, "Crosshair")
            else:
                winreg.SetValueEx(k, "Crosshair", 0, winreg.REG_SZ, cmd)
    except OSError:
        pass
    icon.update_menu()


def move(dx, dy):
    def f():
        C["dx"] += dx
        C["dy"] += dy
        draw()
        save_soon()
    post(f)


def image_menu(i):
    S = SLOTS[i]
    vis = lambda _i: bool(C[S["img"]])
    return M(
        I("Add image...", add_image(i)),
        I("★ Set image as crosshair (centered, hide shape)", set_as_crosshair(i)),
        I("Move image (drag)", lambda *_: post(lambda: place("img" if i == 0 else "img2")), visible=vis),
        I("Image size", radio(S["size"], (16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512)), visible=vis),
        I("Image opacity", radio(S["op"], (20, 40, 60, 80, 100), lambda v: f"{v}%"), visible=vis),
        I("Image rotation", radio(S["rot"], (0, 90, 180, 270), lambda v: f"{v}°"), visible=vis),
        I("Flip horizontal ↔ (left/right)", flip_img(S["fh"]), checked=lambda i: bool(C[S["fh"]]), visible=vis),
        I("Flip vertical ↕ (up/down)", flip_img(S["fv"]), checked=lambda i: bool(C[S["fv"]]), visible=vis),
        I("Image color", color_menu(S["tint"], "Original", (("Black & white", "gray"),)), visible=vis),
        I("Remove image", remove_image(i), visible=vis),
    )


def presets_items():
    """Top of the menu: saved presets directly (click one to load it)"""
    ns = names()
    if not ns:
        out = [I("No saved presets", lambda *_: None, enabled=False)]
    elif len(ns) <= 8:
        out = [I(f"{j + 1}. {n}" if j < 9 else n, load_preset(n), checked=lambda i, n=n: C["cur"] == n, radio=True)
               for j, n in enumerate(ns)]
    else:
        out = [I("Load preset", listing(load_preset))]
    return tuple(out) + (
        M.SEPARATOR,
        I("Save as new...", save_preset),
        I("Share preset (.reticle)...", share_preset),
        I("Import .reticle preset...", import_reticle),
        M.SEPARATOR,
        I("More", M(
            I("Copy preset code", copy_code),
            I("Paste preset code", paste_code),
            I("Copy 6-char code (shape only)", copy_short_code),
            M.SEPARATOR,
            I("Rename current preset...", rename_preset),
            I("Import from JSON file...", import_preset),
            I("Open presets folder", lambda *_: os.startfile(PRE)),
            I("Delete preset", listing(delete_preset)),
        )),
    )


cross_menu = M(
    I("Shape", M(*[I(n, setv("shape", v), checked=lambda i, v=v: C["shape"] == v, radio=True) for n, v in SHAPES])),
    I("Colors", M(
        I("Shape color", color_menu("color")),
        I("Outline color", color_menu("outline_color")),
        I("Dot color", color_menu("dot_color", "Same as shape")),
        M.SEPARATOR,
        I("Adapt shape color to the background", flip("adapt"), checked=lambda i: C["adapt"]),
    )),
    I("Dimensions", M(
        I("Length", radio("length", range(2, 61, 2))),
        I("Thickness", radio("thick", range(1, 13))),
        I("Gap", radio("gap", range(0, 41, 2))),
        I("Outline", radio("outline", range(0, 7))),
        I("Rotation", radio("rot", (0, 15, 30, 45, 60, 75, 90, 135, 180, 225, 270, 315), lambda v: f"{v}°")),
        I("Opacity", radio("opacity", [.1, .2, .3, .5, .7, .85, 1.0], lambda v: f"{int(v * 100)}%")),
    )),
    I("Dot", M(
        I("Center dot", flip("dot"), checked=lambda i: C["dot"]),
        I("Dot size", radio("dot_size", range(1, 13))),
    )),
    M.SEPARATOR,
    I("Show built-in shape", flip("show_shape"), checked=lambda i: C["show_shape"]),
)

media_menu = M(
    I("Image 1", image_menu(0)),
    I("Image 2", image_menu(1)),
    I("Video / GIF", M(
        I("Choose video / GIF...", add_video),
        I("Move video (drag)", lambda *_: post(lambda: place("vid")), visible=lambda i: bool(C["vid"])),
        I("Video size", radio("vid_size", (64, 96, 128, 192, 256, 384, 512, 640, 800, 1024)), visible=lambda i: bool(C["vid"])),
        I("Video opacity", radio("vid_op", (20, 40, 60, 80, 100), lambda v: f"{v}%"), visible=lambda i: bool(C["vid"])),
        I("Hide black background", flip("vid_black"), checked=lambda i: C["vid_black"], visible=lambda i: bool(C["vid"])),
        I("Remove video", remove_video, visible=lambda i: bool(C["vid"])),
    )),
)

draw_menu = M(
    I("Open drawing editor...", lambda *_: post(open_editor)),
    I("Drawing cell size", radio("cell", range(1, 13))),
    I("Clear hand drawing", lambda *_: post(lambda: (C.update(cells={}), apply()))),
)

place_menu = M(
    I("Move crosshair (drag)", lambda *_: post(lambda: place("xh"))),
    I("Reset to center", lambda *_: post(lambda: (C.update(dx=0, dy=0), apply()))),
    I("Monitor", M(lambda: tuple(
        I(f"Monitor {n + 1}  ({m[2]}×{m[3]})", setv("mon", n), checked=lambda i, n=n: C["mon"] == n, radio=True)
        for n, m in enumerate(mons())))),
)

game_menu = M(
    I("Expand crosshair while firing", radio("spread", (0, 2, 4, 6, 8, 12), lambda v: "Off" if v == 0 else str(v))),
    I("Aim-down-sights preset (right mouse button)", M(ads_menu)),
    M.SEPARATOR,
    I(lambda i: ("Bound to: " + C["bind"]) if C["bind"] else "Bind to game (hide outside it)", bind_game),
    I("Unbind", lambda *_: post(lambda: (C.update(bind=""), BOUND.__setitem__(0, True), apply())),
      visible=lambda i: bool(C["bind"])),
    M.SEPARATOR,
    I("Link current preset to an open game...", map_game),
    I("Link by choosing the game file (.exe)...", map_game_file),
    I("Link by typing the path or name (exe)...", map_game_manual),
    I("Hide crosshair outside linked games", flip("hide_outside"), checked=lambda i: C["hide_outside"]),
    I("Linked games", M(gmap_menu)),
)

HK_RELOAD = threading.Event()


def rebind(act):
    if act == "slot":
        r = capture_key("Preset slot modifiers",
                        "Press the modifier combo + any key\n(e.g. Ctrl+Alt+1) - the digits 1-9 are added automatically")
        if r is None:
            return
        new = "+".join(r.split("+")[:-1])
        if not new:
            toast("Use at least one modifier (Ctrl / Alt / Shift / Win)", 3000)
            return
    else:
        new = capture_key(f"Hotkey: {KEY_LABELS[act]}", f"Press the new shortcut for\n\"{KEY_LABELS[act]}\"")
        if new is None:
            return
    trial = {**C["keys"], act: new}
    if not keys_valid(trial):
        toast("That shortcut is already used by another action", 3000)
        return
    C["keys"] = trial
    apply()
    HK_RELOAD.set()
    toast(f"{KEY_LABELS.get(act, 'Preset slots')}: {new}", 2200)


def reset_keys():
    C["keys"] = dict(DEFAULT_KEYS)
    apply()
    HK_RELOAD.set()
    toast("Hotkeys reset to defaults")


settings_menu = M(
    I("Start with Windows", toggle_autostart, checked=lambda i: autostart_on()),
    I("Show name on startup", flip("splash"), checked=lambda i: C["splash"]),
    M.SEPARATOR,
    I("Version: " + VERSION, lambda *_: None, enabled=False),
    I("Check for updates now", lambda *_: check_update(True)),
    I("Check for updates automatically", flip("autoupd"), checked=lambda i: C["autoupd"]),
    M.SEPARATOR,
    I("Hotkeys (click to change)", M(
        *[I((lambda i, a=a: f"{KEY_LABELS[a]}:  {C['keys'][a]}"), lambda *_, a=a: post(lambda: rebind(a)))
          for a in KEY_LABELS],
        I(lambda i: f"Load preset 1 … 9:  {C['keys']['slot']}+1…9", lambda *_: post(lambda: rebind("slot"))),
        M.SEPARATOR,
        I("Reset hotkeys to defaults", lambda *_: post(reset_keys)),
    )),
)

# ---------- settings window (built on open, destroyed on close) ----------
SW = [None]
PV = 220
SWATCH = [c_ for _n, c_ in MENU_COLORS]


def open_settings(tab="Shape"):
    if SW[0] is not None and SW[0].winfo_exists():
        SW[0].deiconify()
        SW[0].lift()
        SW[0].focus_force()
        return
    for _k, _v in {"*Radiobutton.selectColor": BTN, "*Radiobutton.activeBackground": PANEL,
                   "*Radiobutton.activeForeground": FG, "*Listbox.background": BTN, "*Listbox.foreground": FG,
                   "*Listbox.selectBackground": ACC, "*Listbox.highlightThickness": 0,
                   "*Listbox.relief": "flat"}.items():
        root.option_add(_k, _v)
    w = SW[0] = mk("Reticle - Settings")
    w.resizable(False, False)
    st = {"tab": tab, "t": 0.0}
    left = tk.Frame(w)
    left.pack(side="left", fill="both", padx=(12, 6), pady=12)
    right = tk.Frame(w)
    right.pack(side="right", fill="y", padx=(6, 12), pady=12)
    tabbar = tk.Frame(left)
    tabbar.pack(fill="x")
    body = tk.Frame(left, width=500, height=470, highlightthickness=1, highlightbackground=ACC)
    body.pack(fill="both", expand=True)
    body.pack_propagate(False)

    # ---- live preview + preset status
    pcv = tk.Canvas(right, width=PV, height=PV, bg="#1b2430", highlightthickness=1, highlightbackground=EDGE)
    pcv.pack()
    tk.Label(right, text="Live preview   (hover = full-screen view)", fg=MUTE).pack(pady=(4, 10))

    def hover_watch():
        """Enter/Leave events are unreliable here (the dimming window appears under the cursor), so poll the cursor"""
        try:
            if not w.winfo_exists():
                return
            pt = wt.POINT()
            U32.GetCursorPos(ctypes.byref(pt))
            x0, y0 = pcv.winfo_rootx(), pcv.winfo_rooty()
            inside = x0 <= pt.x < x0 + pcv.winfo_width() and y0 <= pt.y < y0 + pcv.winfo_height()
            if inside != (PVW[0] is not None):
                screen_preview(inside)
                if inside:
                    to_top(w)
        except Exception:
            logging.exception("hover_watch")
        w.after(70, hover_watch)
    w.after(300, hover_watch)
    status = tk.Label(right, text="", wraplength=PV, justify="left")
    status.pack(anchor="w", pady=(0, 8))
    savebtn = tk.Button(right, text="Save changes", bg=ACC, fg="#fff", width=22)
    savebtn.pack(pady=3)
    tk.Button(right, text="Save as new...", width=22, command=lambda: (save_preset(), w.after(300, refresh))).pack(pady=3)
    tk.Button(right, text="Close", width=22, command=lambda: close()).pack(side="bottom", pady=3)
    _prev_ph = [None]   # keep PhotoImage reference alive

    def _build_preview():
        """Render crosshair shape + embedded images into a PV×PV PIL image for the preview canvas"""
        cx = cy = PV // 2
        # 1. Draw crosshair shape onto a temporary tk canvas (off-screen render via PIL)
        tmp = Image.new("RGBA", (PV, PV), (27, 36, 48, 255))
        # Draw grid lines
        from PIL import ImageDraw as _ID
        _d = _ID.Draw(tmp)
        _d.line([(cx, 0), (cx, PV)], fill="#26323f")
        _d.line([(0, cy), (PV, cy)], fill="#26323f")
        # Render crosshair shape onto tmp via a hidden tk Canvas then capture pixels
        _tc = tk.Canvas(w, bg="#1b2430", highlightthickness=0, width=PV, height=PV)
        _tc.place(x=-9999, y=-9999)   # off-screen
        paint(_tc, C, cx, cy)
        _tc.update_idletasks()
        # Overlay images (slot 0 and slot 1)
        for i, S in enumerate(SLOTS):
            b64 = C.get(S["img"], "")
            if not b64:
                continue
            try:
                im = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGBA")
                # Apply flip
                if C.get(S["fh"]):
                    im = im.transpose(getattr(Image, "Transpose", Image).FLIP_LEFT_RIGHT)
                if C.get(S["fv"]):
                    im = im.transpose(getattr(Image, "Transpose", Image).FLIP_TOP_BOTTOM)
                # Apply rotation
                if C.get(S["rot"]):
                    im = im.rotate(-C[S["rot"]], expand=True, resample=Image.BICUBIC)
                # Scale to preview size (proportional to PV vs actual display size)
                disp_size = C.get(S["size"], 48)
                scale = PV / 512   # preview is PV px, full display could be up to 512
                sz = max(8, round(disp_size * scale * 2))
                k = sz / max(im.size)
                im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), RS)
                # Apply tint
                tt = C.get(S["tint"], "")
                if tt:
                    a = im.getchannel("A")
                    if tt == "gray":
                        g = im.convert("L")
                        im = Image.merge("RGBA", (g, g, g, a))
                    else:
                        im = Image.new("RGBA", im.size, tuple(int(tt[j:j+2], 16) for j in (1, 3, 5)) + (255,))
                        im.putalpha(a)
                # Apply opacity
                op = C.get(S["op"], 100) / 100
                if op < 1:
                    r_, g_, b_, a_ = im.split()
                    a_ = a_.point(lambda p: round(p * op))
                    im = Image.merge("RGBA", (r_, g_, b_, a_))
                # Position: offset from center
                ox = C.get(S["x"], 0)
                oy = C.get(S["y"], 0)
                px = cx - im.width // 2 + round(ox * scale)
                py = cy - im.height // 2 + round(oy * scale)
                tmp.paste(im, (px, py), im)
            except Exception:
                pass
        _tc.destroy()
        return tmp

    def refresh():
        if not w.winfo_exists():
            return
        # Draw shape on canvas (for the crosshair lines/dots which need tk canvas)
        pcv.delete("all")
        pcv.create_line(PV // 2, 0, PV // 2, PV, fill="#26323f")
        pcv.create_line(0, PV // 2, PV, PV // 2, fill="#26323f")
        paint(pcv, C, PV // 2, PV // 2)
        # Overlay images as a PIL composite on top
        try:
            if C.get("img") or C.get("img2"):
                prev_img = _build_preview()
                # Flatten RGBA onto the dark background
                bg = Image.new("RGB", (PV, PV), (27, 36, 48))
                bg.paste(prev_img.convert("RGB"), mask=prev_img.getchannel("A"))
                ph = ImageTk.PhotoImage(bg)
                pcv.create_image(0, 0, anchor="nw", image=ph)
                _prev_ph[0] = ph   # keep reference
                # Re-draw crosshair shape on top of images
                paint(pcv, C, PV // 2, PV // 2)
        except Exception:
            pass
        dirty = is_dirty()
        status.config(text="Preset: " + (C["cur"] or "none") + ("   (modified)" if dirty else ""))
        savebtn.config(state="normal" if dirty else "disabled")

    savebtn.config(command=lambda: (save_changes(), w.after(300, refresh)))

    def live(k, v):
        C[k] = v
        draw()
        refresh()
        save_soon()

    def commit():
        apply()
        refresh()

    def close(*_):
        screen_preview(False)
        SW[0] = None
        w.destroy()

    # ---- small widget helpers
    def slider(p, label, key, lo, hi, f=1):
        r = tk.Frame(p)
        r.pack(fill="x", pady=2)
        tk.Label(r, text=label, width=12, anchor="w").pack(side="left")
        ready = [False]
        sc = tk.Scale(r, from_=lo, to=hi, orient="horizontal", length=320, bd=0, bg=PANEL, fg=FG,
                      command=lambda x: ready[0] and live(key, int(float(x)) if f == 1 else max(.1, int(float(x)) / f)))
        sc.set(round(C[key] * f))
        ready[0] = True
        sc.pack(side="left")
        sc.bind("<ButtonRelease-1>", lambda e: commit())
        sc.bind("<KeyRelease>", lambda e: commit())

    def check(p, label, key):
        var = tk.BooleanVar(value=bool(C[key]))
        tk.Checkbutton(p, text=label, variable=var, command=lambda: (C.update({key: var.get()}), commit())).pack(anchor="w", pady=2)

    def button(p, text, fn, **kw):
        b = tk.Button(p, text=text, command=fn, **kw)
        b.pack(anchor="w", pady=3)
        return b

    def color_row(p, label, key, same=None):
        box = tk.Frame(p)
        box.pack(fill="x", pady=6)
        tk.Label(box, text=label, anchor="w").pack(anchor="w")
        sw = tk.Frame(box)
        sw.pack(anchor="w", pady=3)

        def setc(c):
            C[key] = c
            commit()
            build()

        def custom():
            c = pick_color(C[key] or C["color"])
            if c:
                setc(c)

        def build():
            for ch in sw.winfo_children():
                ch.destroy()
            cur, i = C[key], 0
            if same:
                tk.Button(sw, text=("✓ " if not cur else "") + same, command=lambda: setc("")).grid(row=0, column=0, columnspan=3, padx=1, pady=1, sticky="w")
                i = 3
            for c in SWATCH + C["my_colors"]:
                on = c == cur
                lum = sum(int(c[j:j + 2], 16) for j in (1, 3, 5)) > 380
                tk.Button(sw, bg=c, fg="#000" if lum else "#fff", text="✓" if on else "", width=2, padx=0, pady=0,
                          command=lambda c=c: setc(c)).grid(row=i // 9, column=i % 9, padx=1, pady=1)
                i += 1
            tk.Button(sw, text="Custom...", command=custom).grid(row=i // 9 + 1, column=0, columnspan=3, pady=4, sticky="w")
        build()

    # ---- tabs
    def tab_shape(p):
        f = tk.Frame(p)
        f.pack(anchor="w", pady=(0, 8))
        bs = {}

        def pick(v):
            C["shape"] = v
            commit()
            for k_, b_ in bs.items():
                b_.config(bg=ACC if k_ == v else BTN)
        for i, (n, v) in enumerate(SHAPES):
            bs[v] = tk.Button(f, text=n, width=14, bg=ACC if C["shape"] == v else BTN, command=lambda v=v: pick(v))
            bs[v].grid(row=i // 4, column=i % 4, padx=2, pady=2)
        slider(p, "Length", "length", 1, 60)
        slider(p, "Thickness", "thick", 1, 20)
        slider(p, "Gap", "gap", 0, 60)
        slider(p, "Outline", "outline", 0, 6)
        slider(p, "Rotation", "rot", 0, 359)
        slider(p, "Opacity %", "opacity", 10, 100, f=100)
        check(p, "Center dot", "dot")
        slider(p, "Dot size", "dot_size", 1, 20)
        check(p, "Show built-in shape", "show_shape")

    def tab_colors(p):
        color_row(p, "Shape color", "color")
        color_row(p, "Outline color", "outline_color")
        color_row(p, "Dot color", "dot_color", same="Same as shape")
        check(p, "Adapt shape color to the background", "adapt")

    def tab_position(p):
        off = tk.Label(p, text="", fg=MUTE)

        def upd():
            off.config(text=f"Offset from center: {C['dx']}, {C['dy']}")

        def mv():
            w.withdraw()
            place("xh")

            def back():
                if PLACING[0] is not None and PLACING[0].winfo_exists():
                    w.after(200, back)
                elif w.winfo_exists():
                    w.deiconify()
                    upd()
                    refresh()
            w.after(300, back)

        def reset():
            C.update(dx=0, dy=0)
            commit()
            upd()
        button(p, "Move crosshair (drag on screen)...", mv)
        button(p, "Reset to center", reset)
        off.pack(anchor="w")
        upd()
        tk.Label(p, text="Monitor", anchor="w").pack(anchor="w", pady=(14, 2))
        mv_ = tk.IntVar(value=C["mon"])
        for n, m in enumerate(mons()):
            tk.Radiobutton(p, text=f"Monitor {n + 1}  ({m[2]}×{m[3]})", variable=mv_, value=n,
                           command=lambda n=n: (C.update(mon=n), commit())).pack(anchor="w")
        tk.Label(p, text="While firing (left mouse)", anchor="w").pack(anchor="w", pady=(14, 0))
        slider(p, "Expand by", "spread", 0, 12)

    def tab_games(p):
        tk.Label(p, text="Aim-down-sights preset (while right mouse is held)", anchor="w").pack(anchor="w")
        av = tk.StringVar(value=C["ads"] or "None")
        om = tk.OptionMenu(p, av, "None", *names(), command=lambda v: (C.update(ads="" if v == "None" else v), commit()))
        om.config(bg=BTN, fg=FG, activebackground=ACC_HI, activeforeground="#fff", highlightthickness=0, bd=0, relief="flat", width=24)
        om["menu"].config(bg=BTN, fg=FG, activebackground=ACC_HI)
        om.pack(anchor="w", pady=(2, 10))
        tk.Label(p, text="Link the current preset to a game", anchor="w").pack(anchor="w")
        row = tk.Frame(p)
        row.pack(anchor="w", pady=3)
        tk.Button(row, text="Open game...", command=lambda: map_game()).pack(side="left", padx=(0, 4))
        tk.Button(row, text="Choose .exe...", command=lambda: map_game_file()).pack(side="left", padx=4)
        tk.Button(row, text="Type path/name...", command=lambda: map_game_manual()).pack(side="left", padx=4)
        lb = tk.Listbox(p, height=6, width=64, activestyle="none")
        keys = sorted(C["gmap"])
        for e in keys:
            lb.insert("end", f"{e if has_sep(e) else e + '  (any folder)'}   ->   {C['gmap'][e]}")
        lb.pack(anchor="w", pady=(6, 3))

        def rm():
            s_ = lb.curselection()
            if s_:
                C["gmap"].pop(keys[s_[0]], None)
                commit()
                show("Games")
        button(p, "Remove selected link", rm)

        def rm_cur():
            n_ = C["cur"]
            C["gmap"] = {e: v for e, v in C["gmap"].items() if v != n_}
            commit()
            show("Games")
        button(p, "Remove ALL links of the current preset", rm_cur)
        check(p, "Hide crosshair outside linked games", "hide_outside")
        tk.Label(p, text="Bind to a single game (hide everywhere else)", anchor="w").pack(anchor="w", pady=(10, 0))
        row = tk.Frame(p)
        row.pack(anchor="w", pady=3)
        tk.Label(row, text=("Bound to: " + C["bind"]) if C["bind"] else "Not bound", fg=MUTE).pack(side="left", padx=(0, 8))
        tk.Button(row, text="Bind to open game...", command=lambda: bind_game()).pack(side="left")
        if C["bind"]:
            tk.Button(row, text="Unbind", command=lambda: (C.update(bind=""), BOUND.__setitem__(0, True), commit(), show("Games"))).pack(side="left", padx=4)

    def tab_keys(p):
        tk.Label(p, text="Click Change, then press the new shortcut (Esc cancels).", fg=MUTE).pack(anchor="w", pady=(0, 8))
        for a in list(KEY_LABELS) + ["slot"]:
            r = tk.Frame(p)
            r.pack(fill="x", pady=3)
            lab = KEY_LABELS.get(a, "Load preset 1 … 9 (modifiers)")
            tk.Label(r, text=lab, width=28, anchor="w").pack(side="left")
            tk.Label(r, text=C["keys"][a] + ("+1…9" if a == "slot" else ""), width=18, anchor="w", fg=ACC_HI).pack(side="left")
            tk.Button(r, text="Change...", command=lambda a=a: (rebind(a), show("Hotkeys"))).pack(side="left")
        button(p, "Reset hotkeys to defaults", lambda: (reset_keys(), show("Hotkeys")))

    def tab_res(p):
        dev = dev_name()
        cur = cur_mode(dev)
        tk.Label(p, text=f"Monitor {C['mon'] + 1}      Now: {res_text(*cur) if cur else 'unknown'}", anchor="w").pack(anchor="w")
        o_ = RES_ORIG.get(dev)
        tk.Label(p, text=(f"Original: {res_text(*o_)}   (comes back when Reticle closes)" if o_ else
                          "Original resolution untouched (it is restored when Reticle closes)"), fg=MUTE, anchor="w").pack(anchor="w", pady=(0, 6))
        row = tk.Frame(p)
        row.pack(anchor="w", pady=2)
        ents = []
        for lab_, val_, wd in (("Width", cur[0] if cur else "", 6), ("Height", cur[1] if cur else "", 6), ("Hz (optional)", "", 5)):
            tk.Label(row, text=lab_).pack(side="left", padx=(0, 3))
            e_ = tk.Entry(row, width=wd, justify="center")
            e_.insert(0, str(val_))
            e_.pack(side="left", padx=(0, 10), ipady=2)
            ents.append(e_)

        def again():
            if w.winfo_exists():
                show("Resolution")
                refresh()

        def go(_e=None):
            try:
                w_, h_ = int(ents[0].get()), int(ents[1].get())
                hz_ = int(ents[2].get()) if ents[2].get().strip() else None
            except ValueError:
                toast("Width and height must be numbers")
                return
            if not (320 <= w_ <= 16384 and 240 <= h_ <= 16384):
                toast("That size looks wrong")
                return
            set_res_ui(w_, h_, hz_)
            w.after(300, again)
        tk.Button(row, text="Apply", command=go, bg=ACC, fg="#fff").pack(side="left", padx=3)
        tk.Button(row, text="Restore original", command=lambda: (restore_res(), w.after(900, again)),
                  state="normal" if o_ else "disabled").pack(side="left", padx=3)
        for e_ in ents:
            e_.bind("<Return>", go)
        tk.Label(p, text="Supported modes (click to fill, double-click to apply).  * = reported by the driver only, may work",
                 fg=MUTE, anchor="w").pack(anchor="w", pady=(8, 2))
        mf = tk.Frame(p)
        mf.pack(anchor="w")
        modes_ = mode_list(dev) + mode_list(dev, True)
        n_std = len(mode_list(dev))
        lbm = tk.Listbox(mf, height=5, width=44, activestyle="none", exportselection=False)
        sb = tk.Scrollbar(mf, command=lbm.yview)
        lbm.config(yscrollcommand=sb.set)
        for j_, (w_, h_, hz_) in enumerate(modes_):
            lbm.insert("end", f"{w_} × {h_}    @ {hz_} Hz" + ("   *" if j_ >= n_std else ""))
        lbm.pack(side="left")
        sb.pack(side="left", fill="y")

        def fill(_e=None):
            s_ = lbm.curselection()
            if s_:
                for e_, v_ in zip(ents, modes_[s_[0]]):
                    e_.delete(0, "end")
                    e_.insert(0, str(v_))
        lbm.bind("<<ListboxSelect>>", fill)
        lbm.bind("<Double-Button-1>", lambda _e: (fill(), go()))
        tk.Label(p, text="Resolution per game (set when that game comes to the front)", anchor="w").pack(anchor="w", pady=(10, 2))
        gr = tk.Frame(p)
        gr.pack(anchor="w")
        for t_, k_ in (("Open game...", "open"), ("Choose .exe...", "file"), ("Type path/name...", "type")):
            tk.Button(gr, text=t_, command=lambda k_=k_: link_game_res(k_, done=lambda: w.after(200, again))).pack(side="left", padx=(0, 4))
        gl = tk.Listbox(p, height=3, width=64, activestyle="none", exportselection=False)
        gkeys = sorted(C["gres"])
        for e_ in gkeys:
            pr_ = parse_res(C["gres"][e_])
            gl.insert("end", f"{e_ if has_sep(e_) else e_ + '  (any folder)'}   ->   {res_text(*pr_) if pr_ else C['gres'][e_]}")
        gl.pack(anchor="w", pady=(4, 2))

        def rm():
            s_ = gl.curselection()
            if s_:
                C["gres"].pop(gkeys[s_[0]], None)
                commit()
                show("Resolution")
        tk.Button(p, text="Remove selected", command=rm).pack(anchor="w", pady=2)
        check(p, "Go back to the original resolution when I leave the game", "res_revert")

    TABS = (("Shape", tab_shape), ("Colors", tab_colors), ("Position", tab_position), ("Resolution", tab_res),
            ("Games", tab_games), ("Hotkeys", tab_keys))
    tb = {}

    def show(name):
        st["tab"] = name
        st["t"] = time.time()
        for ch in body.winfo_children():
            ch.destroy()
        inner = tk.Frame(body)
        inner.pack(fill="both", expand=True, padx=14, pady=12)
        dict(TABS)[name](inner)
        for k_, b_ in tb.items():
            b_.config(bg=ACC if k_ == name else BTN)

    for n, _f in TABS:
        tb[n] = tk.Button(tabbar, text=n, width=10, command=lambda n=n: show(n))
        tb[n].pack(side="left", padx=(0, 3))

    def focus_in(e):
        if e.widget is w and time.time() - st["t"] > .4:
            show(st["tab"])
            refresh()
    w.bind("<FocusIn>", focus_in)
    w.bind("<Escape>", close)
    w.protocol("WM_DELETE_WINDOW", close)
    show(tab if tab in dict(TABS) else "Shape")
    refresh()
    w.focus_force()


menu = M(
    I("Coded by FlxR", lambda *_: None),
    I("Discord: fs.d   (click to copy)", copy_discord),
    M.SEPARATOR,
    I(lambda i: "Current preset: " + (C["cur"] or "none") + ("   (modified)" if is_dirty() else ""),
      lambda *_: None, enabled=False),
    I(lambda i: "Save changes to: " + C["cur"], save_changes, visible=lambda i: is_dirty()),
    I(lambda i: "⬆ Update available: " + UPD["info"]["version"], install_update, visible=lambda i: bool(UPD["info"])),
    I(lambda i: f"Show / hide  ({C['keys']['toggle']})", toggle, checked=lambda i: C["visible"], default=True),
    I("Settings window...", lambda *_: post(open_settings)),
    M.SEPARATOR,
    I("Presets", M(presets_items)),
    I("Crosshair", cross_menu),
    I("Hand drawing", draw_menu),
    I("Images & video", media_menu),
    I("Position & monitor", place_menu),
    M.SEPARATOR,
    I("Resolution", res_menu),
    I("In-game", game_menu),
    I("Settings", settings_menu),
    I("Exit", lambda *_: post(lambda: (restore_res(final=True), icon.stop(), root.destroy()))),
)

# ---------- custom tray menu (dark red + darker edges) ----------
MENU_BG, MENU_EDGE, MENU_HOT, MENU_SEP, MENU_DIS = "#33090f", "#120206", "#7a1822", "#5a1a21", "#8a5a60"
MENU_FONT = ("Segoe UI", 10)
OPEN_MENUS, ACTIVE, MENU_T = [], {}, [0.0]


def close_menus():
    for w in OPEN_MENUS:
        try:
            w.destroy()
        except Exception:
            pass
    OPEN_MENUS.clear()
    ACTIVE.clear()


def work_area(x, y):
    """Work area of the monitor containing the point (excludes the taskbar)"""
    try:
        class MI(ctypes.Structure):
            _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT), ("rcWork", wt.RECT), ("dwFlags", wt.DWORD)]
        U32.MonitorFromPoint.restype = ctypes.c_void_p
        U32.MonitorFromPoint.argtypes = [wt.POINT, wt.DWORD]
        U32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MI)]
        mi = MI()
        mi.cbSize = ctypes.sizeof(MI)
        U32.GetMonitorInfoW(U32.MonitorFromPoint(wt.POINT(x, y), 2), ctypes.byref(mi))
        r = mi.rcWork
        if r.right > r.left and r.bottom > r.top:
            return r.left, r.top, r.right, r.bottom
        raise ValueError("no work area")
    except Exception:
        return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()


def open_menu(m, level, anchor, left=True):
    while len(OPEN_MENUS) > level:
        OPEN_MENUS.pop().destroy()
    for k in [k for k in ACTIVE if k > level]:
        ACTIVE.pop(k)
    try:
        items = list(m)
    except Exception:
        logging.exception("menu items")
        return
    if not items:
        return
    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.configure(bg=MENU_EDGE)
    win.withdraw()
    body = tk.Frame(win, bg=MENU_BG)
    body.pack(padx=3, pady=3)
    OPEN_MENUS.append(win)
    go_left = [left]
    x0, y0, x1, y1 = work_area(anchor[1], anchor[2] if anchor[0] == "point" else anchor[3])
    per_col = max(8, (y1 - y0 - 50) // 30)

    def add_row(parent, it):
        if it is M.SEPARATOR:
            tk.Frame(parent, bg=MENU_SEP, height=1).pack(fill="x", padx=8, pady=4)
            return
        try:
            text, chk, rad, en, sub = it.text, it.checked, it.radio, it.enabled, it.submenu
        except Exception:
            logging.exception("menu item")
            return
        fg = FG if en else MENU_DIS
        row = tk.Frame(parent, bg=MENU_BG, cursor="hand2" if en else "arrow")
        row.pack(fill="x")
        lm = tk.Label(row, text="●" if (chk and rad) else ("✓" if chk else ""), width=2, bg=MENU_BG, fg=fg, font=MENU_FONT)
        lt = tk.Label(row, text=text, bg=MENU_BG, fg=fg, anchor="w", padx=4, pady=5, font=MENU_FONT)
        la = tk.Label(row, text="▸" if sub else "", width=2, bg=MENU_BG, fg=fg, font=MENU_FONT)
        lm.pack(side="left")
        la.pack(side="right")
        lt.pack(side="left", fill="x", expand=True)
        parts = (row, lm, lt, la)

        def paint(c):
            for w_ in parts:
                try:
                    w_.config(bg=c)
                except Exception:
                    pass

        def open_sub():
            if ACTIVE.get(level) is paint and sub and en:
                open_menu(sub, level + 1, ("side", row.winfo_rootx(), row.winfo_rootx() + row.winfo_width(), row.winfo_rooty()), go_left[0])

        def enter(_e):
            old = ACTIVE.get(level)
            if old and old is not paint:
                old(MENU_BG)
            ACTIVE[level] = paint
            while len(OPEN_MENUS) > level + 1 and not sub:
                OPEN_MENUS.pop().destroy()
            if en:
                paint(MENU_HOT)
                if sub:
                    win.after(140, open_sub)

        def click(_e):
            if not en:
                return
            if sub:
                open_sub()
                return
            close_menus()
            root.after(15, lambda: it(icon))
        for w_ in parts:
            w_.bind("<Enter>", enter)
            w_.bind("<Button-1>", click)
    chunks = [items[i:i + per_col] for i in range(0, len(items), per_col)]
    for ci, ch_ in enumerate(chunks):
        if ci:
            tk.Frame(body, bg=MENU_SEP, width=1).pack(side="left", fill="y", pady=4)
        col = tk.Frame(body, bg=MENU_BG)
        col.pack(side="left", anchor="n")
        for it in ch_:
            add_row(col, it)
    win.update_idletasks()
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    if anchor[0] == "point":
        x, y = anchor[1] - w, anchor[2] - h
        if x < x0:
            x = anchor[1]
        if y < y0:
            y = anchor[2]
    else:
        y = anchor[3] - 3
        if left and anchor[1] - w + 2 >= x0:
            x = anchor[1] - w + 2
        elif anchor[2] - 2 + w <= x1:
            x, left = anchor[2] - 2, False
        else:
            x = anchor[1] - w + 2
    go_left[0] = left
    x = max(x0, min(x, x1 - w))
    y = max(y0, min(y, y1 - h))
    win.geometry(f"+{x}+{y}")
    win.deiconify()
    win.lift()


def menu_watch():
    if not OPEN_MENUS:
        return
    try:
        if U32.GetAsyncKeyState(0x1B) & 0x8000:
            close_menus()
            return
        if time.time() - MENU_T[0] > .25 and any(U32.GetAsyncKeyState(v) & 0x8000 for v in (1, 2, 4)):
            pt = wt.POINT()
            U32.GetCursorPos(ctypes.byref(pt))
            if not any(w.winfo_rootx() <= pt.x < w.winfo_rootx() + w.winfo_width()
                       and w.winfo_rooty() <= pt.y < w.winfo_rooty() + w.winfo_height() for w in OPEN_MENUS):
                close_menus()
                return
    except Exception:
        logging.exception("menu_watch")
    root.after(40, menu_watch)


def show_menu(x, y):
    close_menus()
    MENU_T[0] = time.time()
    open_menu(menu, 0, ("point", x, y))
    root.after(40, menu_watch)


icon = pystray.Icon("crosshair", tray_img(), "Reticle", menu)


def _hook_tray():
    """Redirect right-click on the tray icon to our custom menu (if it fails, the normal Windows menu stays)"""
    try:
        for k, fn in list(icon._message_handlers.items()):
            if getattr(fn, "__name__", "") == "_on_notify":
                def wrap(wparam, lparam, _orig=fn):
                    if lparam == 0x205:   # WM_RBUTTONUP
                        pt = wt.POINT()
                        U32.GetCursorPos(ctypes.byref(pt))
                        post(lambda: show_menu(pt.x, pt.y))
                        return
                    return _orig(wparam, lparam)
                icon._message_handlers[k] = wrap
    except Exception:
        logging.exception("tray hook")


_hook_tray()

def hk_actions():
    fn = {"toggle": toggle, "prev": lambda: post(lambda: step_preset(-1)), "next": lambda: post(lambda: step_preset(1)),
          "left": lambda: move(-1, 0), "right": lambda: move(1, 0), "up": lambda: move(0, -1), "down": lambda: move(0, 1)}
    for n in range(9):
        fn[f"slot{n}"] = lambda n=n: post(lambda: load_nth(n))
    return fn


def hotkeys():
    reg, table = [], {}

    def register():
        for i in reg:
            U32.UnregisterHotKey(None, i)
        reg.clear()
        table.clear()
        fn, bad = hk_actions(), []
        for i, mod, vk, act, label in build_combos(dict(C["keys"])):
            table[i] = fn[act]
            if U32.RegisterHotKey(None, i, mod, vk):
                reg.append(i)
            else:
                bad.append(label)
        if bad:
            msg = "Hotkey not working (reserved by another program): " + ", ".join(bad)
            logging.warning(msg)
            post(lambda: toast(msg, 4000))
    register()
    m = wt.MSG()
    while True:
        while U32.PeekMessageW(ctypes.byref(m), None, 0, 0, 1):
            if m.message == 0x312 and m.wParam in table:
                table[m.wParam]()
        if HK_RELOAD.is_set():
            HK_RELOAD.clear()
            register()
        time.sleep(0.015)


SIG = [tuple(U32.GetSystemMetrics(i) for i in (0, 1, 76, 77, 78, 79))]


def poll():
    try:
        while not q.empty():
            q.get()()
        gk = U32.GetAsyncKeyState
        lb = bool(gk(1) & 0x8000) and C["spread"] > 0
        rb = bool(gk(2) & 0x8000) and bool(C["ads"])
        ch = lb != LMB[0] or rb != RMB[0]
        LMB[0], RMB[0] = lb, rb
        TICK[0] += 1
        if TICK[0] % 25 == 0 and shown() and PLACING[0] is None:
            keep_top()
        if gate() and TICK[0] % 8 == 0:
            e = fg_exe()
            if e and not is_own(e):
                b = same_exe(e, C["bind"]) or (C["hide_outside"] and link_for(e) is not None)
                if b != BOUND[0]:
                    BOUND[0], ch = b, True
        if (C["gmap"] or C["gres"]) and TICK[0] % 8 == 0:
            e = fg_exe()
            if e and not is_own(e) and e != LASTEXE[0]:
                LASTEXE[0] = e
                n = link_for(e)
                if n and n != C["cur"]:
                    load_now(n, ask=False)
                game_res(e)
        if GAME_LEAVE[0] and time.time() - GAME_LEAVE[0] > 3:
            GAME_LEAVE[0] = 0.0
            if C["res_revert"] and RES_BY_GAME[0]:
                restore_res()
        if TICK[0] % 25 == 0:       # the desktop size changed behind our back (a game, the user, a driver)
            sig = tuple(U32.GetSystemMetrics(i) for i in (0, 1, 76, 77, 78, 79))
            if sig != SIG[0]:
                SIG[0] = sig
                screen_refresh()
        if C["adapt"]:
            if ImageGrab and TICK[0] % 8 == 4 and shown():
                adapt_request()
        elif AD["col"] or AD["bg"]:
            AD.update(col=None, bg=None, alt=False)
            ch = True
        if ch:
            draw()
    except Exception:
        logging.exception("poll")
    root.after(40, poll)


recover_res()
draw()
clickthrough(root)
icon.run_detached()
threading.Thread(target=hotkeys, daemon=True).start()
if ImageGrab:
    threading.Thread(target=adapt_worker, daemon=True).start()
root.after(6000, upd_loop)
poll()

# Register .reticle file association (silent, runs once per launch)
register_file_assoc()

# If launched by double-clicking a .reticle file, import it automatically
_argv_file = next((a for a in sys.argv[1:] if a.lower().endswith(".reticle") and os.path.isfile(a)), None)
if _argv_file:
    root.after(600, lambda: open_reticle_file(_argv_file))
elif C["splash"]:
    root.after(300, splash)

root.mainloop()
