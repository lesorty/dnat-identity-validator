#!/usr/bin/env python3
"""Carga CPU-bound longa (~90s) — renderizador estilo raytracer.

Papel no experimento CVM-vs-VM: teste *demorado* e compute-dominado. Interseccao
raio-esfera, sombra e reflexao sao aritmetica de ponto flutuante sobre um working
set minimo (so o buffer da imagem), entao a carga e praticamente insensivel ao
custo de criptografia de memoria do SEV-SNP/TDX. Serve para responder "quanto o
TEE cobra em CPU pura?" (resposta esperada: quase nada) e para medir o overhead
de *inicializacao* do Firecracker sobre uma execucao longa (onde o boot fixo
pesa proporcionalmente menos que na carga rapida).

stdlib apenas (o guest nao tem site-packages), deterministico (sem RNG; o
`digest` do quadro renderizado deve bater entre TODAS as celulas).

Contrato DNAT: python3 code/application.py --dataset data/dataset.csv (ignorado).
Ajuste: RT_WIDTH / RT_HEIGHT / RT_SAMPLES / RT_BOUNCES por env ou argumento.
Defaults calibrados para ~90s em 1 vCPU EPYC Milan.
"""
import argparse
import json
import math
import os
import sys
import time


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def _norm(a):
    length = math.sqrt(_dot(a, a)) or 1.0
    return (a[0] / length, a[1] / length, a[2] / length)


# Cena fixa: chao (esfera gigante) + 4 esferas coloridas com reflectividade.
SPHERES = [
    ((0.0, -1000.0, 0.0), 1000.0, (0.5, 0.5, 0.5), 0.0),
    ((0.0, 1.0, 0.0), 1.0, (0.8, 0.3, 0.3), 0.4),
    ((-2.2, 1.0, -1.0), 1.0, (0.3, 0.8, 0.3), 0.2),
    ((2.2, 1.0, -1.0), 1.0, (0.3, 0.3, 0.8), 0.6),
    ((0.0, 0.5, 2.0), 0.5, (0.9, 0.9, 0.2), 0.3),
]
LIGHT = _norm((1.0, 2.0, 1.0))
CAM = (0.0, 1.5, 5.0)


def _hit(orig, d):
    best = None
    best_t = 1e30
    for c, r, col, refl in SPHERES:
        oc = _sub(orig, c)
        b = _dot(oc, d)
        cc = _dot(oc, oc) - r * r
        disc = b * b - cc
        if disc > 0.0:
            t = -b - math.sqrt(disc)
            if 1e-4 < t < best_t:
                best_t = t
                best = (c, r, col, refl)
    if best is None:
        return None
    p = _add(orig, _mul(d, best_t))
    c, r, col, refl = best
    n = _norm(_sub(p, c))
    return p, n, col, refl


def _trace(orig, d, depth):
    h = _hit(orig, d)
    if h is None:
        t = 0.5 * (d[1] + 1.0)
        return (1.0 - 0.5 * t, 1.0 - 0.3 * t, 1.0 - 0.1 * t)
    p, n, col, refl = h
    shadow = _hit(_add(p, _mul(n, 1e-3)), LIGHT)
    diff = max(0.0, _dot(n, LIGHT))
    if shadow is not None:
        diff *= 0.2
    local = _mul(col, 0.1 + 0.9 * diff)
    if refl > 0.0 and depth > 0:
        rd = _sub(d, _mul(n, 2.0 * _dot(d, n)))
        rc = _trace(_add(p, _mul(n, 1e-3)), _norm(rd), depth - 1)
        local = _add(_mul(local, 1.0 - refl), _mul(rc, refl))
    return local


def render(width, height, samples, bounces):
    aspect = width / height
    ns = samples * samples
    checksum = 0
    for j in range(height):
        for i in range(width):
            r = g = b = 0.0
            for sj in range(samples):
                for si in range(samples):
                    dx = (si + 0.5) / samples - 0.5
                    dy = (sj + 0.5) / samples - 0.5
                    px = (2.0 * (i + 0.5 + dx) / width - 1.0) * aspect
                    py = 1.0 - 2.0 * (j + 0.5 + dy) / height
                    d = _norm((px, py, -1.5))
                    col = _trace(CAM, d, bounces)
                    r += col[0]
                    g += col[1]
                    b += col[2]
            ir = int(min(1.0, r / ns) * 255)
            ig = int(min(1.0, g / ns) * 255)
            ib = int(min(1.0, b / ns) * 255)
            checksum = (checksum * 1000003 + ir + (ig << 8) + (ib << 16)) & 0xFFFFFFFFFFFFFFFF
    return checksum


def main() -> int:
    ap = argparse.ArgumentParser(description="CPU-bound raytracer workload")
    ap.add_argument("--dataset", default="data/dataset.csv", help="ignorado; contrato do DNAT")
    ap.add_argument("--output", default="")
    ap.add_argument("--width", type=int, default=int(os.getenv("RT_WIDTH", "2100")))
    ap.add_argument("--height", type=int, default=int(os.getenv("RT_HEIGHT", "1575")))
    ap.add_argument("--samples", type=int, default=int(os.getenv("RT_SAMPLES", "2")))
    ap.add_argument("--bounces", type=int, default=int(os.getenv("RT_BOUNCES", "3")))
    args, _unknown = ap.parse_known_args()

    t0 = time.perf_counter()
    checksum = render(args.width, args.height, args.samples, args.bounces)
    total_s = time.perf_counter() - t0

    rays = args.width * args.height * args.samples * args.samples
    result = {
        "probe": "cpu_raytrace",
        "config": {
            "width": args.width,
            "height": args.height,
            "samples": args.samples,
            "bounces": args.bounces,
            "primary_rays": rays,
        },
        "total_s": round(total_s, 6),
        "rays_per_s": round(rays / total_s, 1) if total_s else 0,
        # Invariante de corretude: mesmo checksum em TODAS as celulas.
        "digest": f"{checksum:016x}",
    }
    print(f"[APP] cpu_raytrace {args.width}x{args.height} spp={args.samples**2} "
          f"in {total_s:.3f}s ({result['rays_per_s']:.0f} rays/s)")
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
