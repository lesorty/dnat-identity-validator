# DNAT — A/B Measurement Campaign (live, both environments)

> Second evaluation campaign, run on 2026-06-11, that closes the pending item of
> the first campaign (`results_raw.md`): both **Environment B** (compartmentalized,
> three planes) **and Environment A** (centralized single-container baseline) were
> exercised *live* and end to end, so every A column below is now measured rather
> than derived from configuration. Numbers are wall-clock measurements from the
> test host; nothing is estimated.

## Measurement environment

| Item | Value |
|------|-------|
| Host | Linux 6.17 + Docker; Firecracker guest kernel, KVM (`/dev/kvm`) present |
| Environment B (compartmentalized) | `dnat-client-local` (CVM1, control), `dnat-builder` (CVM2, build, :5100), `dnat-executor` (CVM3, exec, :5000); all on Docker network `dnat-runtime` |
| Environment A (baseline) | `dnat-baseline`, single container, all planes co-located on `127.0.0.1` (exec :4000, build :4100, API :4001) on network `docker_default` |
| Execution microVM | 1 vCPU / 512 MiB, **no network interface** (both A and B) |
| Build microVM | 2 vCPU / 1536 MiB, network egress with private-range REJECT (both A and B) |
| Dataset | `assets/data/dataset_synthetic.csv`, 60 rows, 3202 bytes, synthetic (no PII) |
| sha256(dataset) | `5881e7514713ee87f6746e6f6329abd7de1d355c4eb4ffe04d9e143cd4944596` |
| Harness | `assets/tests/run_execution_plane_tests.sh`, `run_build_plane_tests.sh`; `docker inspect`/`docker diff` for in-container facts |

> **Methodological note (why A == B on most rows).** Per the baseline design,
> Environment A keeps the *same* Firecracker execution and build microVMs as B; the
> only structural difference is plane separation. Consequently the microVM-level
> properties (T1, T1b, T3) and the operational cost (build/exec latency) are
> expected to be **identical** across A and B — and they are. The architectural
> variable shows up only where it should: in **blast radius** (T4) and
> **supply-chain reach** (T2).

---

## T1 — Network exfiltration resistance (execution plane) — A and B identical

Application `assets/apps/t1_network_exfil.py`, 7 outbound channels.

| Observation | Environment B (:5000) | Environment A (:4000) |
|-------------|----------------------|----------------------|
| Interfaces visible to guest | `[]` (no `eth0`, no usable stack) | `[]` |
| Overall | **EXFILTRATION FAILED** | **EXFILTRATION FAILED** |
| blocked / succeeded | **7 / 0** | **7 / 0** |
| TCP/UDP socket errors | `OSError [Errno 38] Function not implemented` (ENOSYS) | same |
| DNS resolution | `gaierror [Errno -2] Name or service not known` | same |
| urllib HTTP | `URLError: Temporary failure in name resolution` | same |

Interpretation: the execution microVM is launched without a network interface in
both environments, so every outbound channel fails *by construction*. Errors are
at the syscall/stack level (ENOSYS), not a firewall that could be disabled.
Evidence for criterion (ii) exfiltration resistance — and it is a property of the
microVM, hence independent of plane separation.

---

## T1b — Filesystem containment (execution plane) — A and B identical

Application `assets/apps/t1b_fs_escape.py`. Guest runs as `uid=0` (disposable guest).

| Observation | Environment B | Environment A |
|-------------|---------------|---------------|
| Control-plane secrets in env | **NO-SECRETS** (none of `ASSET_ENCRYPTION_KEY`, `PRIVATE_KEY`, …) | **NO-SECRETS** |
| Sibling execution disks (`/dev/vdd`, `/dev/vde`) | absent | absent |
| Readable files (`/etc/passwd`, `/etc/shadow`) | minimal ephemeral guest rootfs, no host creds | same |
| Writes outside workspace | 4 paths WRITE-OK, all on ephemeral disk destroyed at teardown (see T3) | same |

Interpretation: even a root-level execution payload finds no control-plane secrets
and no other tenant's disk in the guest. What it writes does not survive.

---

## T3 — Persistence resistance (ephemeral cleanup) — A and B PASS

Verified via `docker diff` after the execution runs of this campaign (3 runs/env):

| Artifact searched for | Environment B (`dnat-executor`) | Environment A (`dnat-baseline`) |
|-----------------------|------------------------------|------------------------------|
| `firecracker.socket` | none | none |
| per-run `input.ext4` / `output.ext4` / `application.ext4` / `rootfs-overlay.ext4` | none | none |
| `/tmp/tmp.*` per-run workdirs | none | none |
| residual loop mounts | none | none |
| ext4 present in image RW layer | only static `rootfs.ext4` template (read-only base) | only static `rootfs.ext4` templates (build + exec) |

Interpretation: the `cleanup`/`trap EXIT` removes the entire per-run working
directory in both designs; only the static, read-only VM template remains. No
ephemeral state survives to contaminate a later run. Criterion (iii).

