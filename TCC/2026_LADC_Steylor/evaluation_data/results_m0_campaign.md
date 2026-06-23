# DNAT — M0 Campaign (no-isolation baseline vs A vs B, same host)

> Third evaluation campaign, run on **2026-06-23**, that adds the no-isolation
> baseline **M0** to the comparison. All three environments were measured **on the
> same host, back to back**, with the same execution-plane harness
> (`assets/tests/run_execution_plane_tests.sh`), so the numbers are directly
> comparable. M0 is the centralized baseline image (`dnat-baseline`) run with
> `DNAT_NO_MICROVM=1`, which makes the executor run `vm/run-direct.sh` (the same
> `workspace/run.sh` contract, but directly in the container — no Firecracker, no
> disk isolation, no network removal). Nothing is estimated.

## Measurement environment

| Item | Value |
|------|-------|
| Host | Linux 6.17 + Docker 29.3.1; `/dev/kvm` present |
| M0 | `dnat-m0` (image `dnat-m0`=`dnat-baseline`, `DNAT_NO_MICROVM=1`), executor host :6000 → container :5000, `mode=direct` |
| A | `dnat-baseline`, executor host :4000 (Firecracker microVM, no network) |
| B | `dnat-executor`, executor host :5000 (Firecracker microVM, no network) |
| Dataset | `assets/data/dataset_synthetic.csv`, 60 rows |
| Harness | `run_execution_plane_tests.sh` (t1_network_exfil, t1b_fs_escape, benign_stats) |

## Operational cost — execution latency (wall-clock, ms)

| Application | M0 | A | B |
|-------------|---:|---:|---:|
| benign_stats (clean exec) | **66** | 25212 | 25201 |
| t1b_fs_escape | 77 | 25216 | 25204 |
| t1_network_exfil | 8617$^{*}$ | 25710 | 25752 |

$^{*}$ M0's `t1_network_exfil` is inflated by the application's own network
timeouts (M0 actually reaches the network, so blocked-by-routing probes wait on
`TimeoutError`); it is not microVM overhead. The **benign app is the clean
execution-latency comparator**.

**Headline numbers.**
- M0 clean execution ≈ **0.07 s** (66 ms); A ≈ B ≈ **25.2 s**.
- **microVM life-cycle overhead = A − M0 ≈ 25.1 s** — the application compute over
  60 rows is ~tens of milliseconds, so essentially the whole 25.2 s in A/B is the
  microVM (boot, disk discovery, output sync, guarded shutdown).
- **A ≈ B** (25.212 vs 25.201 s): compartmentalization adds no execution cost,
  consistent with the earlier A/B campaign (26.8 s; host warmth differs, the
  A≈B relationship does not).

## Security delta (the point of M0)

| Observation | M0 | A | B |
|-------------|----|----|----|
| Network interfaces in guest | `['eth0','lo']` | none usable | none usable |
| T1 exfiltration | **SUCCEEDED** (5/7 channels; 2 only failed on network timeout) | FAILED | FAILED |
| T1b control-plane secrets found | **6** (`ASSET_ENCRYPTION_KEY`, `PRIVATE_KEY`, `RPC_URL`, `IPFS_API_URL`, `BUILDER_URL`, `EXECUTOR_URL`) | 0 | 0 |
| T1b writes outside workspace | persist (`/persisted`, `/mnt/dnat-app`, `/tmp/exec`) | ephemeral (destroyed at teardown) | ephemeral |

Interpretation: removing the microVM removes the containment. M0 — the same logic
without the execution sandbox — reaches the network, sees the control-plane
secrets, and persists its writes; A and B (Firecracker, no network, ephemeral)
do not. This quantifies, on the cost side, what the ~25 s buys on the security
side.

## What this fills in the paper

- `tab:comparison`: row *Execution latency* (M0 0.07 / A 25.2 / B 25.2 s) and
  *microVM boot/life-cycle overhead* (M0 ≈0 / A ≈25.1 / B ≈25.1 s).
- Build rows for M0: **not differentiated** — M0 keeps the unchanged build
  microVM (only execution is direct), so M0 build cost = A.
- Still pending: blockchain gas (B7.5) and the SGX reference column (cite).
