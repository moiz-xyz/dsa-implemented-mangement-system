"""
Developer utility: draws the simple line icons used in the sidebar.

The generated PNG files are committed in assets/icons/, so this script is
NOT needed to run SMARTBUS. It requires Pillow (installed with matplotlib):

    python assets/generate_icons.py
"""

import os

from PIL import Image, ImageDraw

SIZE = 20          # final icon size in pixels
SCALE = 4          # draw 4x larger, then downsample for smooth edges
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")


def canvas():
    img = Image.new("RGBA", (SIZE * SCALE, SIZE * SCALE), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def s(*values):
    return [v * SCALE for v in values]


def save(img, name, color):
    r, g, b = color
    # recolour: keep alpha, set rgb
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            a = px[x, y][3]
            if a:
                px[x, y] = (r, g, b, a)
    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    img.save(os.path.join(OUT, name))


W = 2 * SCALE  # stroke width


def dashboard(d):
    for x, y in ((2, 2), (11, 2), (2, 11), (11, 11)):
        d.rounded_rectangle(s(x, y, x + 7, y + 7), radius=2 * SCALE, outline="white", width=W)


def bus(d):
    d.rounded_rectangle(s(3, 2, 17, 15), radius=3 * SCALE, outline="white", width=W)
    d.line(s(3, 9, 17, 9), fill="white", width=W)
    d.ellipse(s(5, 15, 8, 18), fill="white")
    d.ellipse(s(12, 15, 15, 18), fill="white")


def route(d):
    d.ellipse(s(2, 13, 7, 18), outline="white", width=W)
    d.ellipse(s(13, 2, 18, 7), outline="white", width=W)
    d.line(s(6, 14, 10, 10, 10, 10, 14, 6), fill="white", width=W, joint="curve")


def users(d):
    d.ellipse(s(6, 2, 13, 9), outline="white", width=W)
    d.arc(s(2, 11, 17, 26), 180, 360, fill="white", width=W)


def ticket(d):
    d.rounded_rectangle(s(2, 5, 18, 15), radius=2 * SCALE, outline="white", width=W)
    for y in (7, 10, 13):
        d.ellipse(s(12, y - 0.5, 13, y + 0.5), fill="white")


def queue(d):
    for x in (2, 8, 14):
        d.ellipse(s(x, 4, x + 4, 8), outline="white", width=W)
        d.line(s(x + 2, 9, x + 2, 16), fill="white", width=W)


def chart(d):
    d.line(s(2, 18, 18, 18), fill="white", width=W)
    for x, top in ((4, 11), (9, 5), (14, 8)):
        d.rounded_rectangle(s(x, top, x + 3, 16), radius=SCALE, fill="white")


def lab(d):
    d.line(s(7, 2, 13, 2), fill="white", width=W)
    d.line(s(8, 2, 8, 8, 3, 17, 17, 17, 12, 8, 12, 2), fill="white", width=W, joint="curve")
    d.line(s(5, 13, 15, 13), fill="white", width=W)


def search(d):
    d.ellipse(s(2, 2, 13, 13), outline="white", width=W)
    d.line(s(11, 11, 18, 18), fill="white", width=W + SCALE)


def logout(d):
    d.line(s(9, 3, 3, 3, 3, 17, 9, 17), fill="white", width=W, joint="curve")
    d.line(s(8, 10, 18, 10), fill="white", width=W)
    d.line(s(14, 6, 18, 10, 14, 14), fill="white", width=W, joint="curve")


def undo(d):
    d.arc(s(4, 4, 18, 18), 200, 90, fill="white", width=W)
    d.line(s(3, 4, 4, 10, 10, 9), fill="white", width=W, joint="curve")


def user(d):
    d.ellipse(s(6, 2, 14, 10), outline="white", width=W)
    d.arc(s(3, 12, 17, 26), 180, 360, fill="white", width=W)


def mapicon(d):
    d.line(s(2, 4, 7, 2, 13, 4, 18, 2, 18, 16, 13, 18, 7, 16, 2, 18, 2, 4), fill="white",
           width=W, joint="curve")
    d.line(s(7, 2, 7, 16), fill="white", width=W)
    d.line(s(13, 4, 13, 18), fill="white", width=W)


ICONS = {"dashboard": dashboard, "bus": bus, "route": route, "users": users,
         "ticket": ticket, "queue": queue, "chart": chart, "lab": lab, "search": search,
         "logout": logout, "undo": undo, "user": user, "map": mapicon}

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, draw in ICONS.items():
        for suffix, color in (("", (203, 213, 225)), ("_white", (255, 255, 255)),
                              ("_blue", (37, 99, 235))):
            img, d = canvas()
            draw(d)
            save(img, f"{name}{suffix}.png", color)
    print(f"Icons written to {OUT}")
