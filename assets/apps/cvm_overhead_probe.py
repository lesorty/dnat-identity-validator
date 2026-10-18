#!/usr/bin/env python3
"""Sonda de overhead de substrato confidencial (SEV-SNP / TDX).

Roda DENTRO do contrato de execucao do DNAT (mesmo `workspace/run.sh`, mesmo
bundle, mesmo caminho HTTP) e serve a um proposito que a `benign_stats.py` nao
consegue cumprir: dar ao experimento CVM-vs-VM um tempo de execucao grande o
bastante, e um perfil de acesso a memoria estressante o bastante, para que o
custo do TEE apareca acima do ruido de medicao.

Motivacao. No modo direto (`DNAT_NO_MICROVM=1`) a execucao da app benigna sobre
60 linhas custa ~66 ms. O overhead de criptografia de memoria do SEV-SNP fica na
casa de 2-8%; sobre 66 ms isso e ~2-5 ms, indistinguivel do jitter de um
round-trip HTTP. Medir a diferenca exige uma carga cujo tempo seja dominado
por trabalho real.

Perfil. Tres fases separadas, cronometradas individualmente, cada uma
estressando um custo diferente do TEE:

  1. `first_touch` — aloca e escreve pela primeira vez o working set inteiro.
     Sob SEV-SNP/TDX cada pagina nova paga aceitacao/validacao (`pvalidate`,
     checagem de RMP), que a literatura reporta como o custo relativo mais alto
     do substrato confidencial.
  2. `memory` — passes repetidos de escrita e leitura sobre o working set ja
     residente. Isola a criptografia de memoria em estado estavel, sem o custo
     de aceitacao da fase 1.
  3. `cpu` — laco aritmetico inteiro sobre working set minimo. Serve de
     controle: deve ser praticamente insensivel ao TEE, entao qualquer
     diferenca aqui e ruido de plataforma, nao overhead confidencial.

Reportar as tres fases separadamente e o que permite escrever no artigo *onde*
o custo aparece, em vez de so um numero agregado.

Restricoes de projeto:
  - Apenas biblioteca padrao (o guest de execucao nao tem site-packages).
  - Working set default de 192 MiB, para caber com folga nos 512 MiB da microVM
    de execucao. Isso mantem a celula "microVM em VM comum" comparavel com as
    celulas em modo direto: as quatro rodam exatamente a mesma carga.
  - Deterministico: nenhum RNG, nenhuma dependencia de rede ou de relogio de
    parede alem da medicao.

Contrato do DNAT: python3 code/application.py --dataset data/dataset.csv
(o dataset e ignorado; existe so para satisfazer o run.sh gerado pelo harness).

Ajuste de duracao: PROBE_MEMORY_PASSES e PROBE_WORKING_SET_MIB por variavel de
ambiente, ou --passes / --working-set-mib. Alvo default ~10 s em 1 vCPU EPYC
Milan. Mantenha os MESMOS valores nas quatro celulas do experimento.
"""

import argparse
import hashlib
import json
import os
import sys
import time

MIB = 1024 * 1024


def _phase_first_touch(working_set_mib: int) -> tuple[bytearray, float]:
    """Aloca o working set e escreve nele pela primeira vez.

    `bytearray(n)` e zerado pelo alocador mas nem sempre materializa todas as
    paginas; a escrita explicita em passo de pagina garante que cada uma seja
    de fato tocada, que e o evento que dispara a aceitacao de memoria no guest
    confidencial.
    """
    total = working_set_mib * MIB
    t0 = time.perf_counter()
    buf = bytearray(total)
    for offset in range(0, total, 4096):
        buf[offset] = 0xA5
    elapsed = time.perf_counter() - t0
    return buf, elapsed


