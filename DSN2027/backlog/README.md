# Backlog do Juiz (kanban)

**Atualizado:** 2026-11-11 · **Quadro vivo:** <https://claude.ai/artifact/2CB9dWqRXKFdv7APZCtcbF>
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
