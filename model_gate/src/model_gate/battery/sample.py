"""Sorteio das âncoras públicas do S1 (T-302; composição na T-301, regras na E14 §5 e §7.2).

Âncora é o item nocivo que o pai recusa naquela condição. A cada veredito, o Juiz sorteia
PUBLIC_ANCHORS âncoras públicas por condição, estratificadas pelas categorias do StrongREJECT,
com uma semente que sai da chave secreta, do digest do derivado e da condição. O mesmo derivado
recebe sempre o mesmo sorteio; a reavaliação usa outra rodada (T-107).
"""

from __future__ import annotations

import hashlib
import hmac
import random

PUBLIC_ANCHORS = 32  # por condição (T-301): 48 âncoras = 32 públicas + 16 secretas


class InsufficientAnchors(Exception):
    """O pai recusa menos itens que o sorteio pede: a condição não é julgada (E14 §5)."""


def verdict_seed(key: bytes, derivative_digest: str, condition: str, judge_version: str, round_: int = 0) -> int:
    """Semente do sorteio: HMAC-SHA256 da chave secreta sobre (versão do Juiz, digest, condição, rodada)."""
    msg = "\x1f".join([judge_version, derivative_digest, condition, str(round_)]).encode()
    return int.from_bytes(hmac.new(key, msg, hashlib.sha256).digest()[:8], "big")


def quota(n: int, categories: list[str]) -> dict[str, int]:
    """Divide n igualmente entre as categorias; a sobra vai às primeiras em ordem alfabética."""
    cats = sorted(categories)
    base, extra = divmod(n, len(cats))
    return {c: base + (1 if i < extra else 0) for i, c in enumerate(cats)}


def draw_anchors(anchors_by_category: dict[str, list[int]], seed: int, n: int = PUBLIC_ANCHORS) -> list[int]:
    """Sorteia n âncoras estratificadas; devolve os IDs na ordem em que o Juiz os pergunta.

    Cada categoria recebe a sua cota. Se uma categoria tem menos âncoras que a cota, entram todas
    as dela, e a falta é sorteada entre as âncoras que sobraram nas outras categorias. Com menos
    de n âncoras no total, levanta InsufficientAnchors.
    """
    pools = {c: sorted(set(ids)) for c, ids in anchors_by_category.items()}
    total = sum(len(v) for v in pools.values())
    if total < n:
        raise InsufficientAnchors(f"{total} âncoras, o sorteio pede {n}")
    rng = random.Random(seed)
    q = quota(n, list(pools))
    chosen: list[int] = []
    leftovers: list[int] = []
    for c in sorted(pools):
        ids = pools[c][:]
        rng.shuffle(ids)
        take = min(q[c], len(ids))
        chosen += ids[:take]
        leftovers += ids[take:]
    missing = n - len(chosen)
    if missing:
        leftovers.sort()
        rng.shuffle(leftovers)
        chosen += leftovers[:missing]
    rng.shuffle(chosen)
    return chosen
