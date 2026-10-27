# E11 · Herança do Juiz de código

**Data:** 2026-10-27 · **Status:** registro. O Juiz de IA para validação de código (vazamento de
dados por aplicações) foi **descartado** em D1. O documento central (`JUIZ_IA.md`) e o levantamento
de literatura do Juiz saíram do repositório e estão na tag git
[`archive/juiz-bounty-2026-10`](https://github.com/lesorty/dnat-identity-validator/blob/archive/juiz-bounty-2026-10/DSN2027/JUIZ_IA.md).
Aqui fica só o que o rumo atual (proteção de modelos, D1–D2) ainda usa, com o texto de 2026-10-17/18.

**Citações antigas.** E2c e E6–E9 citam "JUIZ §x"; o trecho correspondente está em:

| Citação antiga | Aqui |
|---|---|
| JUIZ §1 (ideias herdadas: modelo aberto na CVM, veredito vinculado ao digest) | §1 |
| JUIZ §2 (U1, pesos de modelo) e P5 | §2 |
| JUIZ §3 (tag `pesos-modelo`) | §3 |
| JUIZ §5 (A4, A5, A7, A8) | §4 |
| JUIZ §6.1 (batalha) e §9.2 (verdade de referência CTF) | §5 |
| JUIZ §8 (L2, L4, ponto de desenho), §9.4 e §9.5 | §6 |
| Demais (tags gerais, P1–P12, pesquisa §7, benchmark V1–V6, MVP) | só na tag |

## 1. Ideias de desenho que seguem

- **O portão é uma aplicação do sistema**, na whitelist, que recebe a entrada a julgar e devolve
  um veredito (D2). Antes a entrada era código; agora é um derivado de modelo.
- **Juiz dentro da CVM com modelo de pesos abertos** (hash dos pesos na medição): julga sem que
  ninguém de fora veja a entrada. Com API externa, o provedor vê o que é julgado.
- **Veredito vinculado à fonte e ao digest** do que vai ser executado ou liberado, para que se
  julgue exatamente o que sai (E2c X8).

## 2. Caso U1: pesos de modelo (origem do rumo atual)

| Caso | O que barrar | O que é legítimo |
|---|---|---|
| **Pesos de modelo privados** (professor): arquitetura pública, pesos guardados no DNAT, liberados só para CVM atestada | Remoção de guardrails (*abliteration*, fine-tuning para tirar recusas); exportar os pesos | Inferência, fine-tuning, configuração |

- Pesos = ativo como um dataset; script do usuário = aplicação julgada. Mesmo modelo do DNAT.
- **P5 (o comportamento depende dos dados):** fine-tuning legítimo e abliteration podem ter o
  mesmo código; o dano está nos dados de treino ou no resultado. Ler o código não basta, por isso
  o portão **julga o derivado** (D2).
- **O modelo nunca sai do DNAT** (Steylor, 2026-10-17): executar, ajustar ou consultar o modelo
  só acontece dentro do DNAT; derivados também ficam lá.
- **Destilação:** quem consulta muitas vezes pode treinar um modelo que imita as respostas sem
  tocar nos pesos. Mitigações possíveis: limite de consultas, portão contra apps que geram dados
  de treino em massa, marca d'água **(a verificar eficácia)**. Portão de saída e marca d'água
  podem se tornar impeditivos para o caso (Steylor, 2026-10-17).
- Modelos grandes exigem GPU confidencial **(a verificar disponibilidade)**.

## 3. Tag `pesos-modelo` (sugestão do professor; não decidida)

O dono marca o ativo com tags que dizem para que ele pode ser usado. Para pesos: **permite** uso
dentro da CVM; o portão **procura** exportação de pesos e remoção de guardrails.

## 4. Abordagens herdadas

| # | Abordagem | Uso no rumo atual |
|---|---|---|
| A4 | **Avaliar o resultado**: bateria de recusa no derivado, comparada ao original | É o núcleo do portão (D2) |
| A5 | **Portão de saída** na execução, guiado pelas tags | Contra exportação de pesos pela saída legítima (C3) |
| A7 | Cache do veredito por `(hash da entrada, tags, versão do Juiz)` | Paga uma vez por derivado |
| A8 | Veredito em níveis: aprovado · aprovado com portão · reprovado · inconclusivo | D2 usa aprovado · reprovado · inconclusivo |

## 5. Avaliação: batalha e verdade de referência

- **Batalha atacante × defensor:** atacantes (baratos → caros) tentam burlar defensores (baratos
  → caros), em rodada estática e **adaptativa** (o atacante vê o veredito e tenta de novo).
  Métricas: detecção, falsos positivos, custo por veredito, rodadas até burlar. Cuidado com viés
  de família. Pergunta: um defensor barato detecta o ataque de um atacante caro?
- **Verdade de referência estilo CTF:** o ataque vale se a tarefa é cumprida **e** um teste
  independente, que o defensor nunca vê, confirma o dano. Tudo checado rodando, sem julgamento
  humano. No rumo atual, a bateria secreta de recusa faz esse papel (E6 C4, E9 §3).

## 6. Mecânica de execução (L2, L4) e contrato

- **Variação do segredo** (L2): rodar n vezes (n ≈ 20–50) com valores aleatórios no canário e
  estimar se a saída determina o segredo (vizinho mais próximo, à la F-BLEAU). Pega codificações
  arbitrárias. No rumo atual: **canários nos pesos** trocados entre execuções (E6 C3).
- **Portão na execução real** (L4): repete as checagens na saída real; **orçamento entre
  execuções** contra ataques de diferença (E2c S5). Necessário porque o dano pode aparecer só com
  o ativo real.
- **Ponto de desenho:** quem executa o alvo é a **plataforma**, e o Juiz recebe os resultados
  como entrada, para não rodar código não confiável dentro do próprio container (E2c §6, sinkhole).
- **Contrato:** entrada = fonte + digest + tags + relatório da plataforma (sempre há fonte: todo
  build é atestado, E2b.7); saída = `{veredito, nota, motivos, evidencias}`, cacheada (A7).
