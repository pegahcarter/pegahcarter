"""Rewrite the BADGE, TVL and TOKENS blocks in README.md from live public APIs.

TVL:          DefiLlama protocol API (current + peak TVL, history for assets/tvl-*.svg)
Market caps:  DefiLlama coins API (CoinGecko market caps, no API key needed)
Peak caps:    running max in scripts/peaks.json; free APIs only return 365 days of history,
              so pre-tracking peaks were seeded by hand
FXB bonds:    Frax API (bond list) + on-chain totalFxbMinted (max supply) x $1 face value
OFT list:     hardcoded from FraxFinance/frax-oft-upgradeable README (commit 981a7b9, 2026-09-10)
If a source fails, that block is left unchanged so the README never breaks.
"""
import datetime, functools, json, math, re, urllib.parse, urllib.request

NOW = datetime.datetime.now(datetime.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%d %H:%M UTC")

TVL_PROTOCOLS = [("Aerodrome", "aerodrome"), ("Velodrome", "velodrome"), ("Fraxtal", "fraxtal")]
SKIP = {"borrowed", "staking", "pool2", "vesting"}

EXPLORERS = {
    "ethereum": "https://etherscan.io/address/",
    "fraxtal": "https://fraxscan.com/address/",
    "optimism": "https://optimistic.etherscan.io/address/",
    "base": "https://basescan.org/address/",
}
RPC = {"ethereum": "https://ethereum-rpc.publicnode.com", "fraxtal": "https://rpc.frax.com"}

# (symbol, chain, address, coingecko id)
PROTOCOL_TOKENS = [
    ("AERO", "base", "0x940181a94A35A4569E4529A3CDfB74e38FD98631", "aerodrome-finance"),
    ("VELO", "optimism", "0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db", "velodrome-finance"),
]

# Frax LayerZero OFTs: (symbol, coingecko id)
FRAX_OFTS = [
    ("frxUSD", "frax-usd"),
    ("sfrxUSD", "staked-frax-usd"),
    ("frxETH", "frax-ether"),
    ("sfrxETH", "staked-frax-ether"),
    ("FRAX (WFRAX, formerly FXS)", "frax-share"),
]
PEAKS_FILE = "scripts/peaks.json"
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


def link(chain, addr):
    short = f"`{addr[:6]}…{addr[-4:]}`"
    base = EXPLORERS.get(chain)
    return f"[{short}]({base}{addr})" if base else short


def mcaps(ids):
    d = get("https://coins.llama.fi/mcaps", {"coins": [f"coingecko:{i}" for i in ids]})
    return {i: d.get(f"coingecko:{i}", {}).get("mcap") for i in ids}


# ---------- TVL ----------
@functools.cache
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
ASSETS_URL = "https://raw.githubusercontent.com/pegahcarter/pegahcarter/main/assets"


def day_to_date(day):
    return datetime.date.fromordinal(day + EPOCH)


def peak_of(daily):
    day = max(daily, key=daily.get)
    return daily[day], day_to_date(day)


def badge_block():
    combined = {}
    for _, slug in TVL_PROTOCOLS:
        for day, x in tvl(slug)[1].items():
            combined[day] = combined.get(day, 0) + x
    value, when = peak_of(combined)
    message = f"{usd(value)} ({when:%b %Y})"
    url = ("https://img.shields.io/badge/" + urllib.parse.quote("peak combined TVL") + "-"
           + urllib.parse.quote(message) + "-2a78d6?style=for-the-badge")
    return f"![Peak combined TVL: {message}]({url})"


def tvl_block():
    rows = ["| Protocol | TVL now* | Peak TVL* |", "|---|---|---|"]
    series = []
    for name, slug in TVL_PROTOCOLS:
        cur, daily = tvl(slug)
        peak, when = peak_of(daily)
        series.append((name, daily, cur))
        rows.append(f"| [{name}](https://defillama.com/protocol/{slug}) | {usd(cur)} | {usd(peak)} ({when:%b %Y}) |")
    for theme in THEMES:
        with open(f"assets/tvl-{theme}.svg", "w") as f:
            f.write(tvl_svg(series, THEMES[theme]))
    # Absolute URLs: the profile page at github.com/<user> doesn't resolve repo-relative srcset paths.
    picture = (f'<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="{ASSETS_URL}/tvl-dark.svg">\n'
               f'  <img alt="TVL over time for Aerodrome, Velodrome and Fraxtal" src="{ASSETS_URL}/tvl-light.svg">\n</picture>')
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


# ---------- Tokens ----------
FXB_MINTED = "0xd44845fd"  # totalFxbMinted(): only ever increases, so it is the bond's max supply


def eth_call_uint(chain, addr, data):
    r = get(RPC[chain], {"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                         "params": [{"to": addr, "data": data}, "latest"]})
    return int(r["result"], 16) / 1e18


def update_peaks(caps):
    try:
        peaks = json.load(open(PEAKS_FILE))
    except FileNotFoundError:
        peaks = {}
    for cg, cap in caps.items():
        if cap and cap > peaks.get(cg, {}).get("mcap", 0):
            peaks[cg] = {"mcap": round(cap, -5), "date": NOW.date().isoformat()}
    return peaks


def peak(peaks, cg):
    p = peaks.get(cg)
    if not p:
        return "n/a"
    return f"{usd(p['mcap'])} ({datetime.date.fromisoformat(p['date']):%b %Y})"


def tokens_block():
    caps = mcaps([t[3] for t in PROTOCOL_TOKENS] + [t[1] for t in FRAX_OFTS])
    peaks = update_peaks(caps)

    out = ["**Protocol tokens**", "", "| Token | Chain | Market cap* | Peak market cap* | Contract |", "|---|---|---|---|---|"]
    for sym, chain, addr, cg in PROTOCOL_TOKENS:
        out.append(f"| {sym} | {chain.capitalize()} | {usd(caps[cg])} | {peak(peaks, cg)} | {link(chain, addr)} |")

    out += ["", "**Frax LayerZero OFTs\\*\\***", "", "| Token | Market cap* | Peak market cap* |", "|---|---|---|"]
    for sym, cg in FRAX_OFTS:
        out.append(f"| {sym} | {usd(caps[cg])} | {peak(peaks, cg)} |")
    out += ["", "<sub>\\*\\*Contract addresses on every chain: [Frax docs](https://docs.frax.com/protocol/crosschain/addresses).</sub>"]

    bonds = get("https://api.frax.finance/v2/fxb/bonds")["bonds"]
    out += ["", "**FXB bonds**", "", "| Bond | Chain | Maturity | Value Issued* | Contract |", "|---|---|---|---|---|"]
    for b in sorted(bonds, key=lambda b: (b["maturity"], b["chain"])):
        try:
            cap = usd(eth_call_uint(b["chain"], b["address"], FXB_MINTED) * 1.0)  # max supply x $1 face value
        except Exception:
            cap = "n/a"
        out.append(f"| {b['symbol']} | {b['chain'].capitalize()} | {b['maturity']} | {cap} | {link(b['chain'], b['address'])} |")

    out += ["", FOOTNOTE]
    # Written only after every source succeeded, so a failed run never persists partial peaks.
    with open(PEAKS_FILE, "w") as f:
        json.dump(peaks, f, indent=2)
        f.write("\n")
    return "\n".join(out)


def replace(readme, tag, builder):
    try:
        block = builder()
    except Exception as e:  # keep the old block if a source is down
        print(f"{tag}: skipped ({e})")
        return readme
    pat = rf"(<!-- {tag}:START -->).*?(<!-- {tag}:END -->)"
    return re.sub(pat, lambda m: f"{m.group(1)}\n{block}\n{m.group(2)}", readme, flags=re.S)


readme = open("README.md").read()
readme = replace(readme, "BADGE", badge_block)
readme = replace(readme, "TVL", tvl_block)
readme = replace(readme, "TOKENS", tokens_block)
open("README.md", "w").write(readme)
print(readme)
