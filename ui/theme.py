"""
ui/theme.py -- house visual theme for the Siri English school portal.

Appearance only. No logic, no data access, no service control lives here.

Built on the "clam" ttk base theme deliberately: the native Windows ttk
themes ("vista", "winnative") ignore button background colours, which the
Start/Stop status mapping depends on.

OFF SWITCH
    set PORTAL_THEME=classic

restores the pre-theme appearance exactly, DPI awareness included. Every
edit made by the theme pilot is gated on the CLASSIC flag below.

House palette lives in ui/design_system.py (HOUSE) and is the single
source of truth. Status mapping, which must survive:
    RUNNING / UP / Start  -> HOUSE['primary']  #0F6E66
    STOPPED / DOWN / Stop -> HOUSE['danger']   #B02020
    warnings              -> HOUSE['warning']  #F59221
"""
import os
from pathlib import Path

import tkinter as tk
from tkinter import ttk, font as tkfont

from ui.design_system import HOUSE, SYSTEM_COLORS_CLASSIC, SYSTEM_COLORS_HOUSE

# ---------------------------------------------------------------------------
# Off switch
# ---------------------------------------------------------------------------

CLASSIC = os.environ.get("PORTAL_THEME", "").strip().lower() == "classic"

# ---------------------------------------------------------------------------
# Fonts and DPI
# ---------------------------------------------------------------------------

_BASE_DPI = 96.0
_scale = 1.0

# Classic defaults; replaced by init_root() when the house theme is active.
_FAM_UI = "Arial"
_FAM_HEADER = "Arial"
_FAM_MONO = "Consolas"

# The Siri diamond S-mark for the header bar. Rendered only if present, so a
# missing asset degrades to a text-only header rather than raising.
HEADER_MARK = Path(__file__).resolve().parent / "assets" / "siri_mark.png"


def scale(px):
    """Scale a hard-coded pixel size for the current display DPI.

    Tk's own scaling resizes point-sized fonts but not pixel geometry, so
    every fixed pixel dimension has to come through here. Returns px
    unchanged in classic mode.
    """
    if CLASSIC:
        return px
    return int(round(px * _scale))


def font(size=9, bold=False, italic=False, mono=False, header=False):
    """A font tuple in the house families. Arial (today's font) in classic."""
    family = _FAM_MONO if mono else (_FAM_HEADER if header else _FAM_UI)
    styles = []
    if bold:
        styles.append("bold")
    if italic:
        styles.append("italic")
    return (family, size) + tuple(styles)


def measure(widget, *samples, bold=False, pad=16):
    """Pixel width of the widest sample in the live UI font, plus padding.

    Used instead of character widths so column sizing survives a font or DPI
    change instead of silently drifting.
    """
    f = tkfont.Font(root=widget, font=font(9, bold=bold))
    return max(f.measure(s) for s in samples) + scale(pad)


def _pick_family(root, *names):
    try:
        available = set(tkfont.families(root))
    except tk.TclError:
        return names[-1]
    for name in names:
        if name in available:
            return name
    return names[-1]


def enable_dpi_awareness():
    """Make the process DPI aware. Must run before the first Tk root exists.

    System-aware (level 1), not per-monitor (level 2): Tk 8.6 does not
    rescale on WM_DPICHANGED, so per-monitor awareness leaves the window
    wrong after a drag between monitors.
    """
    if CLASSIC:
        return False
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        return True
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _mix(colour_a, colour_b, t):
    """Blend colour_a toward colour_b by t (0..1). Used for hover/press states."""
    a, b = _rgb(colour_a), _rgb(colour_b)
    return "#%02X%02X%02X" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def system_colors():
    """The colour map for the System tab: house palette, or today's in classic."""
    return dict(SYSTEM_COLORS_CLASSIC if CLASSIC else SYSTEM_COLORS_HOUSE)


def on_panel():
    """kwargs placing a plain tk widget on a house panel. Empty in classic."""
    return {} if CLASSIC else {"bg": HOUSE["panel"]}


# ---------------------------------------------------------------------------
# Root / style setup
# ---------------------------------------------------------------------------

