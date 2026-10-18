#!/usr/bin/env python3
"""Carga I/O-bound longa (~90s) — escrita duravel (fsync) + leitura aleatoria.

Papel no experimento CVM-vs-VM: teste *demorado* dominado por I/O de
armazenamento, nao por CPU. Num guest confidencial a I/O de bloco passa por
bounce buffers de DMA (SWIOTLB, porque o dispositivo nao acessa memoria
criptografada diretamente), entao aqui o custo do TEE deve aparecer de forma
DIFERENTE da carga de CPU pura — e o contraste entre os dois e justamente o que
o experimento quer mostrar. Tambem expoe o custo da camada de bloco do
Firecracker (virtio-blk) na celula microVM.

Projeto para caber na microVM de 512 MiB: o arquivo e pequeno e FIXO; o tempo vem
do numero de passes de escrita duravel (fsync) sobre ele, nao do tamanho. Assim a
mesma carga roda identica nas quatro celulas.

stdlib apenas, deterministico: conteudo funcao do indice do bloco e leituras com
semente fixa, entao o `digest` deve bater entre TODAS as celulas.

Contrato DNAT: python3 code/application.py --dataset data/dataset.csv (ignorado).
Ajuste: IO_FILE_MB / IO_CHUNK_KB / IO_WRITE_PASSES / IO_RANDOM_READS / IO_DIR.
Defaults calibrados para ~90s em 1 vCPU com disco gerenciado Azure.
"""
import argparse
import hashlib
import json
import os
import random
import sys
import tempfile
import time


def _chunk_bytes(index: int, size: int) -> bytearray:
    # Padrao deterministico; os dois primeiros bytes variam por bloco para evitar
    # que dedup/compressao do storage escondam o custo real de escrita.
    buf = bytearray(size)
    seed = (index * 2654435761) & 0xFFFFFFFF
    for i in range(0, size, 512):
        buf[i] = (seed >> ((i // 512) % 24)) & 0xFF
    buf[0] = index & 0xFF
    buf[1] = (index >> 8) & 0xFF
    return buf


def main() -> int:
    ap = argparse.ArgumentParser(description="I/O-bound durable write + random read workload")
    ap.add_argument("--dataset", default="data/dataset.csv", help="ignorado; contrato do DNAT")
    ap.add_argument("--output", default="")
    ap.add_argument("--file-mb", type=int, default=int(os.getenv("IO_FILE_MB", "32")))
    ap.add_argument("--chunk-kb", type=int, default=int(os.getenv("IO_CHUNK_KB", "64")))
    ap.add_argument("--write-passes", type=int, default=int(os.getenv("IO_WRITE_PASSES", "38")))
    ap.add_argument("--random-reads", type=int, default=int(os.getenv("IO_RANDOM_READS", "30000")))
    ap.add_argument("--io-dir", default=os.getenv("IO_DIR", ""))
    args, _unknown = ap.parse_known_args()

    chunk = args.chunk_kb * 1024
    nchunks = (args.file_mb * 1024 * 1024) // chunk
    file_bytes = nchunks * chunk
    io_dir = args.io_dir or os.getcwd()

    fd, path = tempfile.mkstemp(dir=io_dir, prefix="iostress-", suffix=".bin")
    fsyncs = 0
    try:
        # --- fase de escrita duravel: passes repetidos, arquivo de tamanho fixo ---
        t0 = time.perf_counter()
        for _ in range(args.write_passes):
            os.lseek(fd, 0, os.SEEK_SET)
            for k in range(nchunks):
                os.write(fd, _chunk_bytes(k, chunk))
                os.fsync(fd)  # durabilidade -> latencia de storage domina
                fsyncs += 1
        write_s = time.perf_counter() - t0

        # --- fase de leitura aleatoria ---
        rnd = random.Random(0x5EED)  # semente fixa -> deterministico
        hasher = hashlib.sha256()
        t1 = time.perf_counter()
        for _ in range(args.random_reads):
            off = rnd.randrange(0, nchunks) * chunk
            os.lseek(fd, off, os.SEEK_SET)
            hasher.update(os.read(fd, 4096))
        read_s = time.perf_counter() - t1
        digest = hasher.hexdigest()[:16]
    finally:
        os.close(fd)
        try:
            os.unlink(path)
        except OSError:
            pass

    total_s = write_s + read_s
    written_mib = (file_bytes * args.write_passes) / (1024 * 1024)
    result = {
        "probe": "io_stress",
        "config": {
            "file_mb": args.file_mb,
            "chunk_kb": args.chunk_kb,
            "write_passes": args.write_passes,
            "random_reads": args.random_reads,
            "fsync_count": fsyncs,
        },
        "write_s": round(write_s, 6),
        "read_s": round(read_s, 6),
        "total_s": round(total_s, 6),
        "write_mibs": round(written_mib / write_s, 2) if write_s else 0,
        "reads_per_s": round(args.random_reads / read_s, 1) if read_s else 0,
        # Invariante de corretude: mesmo digest em TODAS as celulas.
        "digest": digest,
    }
    print(f"[APP] io_stress write={write_s:.3f}s read={read_s:.3f}s "
          f"({written_mib:.0f} MiB escritos, {fsyncs} fsync)")
    print("[APP] RESULT " + json.dumps(result))

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                json.dump(result, fh, indent=2)
        except OSError as exc:
            print(f"[APP] failed to write output: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
