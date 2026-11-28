#!/usr/bin/env python3
"""Generates a 600x800 8-bit grayscale PNG dashboard for a Kindle (KT2).

Usage:
  python3 make_dash.py out.png            # live weather from Open-Meteo (no API key)
  python3 make_dash.py out.png --demo     # sample data, no network
  add --no-clock for static hosting (no big clock, shows "updated" time)
Requires: Pillow.  Fonts: DejaVu Sans (change FONT_* paths if needed).
"""
import json
import os
import sys
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

W, H = 600, 800
TZ = ZoneInfo("Europe/Vilnius")
LAT, LON = 54.6872, 25.2797  # Vilnius
FONT_DIRS = ["/usr/share/fonts/truetype/dejavu", "/tmp/fonts"]
FONT_URL = ("https://raw.githubusercontent.com/matplotlib/matplotlib/main/"
            "lib/matplotlib/mpl-data/fonts/ttf/")


def _font_path(name):
    """System DejaVu if present, otherwise download once into /tmp (serverless)."""
    for dd in FONT_DIRS:
        p = os.path.join(dd, name)
        if os.path.exists(p):
            return p
    os.makedirs("/tmp/fonts", exist_ok=True)
    p = os.path.join("/tmp/fonts", name)
    urllib.request.urlretrieve(FONT_URL + name, p)
    return p


FONT = _font_path("DejaVuSans.ttf")
FONT_B = _font_path("DejaVuSans-Bold.ttf")

WEEKDAYS = ["Pirmadienis", "Antradienis", "Trečiadienis", "Ketvirtadienis",
            "Penktadienis", "Šeštadienis", "Sekmadienis"]
WEEKDAYS_SHORT = ["Pr", "An", "Tr", "Kt", "Pn", "Št", "Sk"]
MONTHS = ["sausio", "vasario", "kovo", "balandžio", "gegužės", "birželio",
          "liepos", "rugpjūčio", "rugsėjo", "spalio", "lapkričio", "gruodžio"]


def wmo(code):
    """WMO weather code -> (Lithuanian text, icon kind)."""
    if code == 0:
        return "Giedra", "sun"
    if code in (1, 2):
        return "Mažai debesuota", "partly"
    if code == 3:
        return "Debesuota", "cloud"
    if code in (45, 48):
        return "Rūkas", "fog"
    if code in (51, 53, 55, 56, 57):
        return "Dulksna", "rain"
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "Lietus", "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "Sniegas", "snow"
    if code in (95, 96, 99):
        return "Perkūnija", "storm"
    return "—", "cloud"


def fetch_weather():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m"
        "&hourly=temperature_2m,precipitation_probability"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset"
        "&timezone=Europe%2FVilnius&forecast_days=4"
    )
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def demo_weather():
    return {
        "current": {"temperature_2m": 2.4, "apparent_temperature": -0.8,
                    "weather_code": 3, "wind_speed_10m": 14.0},
        "hourly": demo_hourly(),
        "daily": {
            "time": ["2026-11-23", "2026-11-24", "2026-11-25", "2026-11-26"],
            "weather_code": [3, 61, 71, 0],
            "temperature_2m_max": [3.1, 4.0, 0.5, -1.2],
            "temperature_2m_min": [-0.5, 1.2, -2.0, -4.8],
            "sunrise": ["2026-11-23T07:46"] * 4,
            "sunset": ["2026-11-23T15:52"] * 4,
        },
    }


