"""Rewrite the TVL block in README.md from the DefiLlama protocol API.

Writes current, peak and 3-year average TVL, and the history chart in assets/tvl-*.svg.
If the source fails, the block is left unchanged so the README never breaks.
"""
import datetime, json, math, re, urllib.request

NOW = datetime.datetime.now(datetime.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%d %H:%M UTC")

# DefiLlama merged Aerodrome and Velodrome into one parent protocol, "Aero", and the old slugs now
# return it too; listing them separately would count the same TVL twice.
TVL_PROTOCOLS = [("Aero", "aero"), ("Fraxtal", "fraxtal")]
AVG_DAYS = 3 * 365
SKIP = {"borrowed", "staking", "pool2", "vesting"}
FOOTNOTE = f"<sub>*Fetched {STAMP}. See [the update script](scripts/update_tvl.py) for details.</sub>"


def get(url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={
        "User-Agent": "readme-updater", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def usd(x):
    if x is None or x <= 0:
        return "n/a"
    if x >= 1e9:
        return f"${x/1e9:.2f}B"
    if x >= 1e6:
        return f"${x/1e6:.1f}M"
    return f"${x/1e3:.0f}K"


# ---------- TVL ----------
def tvl(slug):
    d = get(f"https://api.llama.fi/protocol/{slug}")
    chains = {k: v for k, v in d["chainTvls"].items() if "-" not in k and k not in SKIP}
    current = sum(d["currentChainTvls"].get(k, 0) for k in chains)
    daily = {}
    for v in chains.values():
        per_day = {}  # a chain can have 2 points on one day (snapshot + live); keep the last
        for p in v["tvl"]:
            per_day[p["date"] // 86400] = p["totalLiquidityUSD"]
        for day, x in per_day.items():
            daily[day] = daily.get(day, 0) + x
    daily[NOW.date().toordinal() - EPOCH] = current  # end every series on the live value shown in the table
    return current, daily


EPOCH = datetime.date(1970, 1, 1).toordinal()
# refs/heads/main, not main: raw.githubusercontent.com was seen serving the previous commit for the
# short branch name after a push, while the full ref resolved to the new one.
ASSETS_URL = "https://raw.githubusercontent.com/pegahcarter/pegahcarter/refs/heads/main/assets"


def day_to_date(day):
    return datetime.date.fromordinal(day + EPOCH)


def peak_of(daily):
    day = max(daily, key=daily.get)
    return daily[day], day_to_date(day)


def recent_avg(daily):
    # Days before a protocol's DefiLlama history starts are skipped, not counted as $0.
    start = NOW.date().toordinal() - EPOCH - AVG_DAYS
    recent = [x for day, x in daily.items() if day > start]
    return sum(recent) / len(recent)


def tvl_block():
    rows = ["| Protocol | TVL now* | 3-year average* | Peak TVL* |", "|---|---|---|---|"]
    series = []
    for name, slug in TVL_PROTOCOLS:
        cur, daily = tvl(slug)
        peak, when = peak_of(daily)
        series.append((name, daily, cur))
        rows.append(f"| [{name}](https://defillama.com/protocol/{slug}) | {usd(cur)} | {usd(recent_avg(daily))} "
                    f"| {usd(peak)} ({when:%b %Y}) |")
    for theme in THEMES:
        with open(f"assets/tvl-{theme}.svg", "w") as f:
            f.write(tvl_svg(series, THEMES[theme]))
    alt = "TVL over time for " + " and ".join(name for name, _ in TVL_PROTOCOLS)
    # Absolute URLs: the profile page at github.com/<user> doesn't resolve repo-relative srcset paths.
    picture = (f'<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="{ASSETS_URL}/tvl-dark.svg">\n'
               f'  <img alt="{alt}" src="{ASSETS_URL}/tvl-light.svg">\n</picture>')
    return "\n".join([picture, ""] + rows + ["", FOOTNOTE])


# ---------- TVL chart ----------
# Series colors are slots 1-3 of the dataviz reference palette, validated for CVD separation in both
# modes. Light-mode aqua is under 3:1 on white, so every line also carries a direct end label.
THEMES = {
    "light": {"fg": "#1f2328", "muted": "#59636e", "grid": "#d1d9e0", "axis": "#afb8c1",
              "surface": "#ffffff", "series": ["#2a78d6", "#eb6834", "#1baf7a"]},
    "dark": {"fg": "#f0f6fc", "muted": "#9198a1", "grid": "#262c36", "axis": "#3d444d",
             "surface": "#0d1117", "series": ["#3987e5", "#d95926", "#199e70"]},
}
W, H, ML, MR, MT, MB = 800, 360, 56, 150, 64, 32


def axis_usd(v):
    if v == 0:
        return "$0"
    return f"${v/1e9:g}B" if v >= 1e9 else f"${v/1e6:g}M"


def tvl_svg(series, t):
    first = min(min(d for d in daily if daily[d] >= max(daily.values()) * 0.01) for _, daily, _ in series)
    last = max(max(d) for _, d, _ in series)
    vmax = max(max(d.values()) for _, d, _ in series)
    step = next(s for s in (1e8, 2.5e8, 5e8, 1e9, 2.5e9, 5e9, 1e10) if vmax / s <= 5)
    top = math.ceil(vmax / step) * step
    pw, ph = W - ML - MR, H - MT - MB
    x = lambda day: ML + (day - first) / (last - first) * pw
    y = lambda v: MT + ph - v / top * ph
    font = 'font-family="system-ui,-apple-system,Segoe UI,Helvetica,Arial,sans-serif"'
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" {font} '
           'role="img" aria-labelledby="t">',
           f'<title id="t">TVL over time: {", ".join(n for n, _, _ in series)}</title>',
           f'<text x="0" y="18" font-size="15" font-weight="600" fill="{t["fg"]}">TVL over time</text>']

    lx = 0
    for (name, _, _), color in zip(series, t["series"]):
        out.append(f'<line x1="{lx}" y1="38" x2="{lx + 16}" y2="38" stroke="{color}" stroke-width="2" stroke-linecap="round"/>'
                   f'<text x="{lx + 22}" y="42" font-size="12" fill="{t["muted"]}">{name}</text>')
        lx += 22 + len(name) * 7 + 20

    for i in range(int(round(top / step)) + 1):
        v = i * step
        gy = y(v)
        stroke = t["axis"] if v == 0 else t["grid"]
        out.append(f'<line x1="{ML}" y1="{gy:.1f}" x2="{ML + pw}" y2="{gy:.1f}" stroke="{stroke}" stroke-width="1"/>'
                   f'<text x="{ML - 8}" y="{gy + 4:.1f}" font-size="11" text-anchor="end" fill="{t["muted"]}">{axis_usd(v)}</text>')
    for year in range(day_to_date(first).year + 1, day_to_date(last).year + 1):
        day = datetime.date(year, 1, 1).toordinal() - EPOCH
        out.append(f'<text x="{x(day):.1f}" y="{H - 10}" font-size="11" text-anchor="middle" fill="{t["muted"]}">{year}</text>')

    ends, peak = [], None
    for (name, daily, cur), color in zip(series, t["series"]):
        pday = max(daily, key=daily.get)
        # Drop pre-launch dust so a series doesn't open with a vertical spike off the baseline.
        start = next(d for d in sorted(daily) if daily[d] >= daily[pday] * 0.01)
        days = [d for d in sorted(daily) if d >= start]
        keep = [d for d in days if (d - days[0]) % 7 == 0 or d in (pday, days[-1])]
        path = " ".join(f"{'M' if i == 0 else 'L'}{x(d):.1f},{y(daily[d]):.1f}" for i, d in enumerate(keep))
        out.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
        ends.append([y(daily[days[-1]]), x(days[-1]), y(daily[days[-1]]), name, cur, color])
        if peak is None or daily[pday] > peak[0]:
            peak = (daily[pday], x(pday), y(daily[pday]), color)

    ends.sort()
    for i in range(1, len(ends)):
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 18)
    overflow = ends[-1][0] - (MT + ph)
    if overflow > 0:
        for e in ends:
            e[0] -= overflow
    for ly, ex, ey, name, cur, color in ends:
        tx = ML + pw + 14
        out.append(f'<line x1="{ex + 6:.1f}" y1="{ey:.1f}" x2="{tx - 4}" y2="{ly:.1f}" stroke="{t["axis"]}" stroke-width="1"/>'
                   f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="4" fill="{color}" stroke="{t["surface"]}" stroke-width="2"/>'
                   f'<text x="{tx}" y="{ly + 4:.1f}" font-size="12"><tspan font-weight="600" fill="{t["fg"]}">{name}</tspan>'
                   f'<tspan fill="{t["muted"]}"> {usd(cur)}</tspan></text>')

    pv, px, py, pc = peak
    out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{pc}" stroke="{t["surface"]}" stroke-width="2"/>'
               f'<text x="{min(max(px, ML + 40), ML + pw - 40):.1f}" y="{py - 10:.1f}" font-size="12" text-anchor="middle">'
               f'<tspan font-weight="600" fill="{t["fg"]}">{usd(pv)}</tspan><tspan fill="{t["muted"]}"> peak</tspan></text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def replace(readme, tag, builder):
    try:
        block = builder()
    except Exception as e:  # keep the old block if a source is down
        print(f"{tag}: skipped ({e})")
        return readme
    pat = rf"(<!-- {tag}:START -->).*?(<!-- {tag}:END -->)"
    return re.sub(pat, lambda m: f"{m.group(1)}\n{block}\n{m.group(2)}", readme, flags=re.S)


readme = open("README.md").read()
readme = replace(readme, "TVL", tvl_block)
open("README.md", "w").write(readme)
print(readme)
