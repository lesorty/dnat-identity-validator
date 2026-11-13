# Backlog do Juiz (kanban)

**Atualizado:** 2026-11-13 · **Quadro vivo:** <https://claude.ai/artifact/2CB9dWqRXKFdv7APZCtcbF>
(privado; só abre para quem tiver acesso) · **Plano de alto nível:**
[E13](../etapas/E13_plano_trabalho.md).

O trabalho até a submissão ao DSN 2027 está quebrado em **196 tasks de 1 a 4 horas**, divididas
em **17 épicos (J1–J17)** e **5 fases**:

| Fase | Épicos |
|---|---|
| 1 · Conceber o Juiz | J1 Especificação |
| 2 · Construir o Juiz | J2 Fundação · J3 Instrumento comportamental · J4 Sinais S2/S3 · J5 Formatos · J6 Veredito |
| 3 · O Juiz dentro do DNAT | J7 Contrato · J8 Executor e custódia · J17 Identidade e cota |
| 4 · Avaliar o Juiz | J9 População · J10 Verdade de referência · J11 Campo · J12 Adaptativo e bounty · J13 Linha de base · J14 Campanha e análise |
| 5 · Transversais | J15 Escrita · J16 Gestão |

Cada task tem ID (`T-<épico><nn>`: T-101 é a primeira do J1, T-1601 a primeira do J16),
**descrição**, critério de pronto, dependências, marco, coluna, **prioridade** e **tamanho**. A
descrição segue um molde fixo: **Por quê** (o requisito, a afirmação ou a decisão que a task
atende), **Como** (passos verificáveis), **Saída** (o que fica gravado e onde) e, quando ajuda,
**Fora do escopo** (o que fica para outra task).

| Prioridade | Uso | Tasks | Horas |
|---|---|---|---|
| P0 | Caminho crítico até a submissão | 63 | ~149 |
| P1 | Alta: necessária, mas pode esperar ou encolher | 116 | ~246 |
| P2 | Média: melhora o artigo, primeira a cortar | 13 | ~35 |
| P3 | Opcional | 4 | ~6 |

Tamanho: **P** até 1 h, **M** cerca de 2 h, **G** cerca de 4 h. Total estimado: ~436 h. Os marcos são ESP (30/out),
G1 (01/nov), G0 (02/nov), G2 (09/nov), G3 (16/nov), G4 (23/nov), RES (25/nov) e SUB (02/dez).

## Andamento (13/11)