def init_root(root):
    """Attach the theme to a Tk root and return its ttk.Style.

    Called by both roots (LoginWindow and MainWindow) so the login window
    matches the portal. In classic mode this returns a plain ttk.Style and
    changes nothing else.
    """
    global _scale, _FAM_UI, _FAM_HEADER, _FAM_MONO

    style = ttk.Style(root)
    if CLASSIC:
        return style

    try:
        dpi = float(root.winfo_fpixels("1i"))
    except tk.TclError:
        dpi = _BASE_DPI
    if dpi > 0:
        _scale = dpi / _BASE_DPI
        root.tk.call("tk", "scaling", dpi / 72.0)

    _FAM_UI = _pick_family(root, "Segoe UI", "Calibri", "Arial")
    _FAM_HEADER = _pick_family(root, "Georgia", _FAM_UI)
    _FAM_MONO = _pick_family(root, "Consolas", "Courier New")

    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont",
                 "TkHeadingFont", "TkIconFont", "TkTooltipFont"):
        try:
            tkfont.Font(root=root, name=name, exists=True).configure(
                family=_FAM_UI, size=9)
        except tk.TclError:
            pass
    try:
        tkfont.Font(root=root, name="TkFixedFont", exists=True).configure(
            family=_FAM_MONO, size=9)
    except tk.TclError:
        pass

    apply(style)
    return style


def treeview_defaults(style):
    """Global Treeview appearance.

    In classic these are the values that main_window.py's attendance tab used
    to set on the shared "Treeview" style, which leaked to every tree in the
    app. Keeping them here preserves that appearance now the attendance tab
    uses its own named style.
    """
    if CLASSIC:
        style.configure("Treeview", rowheight=28, font=("Arial", 10),
                        background="white", foreground="#2c3e50")
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
        return

    style.configure("Treeview",
                    rowheight=scale(28), font=font(10),
                    background=HOUSE["card"], fieldbackground=HOUSE["card"],
                    foreground=HOUSE["ink"], bordercolor=HOUSE["line"])
    style.configure("Treeview.Heading",
                    font=font(10, bold=True), background=HOUSE["panel"],
                    foreground=HOUSE["primary"], relief="flat",
                    padding=scale(4))
    style.map("Treeview",
              background=[("selected", HOUSE["primary"])],
              foreground=[("selected", "#FFFFFF")])


