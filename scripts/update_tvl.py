"""Rewrite the TVL and TOKENS blocks in README.md from live public APIs.

TVL:          DefiLlama protocol API (current + peak TVL)
Market caps:  DefiLlama coins API (CoinGecko market caps, no API key needed)
FXB bonds:    Frax API (bond list) + on-chain totalFxbMinted (max supply) x $1 face value
OFT list:     hardcoded from FraxFinance/frax-oft-upgradeable README (commit 981a7b9, 2026-09-10)
If a source fails, that block is left unchanged so the README never breaks.
"""
import datetime, json, re, urllib.request

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

# Frax LayerZero OFTs: (symbol, Ethereum contract, coingecko id)
FRAX_OFTS = [
    ("frxUSD", "0x566a6442A5A6e9895B9dCA97cC7879D632c6e4B0", "frax-usd"),
    ("sfrxUSD", "0x7311CEA93ccf5f4F7b789eE31eBA5D9B9290E126", "staked-frax-usd"),
    ("frxETH", "0x1c1649A38f4A3c5A0c4a24070f688C525AB7D6E6", "frax-ether"),
    ("sfrxETH", "0xbBc424e58ED38dd911309611ae2d7A23014Bd960", "staked-frax-ether"),
    ("FRAX (WFRAX, formerly FXS)", "0x04ACaF8D2865c0714F79da09645C13FD2888977f", "frax-share"),
    ("Legacy FRAX (LFRAX)", "0x909DBdE1eBE906Af95660033e478D59EFe831fED", "frax"),
]
FOOTNOTE = (f"<sub>*Fetched {STAMP}. See [the update script](scripts/update_tvl.py) "
            "for sources and the latest values; it runs daily.</sub>")


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
    peak_day = max(daily, key=daily.get)
    return current, daily[peak_day], datetime.date.fromtimestamp(peak_day * 86400)


def tvl_block():
    rows = ["| Protocol | TVL now* | Peak TVL* |", "|---|---|---|"]
    for name, slug in TVL_PROTOCOLS:
        cur, peak, when = tvl(slug)
        rows.append(f"| [{name}](https://defillama.com/protocol/{slug}) | {usd(cur)} | {usd(peak)} ({when:%b %Y}) |")
    return "\n".join(rows + ["", FOOTNOTE])


# ---------- Tokens ----------
FXB_MINTED = "0xd44845fd"  # totalFxbMinted(): only ever increases, so it is the bond's max supply


def eth_call_uint(chain, addr, data):
    r = get(RPC[chain], {"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                         "params": [{"to": addr, "data": data}, "latest"]})
    return int(r["result"], 16) / 1e18


def tokens_block():
    caps = mcaps([t[3] for t in PROTOCOL_TOKENS] + [t[2] for t in FRAX_OFTS])

    out = ["**Protocol tokens**", "", "| Token | Chain | Market cap* | Contract |", "|---|---|---|---|"]
    for sym, chain, addr, cg in PROTOCOL_TOKENS:
        out.append(f"| {sym} | {chain.capitalize()} | {usd(caps[cg])} | {link(chain, addr)} |")

    out += ["", "**Frax LayerZero OFTs**", "", "| Token | Market cap* | Ethereum contract |", "|---|---|---|"]
    for sym, addr, cg in FRAX_OFTS:
        out.append(f"| {sym} | {usd(caps[cg])} | {link('ethereum', addr)} |")

    bonds = get("https://api.frax.finance/v2/fxb/bonds")["bonds"]
    out += ["", "**FXB bonds**", "", "| Bond | Chain | Maturity | Value Issued* | Contract |", "|---|---|---|---|---|"]
    for b in sorted(bonds, key=lambda b: (b["maturity"], b["chain"])):
        try:
            cap = usd(eth_call_uint(b["chain"], b["address"], FXB_MINTED) * 1.0)  # max supply x $1 face value
        except Exception:
            cap = "n/a"
        out.append(f"| {b['symbol']} | {b['chain'].capitalize()} | {b['maturity']} | {cap} | {link(b['chain'], b['address'])} |")

    out += ["", FOOTNOTE]
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
readme = replace(readme, "TVL", tvl_block)
readme = replace(readme, "TOKENS", tokens_block)
open("README.md", "w").write(readme)
print(readme)
