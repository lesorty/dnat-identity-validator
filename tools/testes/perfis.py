"""O que muda entre os perfis, num lugar só.

mini:   verificação no notebook, em CPU: prereg de fumaça, bateria local pequena, detector de recusa como
        avaliador e como "juiz de referência", derivados minúsculos. Minutos; NÃO é dado do artigo.
ensaio: os mesmos tamanhos do mini, mas na VM com GPU e com os modelos de verdade (Qwen3Guard no portão,
        juiz de referência no rótulo), fatias em paralelo e lotes. É a primeira coisa a rodar na VM: em
        ~20-30 min mostra que tudo carrega e roda na GPU, e quanto tempo cada passo leva, antes de gastar
        horas. NÃO é dado do artigo.
piloto: a primeira rodada de verdade na VM com GPU (26/11): bem menor que a campanha, para ter resultados
        em poucas horas, conferir a metodologia de ponta a ponta e ter números de comparação antes de decidir
        com o orientador o tamanho da campanha. Prereg do piloto (um formato, uma condição, 24 âncoras),
        bateria reduzida (96 nocivos), 4 + 4 derivados, 3 do campo, 2 rodadas do atacante, e nenhum passo que
        só usa CPU por horas (sem cronômetro em 4 vCPU nem overhead). Uma rodada só, sem pausa: o T3 em diante
        usa direto a proposta de limiares do T2. NÃO é dado do artigo.
nuvem:  a campanha. Prereg provisório na fase 1 (T1, T2) e o prereg.yaml congelado depois (T3 em diante),
        bateria da campanha, Qwen3Guard-Gen-4B como avaliador do portão (T-309 em aberto) e o juiz de
        referência do judge.yaml (modelo exato em aberto, DECISOES.md 24/11). Na GPU.

`env` vai para o ambiente de cada passo (o de quem chamou vence). `silencio_min`: o executor mata o
passo que fica esse tempo sem escrever nada (travado), em vez de deixar a GPU parada cobrando.
"""
from __future__ import annotations

from executor import DATA, REPO, Ctx, prereg_complete

MGD = REPO / "model_gate"
EXP = MGD / "experiments" / "testes"

# Na GPU: o model_gate na placa, determinístico; o torch com CUDA foi instalado por cima do lock (preparar_testes.sh)
# e o uv não pode sincronizar de volta para o de CPU (UV_NO_SYNC).
GPU_ENV = {"MODEL_GATE_DISPOSITIVO": "cuda", "CUBLAS_WORKSPACE_CONFIG": ":4096:8", "UV_NO_SYNC": "1"}

PERFIL = {
    "mini": {
        "prereg_fase1": EXP / "prereg_mini.yaml",
        "prereg": EXP / "prereg_mini.yaml",
        "bateria": DATA / "battery" / "local_t807",
        "avaliador": "detector",
        "rotulo": "--avaliador detector --n-por-categoria 1 --n-seguros 4 --n-utilidade 4 --max-new-tokens 24",
        "threads": 4,
        "fixar_cpu": False,
    },
    "ensaio": {
        "prereg_fase1": EXP / "prereg_mini.yaml",
        "prereg": EXP / "prereg_mini.yaml",
        "bateria": DATA / "battery" / "local_t807",
        "avaliador": "qwen3guard",
        "rotulo": "--avaliador referencia --n-por-categoria 1 --n-seguros 4 --n-utilidade 4 --max-new-tokens 256 --lote 8",
        "threads": 4,
        "fixar_cpu": False,
        "env": {**GPU_ENV, "MG_PARALELO": "2"},
        "silencio_min": 30,
    },
    "piloto": {
        "prereg_fase1": EXP / "prereg_piloto.yaml",
        # sem revisão humana: o T3 em diante usa a proposta que o T2 do piloto calibrou
        "prereg": "$TESTE_DIR/../T2/passos/calibrar/prereg_proposto.yaml",
        "bateria": DATA / "battery" / "piloto",
        "bateria_args": "--n-harmful 96 --n-safe 20 --n-utility 16",
        "avaliador": "qwen3guard",
        "rotulo": "--avaliador referencia --n-por-categoria 4 --n-seguros 8 --n-utilidade 16 --max-new-tokens 512 --lote 16",
        "threads": 4,
        "fixar_cpu": False,
        "env": {**GPU_ENV, "MG_PARALELO": "2"},
        "silencio_min": 45,
    },
    "nuvem": {
        "prereg_fase1": EXP / "prereg_provisorio.yaml",
        "prereg": MGD / "prereg.yaml",
        "bateria": DATA / "battery" / "campanha",
        "avaliador": "qwen3guard",
        "rotulo": "--avaliador referencia --n-por-categoria 8 --n-seguros 12 --n-utilidade 32 --max-new-tokens 512 --lote 16",
        "threads": 4,
        "fixar_cpu": False,
        # 2 vereditos ao mesmo tempo: Qwen3Guard-4B em float32 (~16 GB) + base, derivado e cópias dos formatos,
        # por processo, cabem com folga na H100 de 80 GB; o ensaio mede o pico (gpu_mem_mb no sinal de vida).
        "env": {**GPU_ENV, "MG_PARALELO": "2"},
        "silencio_min": 60,
    },
}

PIN = "taskset -c 0-3 "   # 4 vCPU: onde o artigo mede o custo em CPU (G1)


# Comandos: rodados da raiz do repositório, no ambiente travado do model_gate (uv --frozen).
def mg(perfil: str, module: str, args: str = "") -> str:
    pin = PIN if PERFIL[perfil].get("fixar_cpu") else ""
    return f"cd model_gate && {pin}uv run --frozen python -m {module} {args}".rstrip()


def mg_cpu(module: str, args: str = "") -> str:
    """Na CPU de propósito, presa a 4 vCPU (custo G1, conferência CPU × GPU), em qualquer perfil."""
    return f"cd model_gate && MODEL_GATE_DISPOSITIVO=cpu {PIN}uv run --frozen python -m {module} {args}".rstrip()


def prereg_pronto(perfil: str) -> tuple:
    """Pré-voo dos testes que usam o prereg de depois da calibração (T3 em diante).
    nuvem: o model_gate/prereg.yaml preenchido (T-606) e congelado; piloto: a proposta do T2 do piloto."""
    if perfil == "nuvem":
        return (prereg_complete(),)
    if perfil == "piloto":
        def proposta(ctx: Ctx) -> str | None:
            # Antes de o T2 rodar, quem segura é a dependência (depende=T2): o pré-voo da rodada inteira não
            # deve barrar o que o próprio piloto vai produzir no caminho.
            t2 = ctx.dir.parent / "T2"
            f = t2 / "passos" / "calibrar" / "prereg_proposto.yaml"
            if f.exists() or not (t2 / "resumo.json").exists():
                return None
            return f"o T2 do piloto terminou sem a proposta de limiares ({f})"
        return (proposta,)
    return ()


def dep(test_id: str, step: str, name: str) -> str:
    """Arquivo que outro teste gravou (mesmo perfil e commit): $TESTE_DIR/../T03/passos/<passo>/<nome>."""
    return f"$TESTE_DIR/../{test_id}/passos/{step}/{name}"
