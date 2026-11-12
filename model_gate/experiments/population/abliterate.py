"""Abliteração por ortogonalização dos pesos (F3; T-908; Arditi et al., 2024, §4.1).

Arditi mostra que tirar a direção de recusa r̂ do resíduo, em toda camada e posição, desfaz a
recusa; a mesma intervenção vira edição de pesos ortogonalizando contra r̂ toda matriz que
escreve no resíduo:

    W_out ← W_out − α · r̂ r̂ᵀ W_out       (o_proj e down_proj; peso do Linear em [d_model, d_in])
    W_E   ← W_E   − α · W_E r̂ r̂ᵀ         (embedding; [vocab, d_model])

Com α = 1 (a receita de Arditi) nenhuma escrita no resíduo tem componente em r̂. α em (0, 1]
é a fração da projeção removida, a intensidade da varredura; `layers` diz quais blocos têm a
saída ortogonalizada, e `embedding` se o embedding entra. A direção vem do pacote da T-402
(conferido pelo hash do conteúdo); `direction_layer` escolhe de qual camada ela sai. A escolha
dessa camada pelo efeito da intervenção é a T-414; a varredura da população F3 é a T-917.

Detalhes fixos (FIXED):
- direção renormalizada e conta em float64; volta ao dtype do arquivo do base (bf16 no Qwen2.5-0.5B), como um
  abliterado publicado; os tensores não editados saem byte a byte iguais ao base;
- embedding amarrado ao lm_head (tie_word_embeddings, o caso do Qwen2.5-0.5B): editar o
  embedding também edita a leitura, porque é o mesmo tensor; fica registrado em `tied_embeddings`;
- só arquivo único model.safetensors e matrizes de saída sem bias (Qwen2 e Llama); outro caso
  falha em vez de editar pela metade;
- os demais arquivos do base (config, tokenizer) são copiados sem mudança, e a recipe.json vai
  junto, como na T-901. O derivado é um modelo cheio, carregado por model_gate.io.load.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

import torch
from safetensors import safe_open
from safetensors.torch import load_file, save_file

from model_gate.io.load import dir_digest, model_files
from model_gate.signals.direction import load_direction

WEIGHTS = "model.safetensors"
EMBED = "model.embed_tokens.weight"
OUTPUTS = ("self_attn.o_proj", "mlp.down_proj")  # as matrizes de cada bloco que escrevem no resíduo
FIXED = {
    "formula": "W_out ← W_out − α r̂ r̂ᵀ W_out; W_E ← W_E − α W_E r̂ r̂ᵀ (Arditi 2024, §4.1)",
    "matrices": [f"model.layers.{{l}}.{m}.weight" for m in OUTPUTS],
    "compute_dtype": "float64, com r̂ renormalizada",
    "save_dtype": "o do arquivo do base",
}


@dataclass(frozen=True)
class AblationRecipe:
    """O que varia entre derivados F3. Nenhum padrão: tudo vem da receita."""
    name: str
    direction_layer: int       # camada do pacote da T-402 de onde sai r̂
    layers: tuple[int, ...]    # blocos com o_proj e down_proj ortogonalizados
    scale: float               # α: fração da projeção removida
    embedding: bool            # ortogonalizar também o embedding

    def __post_init__(self):
        if not 0 < self.scale <= 1:
            raise ValueError(f"scale fora de (0, 1]: {self.scale}")
        if not self.layers and not self.embedding:
            raise ValueError("receita sem nenhuma matriz para editar")
        if len(set(self.layers)) != len(self.layers) or list(self.layers) != sorted(self.layers):
            raise ValueError(f"layers deve ser crescente e sem repetição: {self.layers}")


def orthogonalize_out(w: torch.Tensor, r: torch.Tensor, scale: float) -> torch.Tensor:
    """Linear que escreve no resíduo: w [d_model, d_in], r [d_model] unitário. Em float64."""
    w64, r64 = w.to(torch.float64), r.to(torch.float64)
    return w64 - scale * torch.outer(r64, r64 @ w64)


def orthogonalize_embed(e: torch.Tensor, r: torch.Tensor, scale: float) -> torch.Tensor:
    """Embedding e [vocab, d_model]. Em float64."""
    e64, r64 = e.to(torch.float64), r.to(torch.float64)
    return e64 - scale * torch.outer(e64 @ r64, r64)


def edited_names(recipe: AblationRecipe) -> list[str]:
    names = [f"model.layers.{layer}.{m}.weight" for layer in recipe.layers for m in OUTPUTS]
    return ([EMBED] if recipe.embedding else []) + names


def abliterate_tensors(tensors: dict[str, torch.Tensor], r: torch.Tensor, recipe: AblationRecipe,
                       n_layers: int) -> tuple[dict[str, torch.Tensor], dict]:
    """Devolve um novo dicionário (o de entrada não muda) e o resíduo da projeção por matriz.

    Resíduo: max |r̂ᵀW| / max |W| depois de voltar ao dtype do arquivo (0 em aritmética exata com α=1).
    """
    r = r.to(torch.float64)
    if abs(float(r.norm()) - 1) > 1e-5:
        raise ValueError(f"direção não unitária: norma {float(r.norm())}")
    r = r / r.norm()  # o pacote é float32; renormalizar em float64 tira a projeção exatamente
    if any(layer < 0 or layer >= n_layers for layer in recipe.layers):
        raise ValueError(f"camada fora de 0..{n_layers - 1}: {recipe.layers}")
    out = dict(tensors)
    residual = {}
    for name in edited_names(recipe):
        if name not in tensors:
            raise KeyError(f"matriz ausente no base: {name}")
        if name != EMBED and name.replace(".weight", ".bias") in tensors:
            raise NotImplementedError(f"{name} tem bias; a receita não cobre esse caso")
        w = tensors[name]
        if w.shape[-1 if name == EMBED else 0] != r.shape[0]:
            raise ValueError(f"{name}: forma {tuple(w.shape)} não casa com d_model {r.shape[0]}")
        new = (orthogonalize_embed if name == EMBED else orthogonalize_out)(w, r, recipe.scale).to(w.dtype)
        out[name] = new.contiguous()
        proj = (new.to(torch.float64) @ r) if name == EMBED else (r @ new.to(torch.float64))
        residual[name] = float(proj.abs().max() / new.to(torch.float64).abs().max())
    return out, residual


@dataclass
class AblationResult:
    recipe: dict
    direction_sha256: str
    base_digest: str
    tied_embeddings: bool
    save_dtype: str
    out_dir: str
    digest: str
    max_residual: float

    def record(self) -> dict:
        return asdict(self)


def abliterate(base_dir: Path, base_digest: str, direction_path: Path, direction_sha256: str,
               recipe: AblationRecipe, out_dir: Path) -> AblationResult:
    """Gera o derivado F3 em out_dir a partir do base conferido por digest."""
    base_dir, out_dir = Path(base_dir), Path(out_dir)
    got, _ = dir_digest(base_dir)
    if got != base_digest:
        raise RuntimeError(f"{base_dir}: digest {got} != base custodiado {base_digest}")
    files = model_files(base_dir)
    if WEIGHTS not in files or any(f.endswith(".safetensors.index.json") for f in files):
        raise NotImplementedError("só base com arquivo único model.safetensors")
    pack = load_direction(direction_path, direction_sha256)
    if pack["meta"]["base_digest"] != base_digest:
        raise ValueError("o pacote da direção é de outro base")
    config = json.loads((base_dir / "config.json").read_text())
    n_layers = config["num_hidden_layers"]
    if pack["dirs"].shape[0] != n_layers:
        raise ValueError(f"pacote com {pack['dirs'].shape[0]} camadas, base com {n_layers}")
    r = pack["dirs"][recipe.direction_layer]
    if float(r.norm()) == 0:
        raise ValueError(f"direção nula na camada {recipe.direction_layer}")

    tensors = load_file(str(base_dir / WEIGHTS))
    with safe_open(str(base_dir / WEIGHTS), framework="pt") as f:
        metadata = f.metadata()
    dtypes = {str(t.dtype) for t in tensors.values()}
    if len(dtypes) != 1:
        raise ValueError(f"base com dtypes misturados: {dtypes}")
    new, residual = abliterate_tensors(tensors, r, recipe, n_layers)

    out_dir.mkdir(parents=True, exist_ok=True)
    for rel in files:
        if rel != WEIGHTS:
            (out_dir / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(base_dir / rel, out_dir / rel)
    save_file(new, str(out_dir / WEIGHTS), metadata=metadata)
    tied = bool(config.get("tie_word_embeddings", False))
    rec = {"recipe": asdict(recipe), "fixed": FIXED, "base_digest": base_digest,
           "direction_sha256": direction_sha256, "tied_embeddings": tied, "save_dtype": dtypes.pop(),
           "edited": edited_names(recipe)}
    (out_dir / "recipe.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    digest, _ = dir_digest(out_dir)
    return AblationResult(asdict(recipe), direction_sha256, base_digest, tied, rec["save_dtype"], str(out_dir),
                          digest, max(residual.values()))
