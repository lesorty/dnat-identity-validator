# Pretensões do artigo

**Alvo:** DSN 2027, Berlim (D-033) · **Atualizado:** 2026-10-18 · Cronograma em [PLANO.md](PLANO.md).

## Tese (rascunho)

Um sistema de computação confidencial para marketplace de dados e aplicações, em que as
aplicações são **imagens OCI** executadas em CVMs de uso único, e em que a segurança das
aplicações frente aos dados é verificada por um **Juiz de IA que é, ele próprio, uma aplicação
do sistema**.

## Contribuições

| # | Contribuição | Papel | Base |
|---|---|---|---|
| C1 | **Juiz de IA** em camadas contra vazamento pelo canal de saída | **Principal** | D-032, [JUIZ_IA.md](JUIZ_IA.md) |
| C2 | **Juiz como aplicação do sistema**: mesmo pipeline confidencial, whitelist, entrada = outra app | Arquitetural; escalável e *future proof* | D-032 |
| C3 | **Benchmark** de apps com vazamento escondido (não existe hoje) | Artefato | JUIZ_IA §6–§7 |
| C4 | **Aplicações em OCI** executadas em CVM, container sem rede | Pré-requisito e generalização | D-010, D-011, [E2](etapas/E2_isolamento_confidencial.md), [E2b](etapas/E2b_build_oci.md) |

**Ordem de trabalho:** C4 (mínimo) primeiro, depois C1 + C2 + C3.

## O que muda em relação ao LADC 2026

| Antes | Agora |
|---|---|
| Contribuição lida como "isolamento bem engenheirado" | Contribuição é o **Juiz de IA**: um resultado novo |
| Só Python + wheels em ext4 | Qualquer aplicação em imagem OCI |
| Firecracker, que não roda em CVM (A14) | CVM de uso único por job, container sem rede |
| Vazamento pelo resultado fora de escopo | É o alvo do Juiz (D-014) |

## Escopo

**Dentro:** build e execução de OCI em CVM; Juiz como app whitelisted; dataset cifrado (D-018).

**Fora, declarado como limitação ou trabalho futuro**
- Distribuição entre operadores (D-031): o operador segue como ponto único de disponibilidade e censura.
- Atestação detalhada (implícita, D-017).
- Canais encobertos e laterais (D-014).
- Imagem OCI pronta enviada pelo desenvolvedor (D-029).
- Pesos de modelo privados (U1 do Juiz): no máximo como motivação.
