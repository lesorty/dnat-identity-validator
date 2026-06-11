#!/usr/bin/env python3
"""T1 - Teste de resistencia a exfiltracao de rede (execution plane / CVM3).

Esta aplicacao simula codigo malicioso submetido por um comprador que tenta
abrir canais de saida a partir da microVM de execucao para vazar o dataset.
Ela NAO e uma aplicacao legitima: existe apenas para a avaliacao de seguranca
da Secao de Evaluation do artigo.

Contrato de execucao do DNAT (ver run_from_cids.py):
    python3 code/application.py --dataset data/dataset.csv

A aplicacao tenta varios vetores de exfiltracao e imprime, em stdout, um
relatorio determinista com marcadores greppaveis:
    [T1] EXFILTRATION SUMMARY blocked=<n> succeeded=<n>
    [T1] OVERALL: EXFILTRATION FAILED   (nenhum canal aberto -> isolamento OK)
    [T1] OVERALL: EXFILTRATION SUCCEEDED (ao menos um canal aberto -> falha)

Saida sempre com codigo 0 para que o orquestrador capture o relatorio na
primeira estrategia de invocacao.
"""

import argparse
import json
import socket
import struct
import sys
import urllib.request
from pathlib import Path

# Destinos publicos usados apenas para PROVAR tentativa de saida.
# Nenhum dado real e enviado; o payload e um marcador inocuo.
EXFIL_TARGETS = [
    ("dns-udp", "8.8.8.8", 53, "udp"),
    ("dns-tcp", "8.8.8.8", 53, "tcp"),
    ("https", "1.1.1.1", 443, "tcp"),
    ("http", "93.184.216.34", 80, "tcp"),  # example.com
    ("smtp", "142.250.0.0", 25, "tcp"),
]

EXFIL_MARKER = b"DNAT-T1-EXFIL-PROBE"


def list_interfaces() -> list[str]:
    net = Path("/sys/class/net")
    if not net.is_dir():
        return []
    return sorted(p.name for p in net.iterdir())


def try_tcp(host: str, port: int, timeout: float = 4.0) -> tuple[bool, str]:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.sendall(EXFIL_MARKER)
        s.close()
        return True, "connected+sent"
    except Exception as exc:  # noqa: BLE001 - queremos registrar o motivo do bloqueio
        return False, f"{type(exc).__name__}: {exc}"


def try_udp(host: str, port: int, timeout: float = 4.0) -> tuple[bool, str]:
    # UDP nao tem handshake; consideramos "aberto" apenas se conseguirmos
    # enviar E receber alguma resposta, evitando falso-positivo de send-only.
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        # Consulta DNS minima por example.com para provocar resposta real.
        query = build_dns_query("example.com")
        s.sendto(query, (host, port))
        data, _ = s.recvfrom(512)
        s.close()
        return (len(data) > 0), f"received {len(data)} bytes"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def build_dns_query(domain: str) -> bytes:
    tid = 0x1234
    flags = 0x0100  # recursion desired
    header = struct.pack(">HHHHHH", tid, flags, 1, 0, 0, 0)
    qname = b"".join(
        struct.pack("B", len(part)) + part.encode() for part in domain.split(".")
    ) + b"\x00"
    question = qname + struct.pack(">HH", 1, 1)  # A, IN
    return header + question


def try_http_get(timeout: float = 4.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen("http://example.com/", timeout=timeout) as resp:
            body = resp.read(64)
        return True, f"http {resp.status} ({len(body)} bytes)"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def try_dns_resolution(host: str = "example.com") -> tuple[bool, str]:
    try:
        addr = socket.gethostbyname(host)
        return True, f"resolved -> {addr}"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="DNAT T1 network exfiltration probe")
    parser.add_argument("--dataset", default="data/dataset.csv")
    parser.add_argument("--output", default="")
    args, _unknown = parser.parse_known_args()

    report: dict = {"test": "T1-network-exfiltration", "channels": {}}

    interfaces = list_interfaces()
    report["interfaces"] = interfaces
    print(f"[T1] network interfaces visible to guest: {interfaces}")

    # Tamanho do dataset que seria exfiltrado (apenas para contexto, nao enviado).
    ds = Path(args.dataset)
    report["dataset_present"] = ds.is_file()
    report["dataset_size_bytes"] = ds.stat().st_size if ds.is_file() else 0
    print(f"[T1] dataset present={report['dataset_present']} size={report['dataset_size_bytes']}B")

    blocked = 0
    succeeded = 0

    def record(name: str, ok: bool, detail: str) -> None:
        nonlocal blocked, succeeded
        report["channels"][name] = {"opened": ok, "detail": detail}
        if ok:
            succeeded += 1
            print(f"[T1] {name}: EXFILTRATION SUCCEEDED ({detail})")
        else:
            blocked += 1
            print(f"[T1] {name}: EXFILTRATION FAILED ({detail})")

    ok, detail = try_dns_resolution()
    record("dns-resolution", ok, detail)

    for name, host, port, proto in EXFIL_TARGETS:
        if proto == "tcp":
            ok, detail = try_tcp(host, port)
        else:
            ok, detail = try_udp(host, port)
        record(f"{name}({host}:{port}/{proto})", ok, detail)

    ok, detail = try_http_get()
    record("http-urllib(example.com:80)", ok, detail)

    report["blocked"] = blocked
    report["succeeded"] = succeeded
    overall_failed = succeeded == 0

    print(f"[T1] EXFILTRATION SUMMARY blocked={blocked} succeeded={succeeded}")
    if overall_failed:
        print("[T1] OVERALL: EXFILTRATION FAILED")
    else:
        print("[T1] OVERALL: EXFILTRATION SUCCEEDED")

    print("[T1] JSON " + json.dumps(report))

    if args.output:
        try:
            Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
