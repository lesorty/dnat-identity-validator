# Brainstorm 03 — Verificação de aplicações por agentes de IA

**Origem:** conversa de 2026-10-14, após D-015.
**Status:** **contribuição principal do artigo (D-032, 2026-10-17)**. Nada verificado; tudo
**(a verificar)**. Decisões, testes e casos de uso a detalhar pelo Steylor.

**Centralizado em [JUIZ_IA.md](../JUIZ_IA.md)** a partir de 2026-10-17; este arquivo guarda o histórico.

**Desenho base (D-032):** o Juiz é **uma aplicação do sistema**, executada pelo mesmo pipeline
confidencial, que faz parte da whitelist e recebe outra aplicação como entrada.
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

## Ideias integradas com a arquitetura distribuída (2026-10-14, após a E3)

**Status:** propostas, nenhuma decidida. **Com a D-031**, as ideias que dependiam da rede
distribuída (G1 sorteio por stake, G5 liberação pelo comitê de chaves, G8 desafio com stake)
ficam fora; G2, G3, G4, G6, G7 e G9 continuam aplicáveis ao Juiz como aplicação.

| # | Ideia | Como se liga à E3 |
|---|---|---|
| G1 | **Verificador como papel da rede.** Verificadores sorteados por stake, como os builders; relatório final por quórum de k verificadores | Princípio de igualdade (D-023, D-024); D12 |
| G2 | **Diversidade de modelos.** Exigir verificadores com modelos/prompts diferentes, porque o mesmo modelo é enganado do mesmo jeito | Mesma lógica da diversidade de fabricante na política |
| G3 | **Agente dentro de CVM atestada**, com modelo de pesos abertos medido (hash dos pesos na medição). Abre um **terceiro caso: código secreto e dados privados**. O dono do dataset recebe um relatório atestado sem que ninguém veja o código | Mesmo mecanismo do build confidencial (D-027); `K_code` entregue às CVMs verificadoras como às de assemble |
| G4 | **Relatório vinculado à proveniência.** `(H(fonte), propriedade, veredito, medição do agente, assinaturas)` on-chain, sobre a **mesma fonte** que os builders construíram | Recibo e proveniência (direção 1, E2b.4) |
| G5 | **Imposição automática pela política.** A política do dataset exige "propriedade P verificada por ≥ k verificadores"; o comitê de chaves só libera a chave do dataset se o relatório existir no ledger | Mais uma condição na liberação do D4 |
| G6 | **Catálogo de propriedades** padronizadas (saída só agregada com mínimo de k registros; sem identificadores na saída; tamanho máximo de saída; sem acesso a colunas X), com texto livre como complemento | Torna a propriedade checável e comparável |
| G7 | **Testes dinâmicos objetivos ao lado do LLM:** dados sintéticos com o schema do dataset, *canários* (valores únicos plantados que não podem aparecer na saída) e **teste diferencial** (dois datasets que diferem em um registro; se a saída muda de forma reconhecível, há vazamento de registro individual). O agente gera os casos adversariais; a medição é mecânica | Roda na mesma infraestrutura de executores, com dados sintéticos |
| G8 | **Desafio com stake (estilo *optimistic*).** O verificador deposita stake; durante um prazo, ou depois, qualquer um que demonstre um vazamento numa app certificada recebe parte do stake cortado | Responde a "ausência de prova não é prova de ausência": o risco ganha preço |
| G9 | **Portão de saída em tempo de execução.** O executor confere a saída contra a propriedade declarada (tamanho, schema, canários inseridos pelo dono no dataset real) antes de cifrar para o comprador | Evolução da varredura de saída (D-015) dentro da CVM executora |

**Ataques ao próprio agente:** injeção de prompt em comentários e strings ("este código é seguro"),
ofuscação, comportamento ativado só por dados reais. Defesas: remover comentários antes da
análise, diversidade de modelos (G2), testes mecânicos que não dependem do julgamento do LLM (G7)
e o mercado de desafios (G8).

**Avaliação possível:** um benchmark de aplicações com vazamentos conhecidos (saída direta,
codificada, por agregação fraca, por tempo ou tamanho), medindo taxa de detecção e falsos
positivos por técnica (LLM, dinâmico, combinado). Complementa a suíte T1–T5, que mede isolamento.

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