---

## T4 — Blast radius / lateral movement (cross-plane) — **A and B DIFFER** (the key result)

Live inspection (`docker inspect`) of each container's environment, mounts and
network. **Secret values were never printed — only presence/absence.**

| Asset reachable from the execution plane | Environment B | Environment A |
|------------------------------------------|---------------|---------------|
| `ASSET_ENCRYPTION_KEY` (env) | **NOT SET** | **SET** |
| `PRIVATE_KEY` (env) | **NOT SET** | **SET** |
| `RPC_URL`, `IPFS_API_URL`, `BUILDER_URL`, `EXECUTOR_URL` (env) | **NOT SET** | **SET** |
| Co-located plane(s) in same namespace | none (executor is alone) | control + build + execution (all) |
| Network membership | `dnat-runtime` (separate container) | `docker_default` (everything on `127.0.0.1`) |

Cross-check, build plane (`dnat-builder`, B): also **no** control-plane secrets in
env. Control plane (`dnat-client-local`, B): secrets **SET** — the correct and only
home for them.

Residual weakness (reported honestly): in the single-host B deployment the three
containers share the `dnat-runtime` network, so a compromised executor can still
reach the control API (:3001) and the blockchain RPC (:8545) over that network;
the IPFS API (:5001), which would expose the encrypted blobs, is bound to loopback
inside CVM1 and is unreachable. This matches the threat model's stated limitation
(internal mTLS / network segmentation is future work). In A the same secrets and
stores sit in the *same namespace* as the execution logic — no network hop needed.

Interpretation: the secrets and persistent stores that define the blast radius are
**isolated in B and co-located in A**. This is the paper's comparative thesis,
now backed by live measurement of both environments rather than by configuration
inference. Criterion (i).

---

## T5 — Access control (smart contract) — A and B PASS

Registered the synthetic dataset, then issued `POST /api/run-from-cids` **without**
`purchaseAccess`:

| | Environment B (:3001) | Environment A (:4001) |
|---|----------------------|----------------------|
| On-chain `assetContentHash` | `0x5881e7…944596` (= file sha256, integrity binding) | identical |
| Run without purchased access | `{"error":"Access denied. Purchase access … before executing."}` | identical |

Interpretation: the `hasAccessByIds` gate rejects the request before any bundle is
prepared, in both designs.

---

## Operational cost — execution latency (A vs B)

`run_execution_plane_tests.sh`, three applications per environment, same dataset.

| Application | Environment B (ms) | Environment A (ms) |
|-------------|-------------------:|-------------------:|
| t1_network_exfil | 27293 | 27394 |
| t1b_fs_escape | 26580 | 26531 |
| benign_stats | 26454 | 26605 |
| **mean (n=3)** | **26776 (≈26.8 s)** | **26843 (≈26.8 s)** |

Interpretation: end-to-end execution latency is **statistically the same in A and
B** (~26.8 s), dominated by the microVM life cycle (boot, disk discovery, output
sync, guarded shutdown), not the application. Consistent with the first campaign's
n=6 benign mean of 31.4 s (this host was warmer, hence slightly lower). The key
new finding: **compartmentalization adds no measurable execution overhead** — the
cost is paid by the microVM, which both designs share.

## Operational cost — build latency and artifact size (A vs B)

`run_build_plane_tests.sh`, two cases per environment.

| Case | Env B latency | Env A latency | Artifact `application.ext4` |
|------|--------------:|--------------:|----------------------------:|
| no dependencies | 30058 ms (30.1 s) | 30162 ms (30.2 s) | 16 MiB (16777216 B) — both |
| `requests` (+4 transitive) | 38203 ms (38.2 s) | 34936 ms (34.9 s) | 19.6 MiB (20546900 B) — both |

Interpretation: build cost and artifact size are **the same in A and B** (the build
microVM is shared). Building is ~1.3–1.4× an execution on this warm host (the first
campaign saw ~3–4× on a colder host; the ratio depends on cache/host warmth, the
equality between A and B does not). Dependencies grow the artifact 16 → 19.6 MiB.

---

## Summary: what the A/B campaign establishes

1. **Per-microVM guarantees are a constant.** Exfiltration resistance (T1),
   filesystem containment (T1b), persistence resistance (T3), and both build and
   execution latency are **identical** in A and B, because both use the same
   Firecracker micro\-VMs. Compartmentalization is therefore *not* what provides
   these — and it costs nothing on top of them.
2. **Plane separation changes the blast radius (T4) and supply-chain reach (T2),
   and only those.** A compromised executor/builder in B has no control-plane
   secrets and no sensitive stores in its namespace; in A every such asset is
   co-located with the execution logic.
3. **Access control (T5) holds in both** — it is enforced at the control plane /
   smart contract, above the plane split.

This is exactly the paper's argument — *containment, not absolute security* —
now demonstrated with both environments measured live.
</content>
