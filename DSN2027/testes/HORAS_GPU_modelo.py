# Modelo de horas de VM com GPU por teste e perfil (DSN2027/testes/HORAS_GPU.md). Rode: python3 -I HORAS_GPU_modelo.py
# Modelo de horas de GPU por teste. Unidades em minutos; (baixo, central, alto).
V   = (15, 25, 40)    # veredito de 1 derivado na GPU, lote 1, um processo
PAR = 1.8             # ganho de MG_PARALELO=2
PAI = (100, 150, 200) # referência do pai com o acervo inteiro (313 nocivos x 2 formatos x 2 condições)
PAI_RED = tuple(x*0.5 for x in PAI)  # acervo de ~150 nocivos
ROT = (4, 6, 10)      # rótulo de 1 modelo (gpt-oss-20b, lote 16), com a carga amortizada
LOAD = 3              # carga do gpt-oss por passo
LORA, ABL = 2.5, 1.0
PRE = 1.15            # preempção Spot + reinícios

def v(n, par=True, i=1): return n * V[i] / (PAR if par and n > 1 else 1)
def rot(n, i=1): return (n + 1) * ROT[i] + LOAD  # +1: o pai, uma vez por passo (cache depois)
def pop(nl, na): return nl*LORA + na*ABL

def perfis(i):
    m = {}
    # ---------- ROBUSTO ----------
    m["robusto"] = {
      "Preparo + ensaio": 60 + 45,
      "T1": 10 + PAI[i] + v(3, i=i),
      "T2 (20: 10H/10C)": 5 + pop(16, 4) + v(20, i=i) + rot(20, i),
      "T3 (56: 20H/36C, com F0)": pop(44, 12) + v(56, i=i) + rot(56, i),
      "T4+T5 Llama (pai Llama + 13)": 2*PAI[i] + 1.5*v(13, i=i) + rot(13, i) + 30,
      "T5 (8 Qwen)": 5 + v(8, i=i) + rot(8, i),
      "T6 (15 rodadas + LoRA de disfarce)": 15*(V[i] + ABL) + 5*ROT[i] + 6*LORA + 20,
      "T7 (forjada completa)": PAI[i] + 2*V[i],
      "T8": 2*V[i] + 10,
      "T9-T11 (só hashcat na GPU)": 5,
    }
    # ---------- MEDIANO ----------
    m["mediano"] = {
      "Preparo + ensaio": 60 + 45,
      "T1": 10 + PAI[i] + v(3, i=i),
      "T2 (12: 6H/6C)": 5 + pop(9, 3) + v(12, i=i) + rot(12, i),
      "T3 (20: 10H/10C)": pop(15, 5) + v(20, i=i) + rot(20, i),
      "T5 (8 Qwen)": 5 + v(8, i=i) + rot(8, i),
      "T6 (3 rodadas)": 3*(V[i] + ABL) + 2*ROT[i] + LOAD,
      "T7 (forjada completa)": PAI[i] + 2*V[i],
      "T8": 2*V[i] + 10,
      "T9-T11 (só hashcat na GPU)": 5,
    }
    # ---------- SIMPLES ----------
    m["simples"] = {
      "Preparo (disco pronto) + ensaio": 15 + 30,
      "T1 (acervo ~150)": 10 + PAI_RED[i] + v(3, i=i),
      "T2 (8: 4H/4C)": 5 + pop(6, 2) + v(8, i=i) + rot(8, i),
      "T3 (12: 6H/6C)": pop(9, 3) + v(12, i=i) + rot(12, i),
      "T5 (8 Qwen)": 5 + v(8, i=i) + rot(8, i),
      "T6 (3 rodadas)": 3*(V[i] + ABL) + 2*ROT[i] + LOAD,
      "T7 (forjada com bateria reduzida)": PAI_RED[i]*0.5 + 2*V[i],
      "T8 (aproveita o T3)": 2*V[i] + 10,
      "T9-T11 (só hashcat na GPU)": 5,
    }
    return m

res = [perfis(i) for i in range(3)]
for p in res[1]:
    print(f"\n## {p}")
    tot = [0,0,0]
    for k in res[1][p]:
        h = [res[i][p][k]/60 for i in range(3)]
        tot = [a+b for a,b in zip(tot,h)]
        print(f"{k:40s} {h[1]:5.1f} h  ({h[0]:.1f}-{h[2]:.1f})")
    print(f"{'soma':40s} {tot[1]:5.1f} h  ({tot[0]:.1f}-{tot[2]:.1f});  x{PRE} preempção: {tot[1]*PRE:.0f} h ({tot[0]*PRE:.0f}-{tot[2]*PRE:.0f})")

# Clopper-Pearson com 0 escapes: limite superior do IC 95% bilateral
print()
for n in (4,6,8,10,13,18,20,30,36,40):
    print(n, f"0/{n}: sup IC95 = {1-0.025**(1/n):.3f}")
# CPU do T1 (cpu-x-gpu) na VM com GPU
gens = 4*(313+100); toks = gens*215
print("pai na CPU:", gens, "gerações", toks/15/3600, "h gerando +", gens*50.1/3600, "h avaliador")
print("huihui na CPU:", 228*250/15/3600 + 263.9/60, "h")