def apply(style):
    """Configure the house named styles on a ttk.Style. No-op in classic."""
    if CLASSIC:
        return style

    style.theme_use("clam")

    body = font(9)
    bold = font(9, bold=True)
    pad_x, pad_y = scale(10), scale(5)

    ground = HOUSE["ground"]
    panel = HOUSE["panel"]
    ink = HOUSE["ink"]
    line = HOUSE["line"]

    style.configure(".", background=ground, foreground=ink, font=body,
                    bordercolor=line, focuscolor=HOUSE["primary"])
    style.configure("TFrame", background=ground)
    style.configure("TLabel", background=ground, foreground=ink, font=body)
    style.configure("TLabelframe", background=ground, bordercolor=line)
    style.configure("TLabelframe.Label", background=ground,
                    foreground=HOUSE["primary"], font=bold)
    style.configure("TSeparator", background=line)

    style.configure("TNotebook", background=panel, bordercolor=line,
                    tabmargins=(scale(6), scale(4), scale(6), 0))
    style.configure("TNotebook.Tab", background=panel, foreground=ink,
                    padding=(scale(14), scale(6)), font=body)
    style.map("TNotebook.Tab",
              background=[("selected", ground),
                          ("active", _mix(panel, ground, 0.5))],
              foreground=[("selected", HOUSE["primary"])])

    for name in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(name, fieldbackground=ground, background=ground,
                        foreground=ink, bordercolor=line, insertcolor=ink,
                        padding=scale(3))
        style.map(name, bordercolor=[("focus", HOUSE["primary"])])

    style.configure("TScrollbar", background=panel, troughcolor=ground,
                    bordercolor=line, arrowcolor=HOUSE["primary"])

    for name in ("TCheckbutton", "TRadiobutton"):
        style.configure(name, background=ground, foreground=ink, font=body)

    style.configure("TButton", font=body, padding=(pad_x, pad_y),
                    background=panel, foreground=ink, bordercolor=line,
                    relief="flat")
    style.map("TButton",
              background=[("pressed", _mix(panel, "#000000", 0.10)),
                          ("active", _mix(panel, "#FFFFFF", 0.40)),
                          ("disabled", _mix(panel, ground, 0.55))],
              foreground=[("disabled", HOUSE["ink_muted"])])

    # Status-carrying buttons. White on #F59221 is 2.3:1 and fails; ink on
    # #F59221 is 6.9:1, so warning buttons take ink text, not white.
    for name, bg, fg in (
        (BTN_STYLE["success"], HOUSE["primary"], "#FFFFFF"),
        (BTN_STYLE["danger"], HOUSE["danger"], "#FFFFFF"),
        (BTN_STYLE["warning"], HOUSE["warning"], HOUSE["ink"]),
    ):
        style.configure(name, font=body, padding=(pad_x, pad_y),
                        background=bg, foreground=fg,
                        bordercolor=_mix(bg, "#000000", 0.15), relief="flat")
        style.map(name,
                  background=[("pressed", _mix(bg, "#000000", 0.14)),
                              ("active", _mix(bg, "#FFFFFF", 0.14)),
                              ("disabled", _mix(bg, ground, 0.62))],
                  foreground=[("disabled", HOUSE["ink_muted"])])

    # Neutral buttons (Log, Browse, Refresh, the dialog toggle) sit ON a cream
    # panel, so a cream fill left them with no visible edge at all. They get a
    # real 1px outline instead, and a hover that brightens the fill and turns
    # the outline green. lightcolor/darkcolor are pinned to the fill so clam
    # does not add its 3D bevel on top. Ink text throughout.
    style.configure(BTN_STYLE["neutral"], font=body, padding=(pad_x, pad_y),
                    background=panel, foreground=ink,
                    bordercolor=line, lightcolor=panel, darkcolor=panel,
                    borderwidth=1, relief="solid")
    style.map(BTN_STYLE["neutral"],
              background=[("pressed", _mix(panel, "#000000", 0.08)),
                          ("active", ground),
                          ("disabled", _mix(panel, ground, 0.55))],
              bordercolor=[("pressed", HOUSE["primary"]),
                           ("active", HOUSE["primary"]),
                           ("disabled", line)],
              lightcolor=[("active", ground),
                          ("pressed", _mix(panel, "#000000", 0.08))],
              darkcolor=[("active", ground),
                         ("pressed", _mix(panel, "#000000", 0.08))],
              foreground=[("disabled", HOUSE["ink_muted"])])

    for name, fill in (("Horizontal.TProgressbar", HOUSE["primary"]),
                       ("House.Caution.Horizontal.TProgressbar", HOUSE["fill_only"]),
                       ("House.Danger.Horizontal.TProgressbar", HOUSE["danger"])):
        style.configure(name, background=fill, troughcolor=panel,
                        bordercolor=line, lightcolor=fill, darkcolor=fill,
                        thickness=scale(14))

    treeview_defaults(style)
    return style


# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------

BTN_STYLE = {
    "success": "House.Success.TButton",
    "danger": "House.Danger.TButton",
    "warning": "House.Warning.TButton",
    "neutral": "House.Neutral.TButton",
}

# Exactly the colours the System tab set before the pilot, for classic mode.
_CLASSIC_SET = {
    "success": {"bg": "#27ae60", "fg": "white"},
    "danger": {"bg": "#e74c3c", "fg": "white"},
    "warning": {"bg": "#f39c12", "fg": "white"},
    "neutral": {},
}


def button(parent, kind="neutral", classic=None, **kw):
    """Create a themed button.

    kind    -- 'success' | 'danger' | 'warning' | 'neutral'
    classic -- tk-only kwargs (bg, fg, font, padx, pady, width) reproducing
               today's look, applied in classic mode only
    **kw    -- options valid for both widget classes (text, command, state)

    ttk buttons ignore bg=, so every construction site and every runtime
    recolour has to go through here or through set_button().
    """
    if CLASSIC:
        opts = dict(classic or {})
        opts.update(kw)
        return tk.Button(parent, **opts)
    kw.setdefault("style", BTN_STYLE.get(kind, BTN_STYLE["neutral"]))
    return ttk.Button(parent, **kw)