def _phase_memory(buf: bytearray, passes: int) -> tuple[float, str]:
    """Escreve e le o working set repetidas vezes, ja residente.

    A carga e deliberadamente dominada por `memcpy` (atribuicao de fatia), nao
    por hash: o SEV-SNP cobra na largura de banda de memoria, e SHA-256 com
    aceleracao de hardware e compute-bound, o que diluiria justamente o sinal
    que queremos. Por isso o digest e calculado uma unica vez, no fim, e serve
    so de checagem de corretude: se as tres celulas do experimento nao
    produzirem o mesmo digest, elas nao executaram a mesma carga e a comparacao
    nao vale.
    """
    total = len(buf)
    chunk = 8 * MIB
    view = memoryview(buf)

    t0 = time.perf_counter()
    for p in range(passes):
        pattern = bytes([(p * 31 + 7) & 0xFF]) * chunk
        # Escrita sequencial sobre todo o working set.
        for offset in range(0, total, chunk):
            end = min(offset + chunk, total)
            buf[offset:end] = pattern[: end - offset]
        # Copia interna: forca leitura + escrita no mesmo passe, dobrando o
        # trafego de memoria por iteracao.
        half = (total // 2 // chunk) * chunk
        for offset in range(0, half, chunk):
            buf[offset + half : offset + half + chunk] = view[offset : offset + chunk]

    hasher = hashlib.sha256()
    for offset in range(0, total, chunk):
        hasher.update(view[offset : min(offset + chunk, total)])
    digest = hasher.hexdigest()
    elapsed = time.perf_counter() - t0
    view.release()
    return elapsed, digest


def _phase_cpu(iterations: int) -> tuple[float, int]:
    """Laco aritmetico inteiro com working set que cabe em cache.

    Controle do experimento: sem trafego de memoria relevante, o TEE nao deveria
    cobrar nada aqui.
    """
    t0 = time.perf_counter()
    acc = 12345
    for i in range(iterations):
        acc = (acc * 1103515245 + 12345) & 0x7FFFFFFF
        acc ^= (acc >> 13)
    elapsed = time.perf_counter() - t0
    return elapsed, acc


def main() -> int:
    parser = argparse.ArgumentParser(description="Confidential-substrate overhead probe")
    parser.add_argument("--dataset", default="data/dataset.csv", help="ignorado; contrato do DNAT")
    parser.add_argument("--output", default="")
    parser.add_argument(
        "--working-set-mib",
        type=int,
        default=int(os.getenv("PROBE_WORKING_SET_MIB", "192")),
    )
    parser.add_argument(
        "--passes",
        type=int,
        default=int(os.getenv("PROBE_MEMORY_PASSES", "20")),
    )
    parser.add_argument(
        "--cpu-iterations",
        type=int,
        default=int(os.getenv("PROBE_CPU_ITERATIONS", "8000000")),
    )
    args, _unknown = parser.parse_known_args()

    wall0 = time.perf_counter()

    buf, first_touch_s = _phase_first_touch(args.working_set_mib)
    memory_s, digest = _phase_memory(buf, args.passes)
    del buf
    cpu_s, cpu_acc = _phase_cpu(args.cpu_iterations)

    total_s = time.perf_counter() - wall0

    bytes_touched = args.working_set_mib * MIB * args.passes
    result = {
        "probe": "cvm_overhead",
        "config": {
            "working_set_mib": args.working_set_mib,
            "memory_passes": args.passes,
            "cpu_iterations": args.cpu_iterations,
        },
        "phases_s": {
            "first_touch": round(first_touch_s, 6),
            "memory": round(memory_s, 6),
            "cpu": round(cpu_s, 6),
        },
        "total_s": round(total_s, 6),
        # Vazao derivada: escrita + leitura por passe.
        "memory_throughput_mibs": round((bytes_touched * 2 / MIB) / memory_s, 2) if memory_s else 0,
        # Invariantes de corretude: devem bater entre TODAS as celulas do experimento.
        "digest": digest,
        "cpu_acc": cpu_acc,
    }

    print(f"[APP] processed probe in {result['total_s']:.3f}s "
          f"(first_touch={first_touch_s:.3f}s memory={memory_s:.3f}s cpu={cpu_s:.3f}s)")
    print("[APP] RESULT " + json.dumps(result))

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                json.dump(result, fh, indent=2)
            print(f"[APP] wrote result to {args.output}")
        except OSError as exc:
            print(f"[APP] failed to write output: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
