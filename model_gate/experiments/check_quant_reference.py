"""T-501 (conferência da T-502): quantização própria × bitsandbytes numa amostra de matrizes do base.

Roda no ambiente descartável com o bitsandbytes sem dependências (cabeçalho de
experiments/probe_bitsandbytes.py). Para cada formato e matriz amostrada: fração de pesos em outro
código, erro máximo e médio entre os pesos desquantizados, e o erro máximo por bloco.

    /tmp/bnb/bin/python -I experiments/check_quant_reference.py <pasta do modelo> [n_matrizes] [semente]
"""
import glob
import json
import os
import random
import sys

import bitsandbytes.functional as F
import torch
from safetensors.torch import load_file

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from model_gate.formats.quant import BLOCKSIZE_4BIT, dequantize, quantize  # noqa: E402

model_dir = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
files = sorted(glob.glob(os.path.join(model_dir, "**", "*.safetensors"), recursive=True))
weights = {}
for f in files:
    weights |= load_file(f)
names = sorted(k for k, v in weights.items() if k.endswith(".weight") and v.dim() == 2 and "embed" not in k and "lm_head" not in k)
sample = sorted(random.Random(seed).sample(names, n))
out = {"model_dir": model_dir, "seed": seed, "matrices": sample, "formats": {}}
for fmt in ("nf4", "fp4", "int8"):
    rows = []
    for name in sample:
        w = weights[name].to(torch.float32)
        ours = dequantize(quantize(w, fmt))
        if fmt == "int8":
            cq, scale, _ = F.int8_vectorwise_quant(w.to(torch.float16))
            ref = cq.to(torch.float32) * (scale.to(torch.float32)[:, None] / 127.0)
        else:
            q, st = F.quantize_4bit(w, quant_type=fmt, blocksize=BLOCKSIZE_4BIT)
            ref = F.dequantize_4bit(q, st).to(torch.float32)
        diff = (ours - ref).abs()
        per_block = diff.reshape(-1, BLOCKSIZE_4BIT).amax(1) if diff.numel() % BLOCKSIZE_4BIT == 0 else diff.reshape(1, -1).amax(1)
        rows.append({
            "matrix": name, "numel": w.numel(),
            "frac_diff_code": float((diff > 1e-6 * (w.abs().max())).float().mean()),
            "max_abs_err": float(diff.max()), "mean_abs_err": float(diff.mean()),
            "max_err_per_block": float(per_block.max()),
            "max_quant_err_ours": float((ours - w).abs().max()),
        })
    out["formats"][fmt] = rows
print(json.dumps(out, indent=2))