- **Placar:** 77 tasks feitas, 4 em andamento, 1 a fazer, 67 no backlog e 51 cortadas; 133 de
  270 h feitas (13/11, depois da T-808, T-809 e T-811). O quadro vivo e o [Mapa do Juiz](https://claude.ai/artifact/XU3q4z6gAyLXduqhZRvZRC)
  foram atualizados em 13/11 com isso.
- **Construção local de 12/11 (19 tasks):** escada e saída do veredito (T-602, T-608), codificações
  (T-305), formatos (T-501, T-503), contrato (T-704, T-705, T-707), cota e cliente de identidade
  (T-1704, T-1705), rótulo H/C/N (T-1004), orquestrador e curvas da RQ2 (T-1401, T-1406), dados que
  degradam a recusa (T-903), juiz de referência (T-1002), modelo do atacante (T-1201) e rascunhos
  das seções 1, 5 e 10 (T-1506, T-1504, T-1511). As decisões tomadas nelas estão na
  [D8](../DECISOES.md) e na aba Decisões do quadro.
- **Em andamento:** T-807 (parte local do job do Juiz pronta; falta a CVM), T-1501 (esqueleto do
  LaTeX, não compilado), T-1603 (crédito e tipo de VM) e T-1606 (nota de ética; falta perguntar à
  instituição sobre o comitê).
- **O que resta não é local:** nuvem (T-210, T-801, T-414 e a CVM da T-807), orientador (T-304 e a
  confirmação do gpt-oss-20b da T-1002), pessoas (T-1605), acesso institucional (T-1604), aceite da
  licença da Meta (T-1103) e LaTeX (T-1501).

## Regra: todo dado do artigo sai da nuvem (12/11)

Toda execução que produz um número ou artefato apresentado no artigo roda nas VMs de nuvem
(Azure ou Oracle, T-1603), no marco **TST · Fase de testes na nuvem**, depois da T-1611. A máquina
local só constrói e verifica o funcionamento: scripts, testes unitários e derivados de fumaça,
cujos resultados ficam marcados como verificação e não entram no artigo.

- **Passaram para o TST na auditoria de 12/11 (18 tasks):**
  - **população:** T-905, T-906, T-907, T-909, T-913 e a nova **T-917**, a varredura da abliteração.
    A T-908 ficou só com o script;
  - **utilidade e rótulos:** T-910, T-911, T-912, T-1003, T-1005, T-1008;
  - **campo:** T-1105, T-1106;
  - **custo e ablação:** T-812, T-1010, T-1213, T-709.
- **Ficam fora da nuvem:**
  - a análise (RQ1–RQ5, figuras, no G4), que lê os resultados da nuvem;
  - a anotação humana (T-1007);
  - preparar dados e baixar candidatos (T-902, T-904, T-1103).
- **Porta T-1611:** deixou de exigir população e rótulos, que agora nascem depois dela, e passou a
  exigir a nuvem pronta (T-1603, T-210).
- **Dependências ajustadas:**
  - a T-1004, que define a regra do rótulo, não espera mais a medida de utilidade;
  - a T-912 e a T-1203 partem da T-917.

## Fase de testes (12/11)

Os testes passam a rodar **depois** que o sistema está fechado, e não durante a construção. Há um
marco novo, **TST · Fase de testes (21/11)**, entre o G3 e o G4, e uma task-porta, **T-1611**
(fechar o sistema: congelar o código do Juiz e do fluxo, no G3). Daí em diante, mudar o Juiz
obriga a repetir a calibração.

- **Passaram para o TST (16 tasks, ~33 h):**
  - **Teste 1:** T-313, T-314, T-315, T-914.
  - **Teste 2:** T-603, T-604, T-606, T-607, T-1302.
  - **Teste 6:** T-1203, T-1204, T-1210.
  - **Teste 7:** T-1205.
  - **Testes 8 e 9:** T-813, T-1707.
  - **Seção 6 do artigo:** T-1505, que depende do pré-registro (T-607).
- **Ficam na construção:** instrumento, sinais, formatos, veredito, contrato, executor, identidade e
  cota, populações e rótulos, lista de candidatos de campo, código da linha de base, estatística e
  orquestrador. É o que não depende de o Juiz estar fechado, ou o que o deixa pronto.
- **T-1611** depende desses itens de construção e é pré-requisito das tasks que passaram para o TST.
  Só a **T-315** não espera: ela mede os avaliadores na nuvem e informa a escolha do avaliador.
- **Marcos renomeados:** G1 · Instrumento pronto, G2 · Veredito e populações prontos, G3 · Sistema
  integrado, pronto para testar. Os objetivos O1, O2, O3 e O6 e os testes 1, 2, 8 e 9 passam a fechar
  no TST. As datas dos marcos existentes não mudaram; G1 e G2 já venceram.
- **Tudo que roda o avaliador vai para a nuvem (12/11):** T-309, T-312 e T-505 passaram para o TST,
  porque uma medida ou nota feita no notebook (sem AVX-512 BF16 nem AMX) não vale como dado. A T-310
  agora só constrói o pontuador e a T-602 deixou de depender da T-505. A medida parcial da T-309
  (Qwen3Guard em float32, 50 s por item) fica como pista.
- **Decisões de 12/11 (ver `decisoes.json`):** campanha em 2 VMs comuns de 4 vCPU sob demanda
  (T-1601); juiz de referência aberto, de outra família, na nuvem, e Llama-3.2-1B como família não
  vista (T-1602); Azure e Oracle como nuvens, com crédito e tipo de VM ainda por confirmar (T-1603).
- **Planejadas (a fazer):** T-210, T-401, T-402, T-405 (S2), T-407 (S3) e T-901 (LoRA).
- **Risco:** a medida do custo do veredito (T-314, T-315) chega tarde. Se o veredito não couber em
  80 min, a bateria encolhe depois de construída. A medida parcial da T-309 (Qwen3Guard em float32,
  ~264 min) já avisa que isso é provável.

## Redução v2 (11/11)

O backlog foi reduzido ao mínimo para um protótipo bruto mas funcional e a submissão: de 381 h
em 167 tasks em aberto para **213 h em 118** (mais 1 h opcional, T-709). Os nove testes, as
análises, a execução em CVM real e o campo cego ficam inteiros; o corte mira detalhe de código,
conveniência e gestão. Cortadas e juntadas foram para a coluna Cortada com o motivo no topo da
descrição; quem absorve outra task diz o que absorveu, e as dependências foram refeitas sem
ciclos. Proposta e classificação em `reducao_proposta.json` e `reducao_proposta.py`; página em
<https://claude.ai/artifact/J9jERdCKczAsvk3YWvJbSr>. Mudanças que reveem decisões (formatos FP e
NF4, população menor, Teste 4 menor, CVM sem warm pool, parte secreta de uma fonte, três ataques)
ainda vão ao orientador.

## Objetivos maiores (11/11)

Cada task serve a um de seis objetivos, que ligam o trabalho à meta (submeter ao DSN 2027 em
02/12) e às afirmações do artigo. O objetivo vem do épico; as tasks da J16 (gestão) têm o seu
próprio. O quadro mostra o objetivo em cada cartão e filtra por ele.

