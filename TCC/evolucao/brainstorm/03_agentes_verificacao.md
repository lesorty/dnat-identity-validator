# Brainstorm 03 — Verificação de aplicações por agentes de IA

**Origem:** conversa de 2026-10-14, após D-015.
**Status:** só motivação e perguntas. Nada verificado; tudo **(a verificar)**. Frente futura (D-016).
**Relacionados:** D-014, D-015 · [E2b, varredura de saída](../resultados/E2b_build_oci.md)

## Motivação

| Caso | Código | Dados | Situação no DNAT |
|---|---|---|---|
| 1 | secreto | públicos ou conhecidos | Funciona bem: nenhum lado corre risco |
| 2 | **conhecido** | **privados** | **Lacuna**: o código é verificável, mas o esforço de verificar é proibitivo, e isso gera insegurança no dono dos dados |

## Ideia

O usuário declara **propriedades de segurança** que a aplicação deve cumprir (ex.: não vazar
dados). Agentes de IA verificam a aplicação contra elas e produzem um relatório, que fica
disponível ao dono dos dados antes de autorizar o uso.

Cobre vazamento **direto** e **indireto**: por fuzzing, por máscara (dado transformado mas
recuperável), pelo resultado, por canais laterais.

## Relação com o que já decidimos

- Evolui a **varredura de saída** (D-015), que hoje é básica.
- Toca no **X8** (D-014), que está fora de escopo no artigo: esta frente seria o caminho para
  tratá-lo no futuro, junto com a política de saída (direção 4).

## Perguntas em aberto

- Como se **especifica** uma propriedade ("não vaza dados") de forma que um agente verifique?
- O que o agente **garante**? Ausência de prova não é prova de ausência: qual é o nível de
  confiança aceitável e como ele é declarado?
- **Quem confia no agente?** O agente também é um componente; o relatório é atestado?
- Os agentes rodam **onde**: no builder atestado, em CVM própria, fora do sistema?
- Que técnicas entram: análise estática, execução com dados sintéticos, fuzzing, análise de
  fluxo de informação, testes diferenciais?
- Como lidar com **ataques ao próprio agente** (código que tenta enganar o verificador)?
- Qual o custo, e quem paga?
- Como o relatório entra na **cadeia verificável** (proveniência, ledger)?
