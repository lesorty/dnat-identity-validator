"""T-503: o bitsandbytes carrega o 0,5B em 8 e 4 bits (NF4, FP4) em CPU?

Uso (sem mexer no uv.lock: o bitsandbytes entra sem dependências, sobre o torch CPU do projeto):
    uv venv /tmp/bnb --python .venv/bin/python
    .venv/bin/python -c "import site; print(site.getsitepackages()[0])" > "$(/tmp/bnb/bin/python -c 'import site; print(site.getsitepackages()[0])')/project.pth"
    uv pip install --python /tmp/bnb/bin/python --no-deps bitsandbytes
    /tmp/bnb/bin/python -I experiments/probe_bitsandbytes.py ~/model_gate_data/models/Qwen__Qwen2.5-0.5B-Instruct
Não use `uv run --with bitsandbytes`: ele resolve o torch do PyPI (com CUDA) por cima do torch CPU.
Resultado em src/model_gate/formats/README.md.
"""
import json, sys, time, traceback, glob, os
import torch, transformers
out = {"torch": torch.__version__, "transformers": transformers.__version__}
try:
    import bitsandbytes as bnb
    out["bitsandbytes"] = bnb.__version__
except Exception as e:
    out["bitsandbytes_import_error"] = repr(e); print(json.dumps(out, indent=2)); sys.exit()
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
path = sys.argv[1]
snap = sorted(glob.glob(os.path.join(path, "**", "config.json"), recursive=True))
mdir = os.path.dirname(snap[0]) if snap else path
out["model_dir"] = mdir
tok = AutoTokenizer.from_pretrained(mdir)
msgs = [{"role": "user", "content": "What is the capital of France?"}]
ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt")
if not torch.is_tensor(ids): ids = ids["input_ids"]
cfgs = {"int8": BitsAndBytesConfig(load_in_8bit=True),
        "nf4": BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float32),
        "fp4": BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="fp4", bnb_4bit_compute_dtype=torch.float32)}
for name, q in cfgs.items():
    r = {}
    try:
        t = time.time()
        m = AutoModelForCausalLM.from_pretrained(mdir, quantization_config=q, device_map="cpu", torch_dtype=torch.float32)
        r["load_s"] = round(time.time() - t, 2)
        r["linear_types"] = sorted({type(x).__name__ for x in m.modules() if "Linear" in type(x).__name__})
        t = time.time()
        with torch.no_grad():
            g = m.generate(ids, max_new_tokens=12, do_sample=False)
        r["gen_s"] = round(time.time() - t, 2)
        r["text"] = tok.decode(g[0, ids.shape[1]:], skip_special_tokens=True)
        r["ok"] = True
        del m
    except Exception as e:
        r["ok"] = False
        r["error"] = f"{type(e).__name__}: {e}"[:600]
    out[name] = r
print(json.dumps(out, indent=2, ensure_ascii=False))
