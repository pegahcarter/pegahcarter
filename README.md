<!-- BADGE:START -->
![Peak combined TVL: $1.35B (Dec 2024)](https://img.shields.io/badge/peak%20combined%20TVL-%241.35B%20%28Dec%202024%29-2a78d6?style=for-the-badge)
<!-- BADGE:END -->

## Protocols I engineered

<!-- TVL:START -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/pegahcarter/pegahcarter/main/assets/tvl-dark.svg">
  <img alt="TVL over time for Aerodrome, Velodrome and Fraxtal" src="https://raw.githubusercontent.com/pegahcarter/pegahcarter/main/assets/tvl-light.svg">
</picture>

| Protocol | TVL now* | Peak TVL* |
|---|---|---|
| [Aerodrome](https://defillama.com/protocol/aerodrome) | $372.0M | $1.25B (Dec 2024) |
| [Velodrome](https://defillama.com/protocol/velodrome) | $37.9M | $324.0M (Mar 2023) |
| [Fraxtal](https://defillama.com/protocol/fraxtal) | $168.9M | $281.2M (Jul 2025) |

<sub>*Fetched 2026-09-24 14:36 UTC. See [the update script](scripts/update_tvl.py) for details.</sub>
<!-- TVL:END -->

## Tokens I developed

<!-- TOKENS:START -->
**Protocol tokens**

| Token | Chain | Market cap* | Peak market cap* | Contract |
|---|---|---|---|---|
| veAERO | Base | $719.0M | $1.50B (Dec 2024) | [`0xeBf4…e6B4`](https://basescan.org/address/0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4) |
| veVELO | Optimism | $39.6M | $242.0M (Dec 2024) | [`0xFAf8…787d`](https://optimistic.etherscan.io/address/0xFAf8FD17D9840595845582fCB047DF13f006787d) |

**Frax LayerZero OFTs\*\***

| Token | Market cap* | Peak market cap* |
|---|---|---|
| frxUSD | $104.8M | $140.1M (May 2026) |
| sfrxUSD | $33.1M | $46.1M (Apr 2026) |
| frxETH | $164.0M | $1.20B (Mar 2024) |
| sfrxETH | $116.1M | $856.0M (Mar 2024) |
| FRAX (WFRAX, formerly FXS) | $26.7M | $226.9M (Sep 2025) |

<sub>\*\*Contract addresses on every chain: [Frax docs](https://docs.frax.com/protocol/crosschain/addresses).</sub>

**FXB bonds**

| Bond | Chain | Maturity | Value Issued* | Contract |
|---|---|---|---|---|
| FXB_20240630 | Ethereum | 2024-06-30 | $4.3M | [`0x0dE5…df1e`](https://etherscan.io/address/0x0dE54CFdfeD8005176f8b7A9D5438B45c4F1df1e) |
| FXB_20241231 | Ethereum | 2024-12-31 | $4.7M | [`0xF8FD…6F09`](https://etherscan.io/address/0xF8FDe8A259A3698902C88bdB1E13Ff28Cd7f6F09) |
| FXB20251231 | Fraxtal | 2025-12-31 | $3.6M | [`0xacA9…C6CA`](https://fraxscan.com/address/0xacA9A33698cF96413A40A4eB9E87906ff40fC6CA) |
| FXB_20261231 | Ethereum | 2026-12-31 | $6.0M | [`0x7623…4ff3`](https://etherscan.io/address/0x76237BCfDbe8e06FB774663add96216961df4ff3) |
| FXB20271231 | Fraxtal | 2027-12-31 | $4.3M | [`0x6c9f…A818`](https://fraxscan.com/address/0x6c9f4E6089c8890AfEE2bcBA364C2712f88fA818) |
| FXB20291231 | Fraxtal | 2029-12-31 | $12.7M | [`0xF1e2…2153`](https://fraxscan.com/address/0xF1e2b576aF4C6a7eE966b14C810b772391e92153) |
| FXB20551231 | Fraxtal | 2055-12-31 | $13.6M | [`0xc381…EA83`](https://fraxscan.com/address/0xc38173D34afaEA88Bc482813B3CD267bc8A1EA83) |

<sub>*Fetched 2026-09-24 14:36 UTC. See [the update script](scripts/update_tvl.py) for details.</sub>
<!-- TOKENS:END -->

## Design

<details>
<summary><b>Frax crosschain hub</b>: architecture diagram of Frax token flows across 17 chains</summary>
<br>
<a href="https://docs.frax.com/protocol/crosschain/addresses"><img src="assets/crosschain-hub.png" width="700" alt="Frax crosschain hub architecture diagram"></a>
</details>

<details>
<summary><b>FXB bonds</b>: architecture diagram of the FXB zero-coupon bond system and Bonds AMO auctions</summary>
<br>
<img src="assets/fxb-amo.png" width="700" alt="FXB bonds and Bonds AMO architecture diagram">
</details>