def demo_hourly():
    from datetime import timedelta
    t0 = datetime(2026, 11, 23, 0, 0)
    temps = [2.4, 2.0, 1.8, 1.5, 1.4, 1.6, 2.2, 3.0, 3.8, 4.1, 4.3, 4.0, 3.5, 3.0,
             2.6, 2.4, 2.2, 2.0, 1.9, 1.8, 1.7, 1.6, 1.5, 1.4]
    prob = [5, 5, 10, 10, 15, 20, 35, 55, 70, 60, 45, 30, 20, 15, 10, 5, 5, 5, 0, 0, 0, 0, 0, 0]
    times = [(t0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(48)]
    return {"time": times, "temperature_2m": (temps * 2)[:48],
            "precipitation_probability": (prob * 2)[:48]}


def icon(d, kind, cx, cy, s):
    """Very simple monochrome weather icons, size ~ s."""
    k = 0
    if kind in ("sun", "partly"):
        r = s // 4
        ox, oy = (-s // 6, -s // 6) if kind == "partly" else (0, 0)
        d.ellipse([cx + ox - r, cy + oy - r, cx + ox + r, cy + oy + r], outline=k, width=4)
        if kind == "sun":
            import math
            for a in range(0, 360, 45):
                x1 = cx + (r + 6) * math.cos(math.radians(a))
                y1 = cy + (r + 6) * math.sin(math.radians(a))
                x2 = cx + (r + 16) * math.cos(math.radians(a))
                y2 = cy + (r + 16) * math.sin(math.radians(a))
                d.line([x1, y1, x2, y2], fill=k, width=3)
    if kind in ("cloud", "partly", "rain", "snow", "storm", "fog"):
        oy = s // 10 if kind != "partly" else s // 6
        ox = 0 if kind != "partly" else s // 8
        def shape(draw, grow, fill):
            g = grow
            draw.ellipse([cx - s // 3 + ox - g, cy - s // 12 + oy - g, cx - s // 12 + ox + g, cy + s // 5 + oy + g], fill=fill)
            draw.ellipse([cx - s // 5 + ox - g, cy - s // 4 + oy - g, cx + s // 8 + ox + g, cy + s // 8 + oy + g], fill=fill)
            draw.ellipse([cx - s // 24 + ox - g, cy - s // 5 + oy - g, cx + s // 3 + ox + g, cy + s // 6 + oy + g], fill=fill)
            draw.rounded_rectangle([cx - s // 4 + ox - g, cy - s // 20 + oy - g, cx + s // 4 + ox + g, cy + s // 5 + oy + g], radius=s // 10, fill=fill)
        shape(d, 3, k)      # black outline silhouette
        shape(d, -1, 255)   # white inside
    if kind in ("rain", "storm"):
        for dx in (-s // 6, 0, s // 6):
            d.line([cx + dx, cy + s // 3 + 6, cx + dx - 6, cy + s // 2 + 6], fill=k, width=3)
    if kind == "snow":
        for dx in (-s // 6, 0, s // 6):
            d.ellipse([cx + dx - 3, cy + s // 3 + 8, cx + dx + 3, cy + s // 3 + 14], fill=k)
    if kind == "fog":
        for i in range(3):
            d.line([cx - s // 3, cy + s // 3 + i * 8, cx + s // 3, cy + s // 3 + i * 8], fill=k, width=3)


def center(d, text, y, font, fill=0, x0=0, x1=W):
    w = d.textlength(text, font=font)
    d.text((x0 + (x1 - x0 - w) / 2, y), text, font=font, fill=fill)


def hourly_slice(data, now, n=12):
    h = data["hourly"]
    start = now.replace(minute=0, second=0, microsecond=0, tzinfo=None)
    times = [datetime.fromisoformat(t) for t in h["time"]]
    idx = next((i for i, t in enumerate(times) if t >= start), 0)
    out = []
    for i in range(idx, min(idx + n, len(times))):
        pp = h["precipitation_probability"][i]
        out.append((times[i], h["temperature_2m"][i], pp if pp is not None else 0))
    return out


def draw_hourly(d, f, rows, y0):
    """Temperature line + precipitation-probability bars for the next hours."""
    x_l, x_r = 40, W - 40
    n = len(rows)
    step = (x_r - x_l) / max(n - 1, 1)
    xs = [x_l + i * step for i in range(n)]
    temps = [r[1] for r in rows]
    tmin, tmax = min(temps), max(temps)
    span = max(tmax - tmin, 2.0)
    ty0, ty1 = y0 + 64, y0 + 112        # temperature band (top..bottom)
    ys = [ty1 - (t - tmin) / span * (ty1 - ty0) for t in temps]

    center(d, "Linija – temperatūra, stulpeliai – lietus", y0, f(18))

    base, maxh = y0 + 164, 40
    bw = 28
    for x, (_, _, pp) in zip(xs, rows):
        h = int(pp / 100 * maxh)
        d.rectangle([x - bw // 2, base - maxh, x + bw // 2, base], outline=190)
        if h > 0:
            d.rectangle([x - bw // 2, base - h, x + bw // 2, base], fill=60)
    d.line([x_l - 14, base, x_r + 14, base], fill=0, width=2)

    d.line(list(zip(xs, ys)), fill=0, width=4)
    for x, y in zip(xs, ys):
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=0)
    for i, (x, y, t) in enumerate(zip(xs, ys, temps)):
        if i % 2 == 0:
            txt = f"{t:+.0f}°"
            w = d.textlength(txt, font=f(22, True))
            d.text((x - w / 2, y - 33), txt, font=f(22, True), fill=0)

    for i, (x, (t, _, pp)) in enumerate(zip(xs, rows)):
        lab = f"{t.hour:02d}"
        w = d.textlength(lab, font=f(20, True))
        d.text((x - w / 2, base + 4), lab, font=f(20, True), fill=0)
        if i % 2 == 0 and pp >= 10:
            pt = f"{pp}%"
            w = d.textlength(pt, font=f(16))
            d.text((x - w / 2, base + 28), pt, font=f(16), fill=0)


def render(data, now, clock=True):
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    f = lambda sz, b=False: ImageFont.truetype(FONT_B if b else FONT, sz)

    # Header: big day number on the left, weekday / month / update time on the right
    day_txt = str(now.day) if not clock else now.strftime("%H:%M")
    big = f(150, True)
    d.text((34, 1), day_txt, font=big, fill=0)
    xr = 34 + int(d.textlength(day_txt, font=big)) + 34
    d.text((xr, 14), WEEKDAYS[now.weekday()], font=f(40, True), fill=0)
    d.text((xr, 70), f"{now.year} m.", font=f(30), fill=0)
    d.text((xr, 104), MONTHS[now.month - 1], font=f(30), fill=0)
    d.text((xr, 142), f"atnaujinta {now.strftime('%H:%M')}", font=f(20), fill=0)
    d.line([30, 174, W - 30, 174], fill=0, width=3)

    # Current weather
    cur = data["current"]
    text, kind = wmo(cur["weather_code"])
    icon(d, kind, 100, 250, 130)
    d.text((196, 178), f"{cur['temperature_2m']:+.0f}°", font=f(104, True), fill=0)
    d.text((200, 296), text, font=f(34), fill=0)
    center(d, f"Jaučiasi {cur['apparent_temperature']:+.0f}°   ·   vėjas {cur['wind_speed_10m']:.0f} km/h",
           340, f(26, True))
    d.line([30, 382, W - 30, 382], fill=0, width=3)

    # Hourly forecast
    draw_hourly(d, f, hourly_slice(data, now), 392)
    d.line([30, 608, W - 30, 608], fill=0, width=3)

    # 3-day forecast
    day = data["daily"]
    colw = (W - 60) // 3
    for i in range(1, 4):
        x0 = 30 + (i - 1) * colw
        x1 = x0 + colw
        dt = datetime.fromisoformat(day["time"][i])
        t, k = wmo(day["weather_code"][i])
        center(d, WEEKDAYS_SHORT[dt.weekday()] + f" {dt.day}", 612, f(26, True), x0=x0, x1=x1)
        icon(d, k, (x0 + x1) // 2, 674, 56)
        center(d, f"{day['temperature_2m_max'][i]:+.0f}° / {day['temperature_2m_min'][i]:+.0f}°",
               712, f(24, True), x0=x0, x1=x1)
        center(d, t, 742, f(19), x0=x0, x1=x1)

    d.line([30, 771, W - 30, 771], fill=0, width=3)
    sr = day["sunrise"][0][11:16]
    ss = day["sunset"][0][11:16]
    center(d, f"Saulėtekis {sr}   ·   Saulėlydis {ss}", 775, f(21))
    return img


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "dash.png"
    demo = "--demo" in sys.argv
    now = datetime.now(TZ)
    if demo:
        now = datetime(2026, 11, 23, 0, 10, tzinfo=TZ)
        data = demo_weather()
    else:
        data = fetch_weather()
    img = render(data, now, clock="--no-clock" not in sys.argv)
    img.save(out, "PNG", optimize=True)  # mode L, 8-bit gray, no alpha
    print(f"wrote {out} ({img.size[0]}x{img.size[1]}, {img.mode})")


if __name__ == "__main__":
    main()
