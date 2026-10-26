"""
The Attendance page's lessons strip (new look N3): one card per lesson of the Date-box day, wrapping to more rows
when the page is narrow.

Presentation only. The caller hands in the cards as plain dicts and a click handler; this file reads no data, opens
nothing and never touches the keyboard focus (test_n3 T11 pins its source).

A card dict: class_id, time ("16:00–17:00"), name, cancelled (bool), n (students), marked (students with a mark).
"""

import tkinter as tk

from ui import theme

CANCELLED_LINE = "Cancelled · not recorded by schedule"
NO_LESSONS = "No lessons on this day"
NO_DATE = "No date"


def make_strip(parent):
    """The strip's frame on the page ground. Pack it; then fill it with show_cards or show_message."""
    strip = tk.Frame(parent, bg=theme.colour('ground', '#ecf0f1'), padx=theme.scale(20), takefocus=0)
    strip._cols = 0
    strip.bind("<Configure>", lambda e: _reflow(strip))
    return strip


def _clear(strip):
    for w in strip.winfo_children():
        w.destroy()
    strip._cols = 0


def show_message(strip, text):
    """One muted line instead of cards ("No lessons on this day", "No date")."""
    _clear(strip)
    tk.Label(strip, text=text, bg=strip.cget("bg"), fg=theme.colour('ink_muted', '#7f8c8d'), font=theme.font(9),
             anchor="w", takefocus=0).grid(row=0, column=0, sticky="w", pady=(0, theme.scale(8)))


def _third_line(card):
    if card["cancelled"]:
        return CANCELLED_LINE
    if not card["n"]:
        return "No students"
    if card["marked"]:
        return f"{card['marked']} of {card['n']} marked"
    return f"{card['n']} student" + ("" if card["n"] == 1 else "s")


def show_cards(strip, cards, selected_id, on_click):
    """One card per dict, in order; the card of selected_id is highlighted; a click on a card (or any of its
    labels) calls on_click(class_id)."""
    _clear(strip)
    if not cards:
        show_message(strip, NO_LESSONS)
        return
    bg = theme.colour('card', 'white')
    muted = theme.colour('ink_muted', '#7f8c8d')
    wrap = theme.scale(150)
    for card in cards:
        selected = card["class_id"] == selected_id
        box = tk.Frame(strip, bg=bg, highlightthickness=2 if selected else 1,
                       highlightbackground=theme.colour('primary', '#2c3e50') if selected
                       else theme.colour('line', '#bdc3c7'),
                       padx=theme.scale(10), pady=theme.scale(6), takefocus=0)
        head = tk.Frame(box, bg=bg, takefocus=0)
        head.pack(side=tk.TOP, fill=tk.X)
        tk.Label(head, text=card["time"], bg=bg, fg=muted, font=theme.font(9), anchor="w", wraplength=wrap,
                 pady=theme.scale(2), takefocus=0).pack(side=tk.LEFT)
        if card["cancelled"]:
            tk.Label(head, text="Cancelled", bg=theme.colour('tag_cancelled_bg', '#fadbd8'),
                     fg=theme.colour('tag_cancelled_fg', '#c0392b'), font=theme.font(8, bold=True),
                     padx=theme.scale(4), takefocus=0).pack(side=tk.RIGHT, padx=(theme.scale(6), 0))
        tk.Label(box, text=card["name"], bg=bg, fg=muted if card["cancelled"] else theme.colour('ink', '#2c3e50'),
                 font=theme.font(10, bold=True), anchor="w", justify=tk.LEFT, wraplength=wrap, pady=theme.scale(2),
                 takefocus=0).pack(side=tk.TOP, fill=tk.X)
        tk.Label(box, text=_third_line(card), bg=bg,
                 fg=theme.colour('tag_cancelled_fg', '#c0392b') if card["cancelled"] else muted,
                 font=theme.font(9), anchor="w", justify=tk.LEFT, wraplength=wrap, pady=theme.scale(2),
                 takefocus=0).pack(side=tk.TOP, fill=tk.X)
        for w in [box] + _descendants(box):
            w.bind("<Button-1>", lambda e, cid=card["class_id"]: on_click(cid))
    _reflow(strip)


def _descendants(w):
    out = []
    for c in w.winfo_children():
        out.append(c)
        out.extend(_descendants(c))
    return out


def _reflow(strip):
    """Grid the cards into as many equal columns as the strip's width holds. Only a change in the number of
    columns re-grids, so the strip's own height change is a no-op."""
    cards = [w for w in strip.winfo_children() if isinstance(w, tk.Frame)]
    if not cards:
        return
    width = strip.winfo_width() - 2 * int(str(strip.cget("padx")))
    gap = theme.scale(10)
    widest = max(c.winfo_reqwidth() for c in cards) + gap
    cols = max(1, width // widest) if width > 1 else len(cards)
    cols = min(cols, len(cards))
    if cols == strip._cols:
        return
    for i in range(max(strip._cols, cols, len(cards))):
        strip.grid_columnconfigure(i, uniform="", weight=0, minsize=0)
    for i in range(cols):
        strip.grid_columnconfigure(i, uniform="card")
    for k, c in enumerate(cards):
        c.grid(row=k // cols, column=k % cols, sticky="nsew", padx=(0, gap), pady=(0, theme.scale(8)))
    strip._cols = cols
