# Pretensões do artigo

**Alvo:** DSN 2027, Berlim (D1) · **Atualizado:** 2026-10-27 · Cronograma em [PLANO.md](PLANO.md).

## Tese (rascunho; o problema exato sai da [E10](etapas/E10_problema.md))

Modelos de pesos abertos perdem a recusa quando são modificados, por acidente (fine-tuning
legítimo) ou de propósito (obliteração), e as salvaguardas dentro dos pesos não resistem a quem
escreve neles. O DNAT trata modelos como uma **cadeia de suprimentos sob custódia**: pesos e
derivados nunca saem da CVM, e todo derivado passa por um **portão de liberação** que verifica, contra
a referência que só a plataforma guarda, se a recusa foi preservada.

## Contribuições candidatas

| # | Contribuição | Papel | Base |
|---|---|---|---|
| C1 | **Custódia + portão de liberação** de derivados: prevenção, detecção, contenção e recuperação | Principal (sistema) | D1, D2, [E8](etapas/E8_alinhamento_dsn.md) §9 |
| C2 | **Avaliação de dependabilidade** do portão: modelo de falhas com quantidade, verdade de referência independente, teste cego com obliterados de campo, atacante adaptativo | Principal (avaliação) | [E9](etapas/E9_testes_validos.md) §3 |
| C3 | **Controle de exportação** de pesos pela saída legítima | Secundária | [E6](etapas/E6_alt_modelos_abertos.md) §6 |
| C4 | **Bounty** para entradas ou derivados que explorem o modelo | Extensão ou trabalho futuro | Orientador, 2026-10-27 |

## Escopo

**Dentro:** custódia em CVM; portão em CPU com modelos pequenos; execução do job sem rede (D4).

**Fora, declarado como limitação ou trabalho futuro**
- Distribuição entre operadores e atestação detalhada (D3).
- Canais laterais e falhas de hardware na CVM (D3).
- Destilação por consultas e backdoors com gatilho (E6 §9).
- Modelos grandes em GPU confidencial (opcional).

## Histórico

- **LADC 2026:** isolamento de aplicações Python (tag `ladc-2026`).
- **2026-10-17/18:** Juiz de IA contra vazamento em código.
- **2026-10-27:** proteção de modelos abertos ([E7](etapas/E7_decisao_rumo.md), decidida com o orientador).