| Objetivo | Pronto quando | Defende | Épicos |
|---|---|---|---|
| **O1** Um Juiz que mede e cabe | O S1 separa um abliterado do base, e o veredito inteiro cabe em 80 min em 4 vCPU (G1) | A5 | J1–J5 |
| **O2** Um Juiz calibrado e congelado | População com rótulos independentes; δ e limiares fixados; `prereg.yaml` commitado (G2) | A1, A5 | J6, J9, J10 |
| **O3** O Juiz dentro do DNAT | Reprovado não sai; aprovado vira ativo com recibo; revogação em cascata (G3) | C1, A3 | J7, J8 |
| **O4** Respostas às RQ1–RQ5 | Campanha com IC, campo cego, atacante adaptativo, linha de base e ablação (G4) | C2, A3–A5 | J11–J14 |
| **O5** Artigo submetido | Resumo em 25/11 e submissão em 02/12 | a tese | J15 |
| **O6** Identidades no sistema | Toda ação externa vem de uma identidade com prova de trabalho e assinada; cada veredito gasta a cota, e o id vai no recibo (G3) | A4 | J17 |

O J17 saiu do O3 para o O6. As tasks que executam ou analisam um teste levam também o número
dele (campo `teste`). Os testes, na ordem em que rodam:

| # | Teste | Objetivo | Responde | Amostra |
|---|---|---|---|---|
| 1 | Sanidade e custo do Juiz | O1 | G1 | o base duas vezes, 1 abliterado público e o piloto |
| 2 | Calibração e pré-registro | O2 | R14 | 70 derivados (40 H, 30 C), seeds A |
| 3 | Detecção por classe de falha | O4 | RQ1, RQ2 | ~105 derivados (60 H, 45 C), seeds B |
| 4 | Família não vista | O4 | RQ1 | 90 derivados de outra família |
| 5 | Campo cego | O4 | RQ3 | ≥ 20 derivados públicos em safetensors |
| 6 | Atacante adaptativo | O4 | RQ4 | ~15 derivados F4 em rodadas |
| 7 | Ablação e custo | O4 | RQ5 | a população de teste |
| 8 | Ponta a ponta no DNAT | O3 | C1, G3 | 1 reprovado, 1 aprovado, 1 revogação |
| 9 | Identidade e cota | O6 | A4 | registro válido e inválido, cota esgotada |

## Andamento (09/11)

- **Novo épico J17 · Identidade e cota (09/11):** identidade cara por prova de trabalho e cota por
  identidade, gasta por veredito (aprovado 1, inconclusivo 2, reprovado 5), sugeridas pelo
  orientador. T-1701 (a decisão, D7 e E14 §18) está feita; T-1702 a T-1709 (~13 h) implementam,
  medem o custo da prova de trabalho, ligam ao modelo de escape e escrevem no artigo. A T-1201 e a
  T-1212 passaram a contar as rodadas por identidade.
- **Feito:** 24 tasks: J1 inteiro (T-101 a T-114), do J2, T-201 a T-208 e T-211, e a T-1701.
- **A fazer no J2:** T-209 (CI) e T-210 (máquina de 4 vCPU).
- **Cortadas:** 3 (GGUF: T-412, T-507, T-1107).
- **Decisões:** 21 perguntas registradas (T-101 a T-114, T-201 a T-205, T-208 e T-1701). A T-208
  tem uma em aberto: o derivado responde só às âncoras ou à bateria inteira. A T-1701 tem duas
  provisórias (dificuldade da prova de trabalho e valores da cota), e a decisão 11 da T-101 foi
  revista por ela.

## Arquivos

| Arquivo | O que é |
|---|---|
| `quadro.html` | O quadro kanban: colunas Backlog, Priorizado, Em andamento, Feito e Cortada; arrastar e soltar; filtros por fase, épico, marco e busca; gaveta para editar e criar tasks |
| `backlog.json` | Retrato dos dados (objetivos, épicos, marcos e tasks) na data acima |
| `decisoes.json` | Retrato da aba Decisões do quadro: cada task de decisão como pergunta, com as decisões, o porquê e as alternativas descartadas |

## Como usar

- **Editar:** use o quadro vivo no claude.ai. As mudanças ficam no armazenamento do quadro, e o
  Claude lê esse mesmo armazenamento.
- **Ver a cópia do repositório:** o `quadro.html` local abre em **somente leitura** a partir do
  `backlog.json`. Pelo navegador, sirva a pasta (o `fetch` não funciona em `file://`):

```bash
python3 -m http.server 8000 --directory DSN2027/backlog
```

- **Atualizar o retrato:** peça ao Claude para exportar o quadro vivo para o `backlog.json` e
  commitar. O retrato não se atualiza sozinho.