def set_button(btn, kind=None, **kw):
    """Recolour/relabel a button created by button(). Safe on both classes."""
    if CLASSIC:
        if kind:
            kw.update(_CLASSIC_SET.get(kind, {}))
    elif kind:
        kw["style"] = BTN_STYLE.get(kind, BTN_STYLE["neutral"])
    btn.config(**kw)


# ---------------------------------------------------------------------------
# Flat plain buttons (new look N1)
# ---------------------------------------------------------------------------
#
# The portal's plain tk.Buttons stay tk.Buttons (tests find them by
# winfo_class() == "Button"); only their colours and relief change. The
# border width is left as it is, so no button changes size: a flat border is
# drawn in the button's own colour. Windows Tk does not paint an unfocused
# button's highlight ring, so no kind can rely on it for an edge: the
# secondary kind is a light grey fill instead of white, which shows on white
# cards and on the ground alike (N1 Phase 4, David: option C).

_FLAT = {
    "primary": (HOUSE["primary"], "#FFFFFF", HOUSE["primary_dark"], HOUSE["primary"]),
    "secondary": (HOUSE["btn_secondary"], HOUSE["ink"], HOUSE["btn_secondary_active"],
                  HOUSE["btn_secondary"]),
    "danger": (HOUSE["danger"], "#FFFFFF", HOUSE["danger_active"], HOUSE["danger"]),
    "warning": (HOUSE["warning"], HOUSE["ink"], HOUSE["warning_active"], HOUSE["warning"]),
}
_FLAT_ALIAS = {"success": "primary"}


def flat_colors(kind):
    """The colour options of a flat button of this kind. Empty in classic."""
    if CLASSIC:
        return {}
    bg, fg, active, edge = _FLAT[_FLAT_ALIAS.get(kind, kind)]
    return {"bg": bg, "fg": fg, "activebackground": active,
            "activeforeground": fg, "highlightbackground": edge,
            "highlightcolor": HOUSE["ink"]}


def flat_button(parent, kind, **kw):
    """A plain tk.Button in the house colours of `kind`.

    kind -- 'primary' | 'secondary' | 'danger' | 'warning' ('success' is
            primary)
    **kw -- tk.Button options. The colour options given here (bg, fg, ...)
            are today's look and are used only in classic mode, where the
            button is built exactly as before.
    """
    if not CLASSIC:
        kw.update(flat_colors(kind))
        kw["relief"] = "flat"
    return tk.Button(parent, **kw)


def set_flat(btn, kind, **kw):
    """Recolour a flat button at run time. `kw` (bg, fg, ...) is today's look,
    applied in classic mode only; other options go in an ordinary config()."""
    btn.config(**(flat_colors(kind) if not CLASSIC else kw))


def colour(token, classic):
    """A house token for a plain tk widget, or today's literal in classic."""
    return classic if CLASSIC else HOUSE[token]


# ---------------------------------------------------------------------------
# Header bar
# ---------------------------------------------------------------------------

def panel(parent, text, **kw):
    """A section LabelFrame: cream house panel, or today's default in classic."""
    kw.setdefault("font", font(10, bold=True))
    if not CLASSIC:
        kw.setdefault("bg", HOUSE["panel"])
        kw.setdefault("fg", HOUSE["primary"])
        kw.setdefault("bd", 0)
        kw.setdefault("relief", "flat")
    return tk.LabelFrame(parent, text=text, **kw)


def header_mark(parent, bg, height_px):
    """The Siri diamond S-mark for a header bar, or None if unavailable.

    Returns None in classic mode, when the asset is missing, or on any load
    error, so the header falls back to text only and never raises.
    """
    if CLASSIC or not HEADER_MARK.exists():
        return None
    try:
        from PIL import Image, ImageTk
        img = Image.open(HEADER_MARK)
        height = max(1, height_px - scale(12))
        width = max(1, round(img.width * (height / img.height)))
        img = img.resize((width, height), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        label = tk.Label(parent, image=photo, bg=bg, bd=0)
        label.image = photo  # keep a reference or Tk drops the image
        return label
    except Exception:
        return None
