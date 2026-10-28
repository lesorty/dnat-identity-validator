# Backlog do Juiz (kanban)

**Atualizado:** 2026-10-28 · **Quadro vivo:** <https://claude.ai/artifact/2CB9dWqRXKFdv7APZCtcbF>
(privado; só abre para quem tiver acesso) · **Plano de alto nível:**
[E13](../etapas/E13_plano_trabalho.md).

O trabalho até a submissão ao DSN 2027 está quebrado em **187 tasks de 1 a 4 horas**, divididas
em **16 épicos (J1–J16)** e **5 fases**:

| Fase | Épicos |
|---|---|
| 1 · Conceber o Juiz | J1 Especificação |
| 2 · Construir o Juiz | J2 Fundação · J3 Instrumento comportamental · J4 Sinais S2/S3 · J5 Formatos · J6 Veredito |
| 3 · O Juiz dentro do DNAT | J7 Contrato · J8 Executor e custódia |
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
| P1 | Alta: necessária, mas pode esperar ou encolher | 107 | ~231 |
| P2 | Média: melhora o artigo, primeira a cortar | 13 | ~35 |
| P3 | Opcional | 4 | ~6 |

Tamanho: **P** até 1 h, **M** cerca de 2 h, **G** cerca de 4 h. Total estimado: ~421 h. Os marcos são ESP (30/out),
G1 (01/nov), G0 (02/nov), G2 (09/nov), G3 (16/nov), G4 (23/nov), RES (25/nov) e SUB (02/dez).

## Arquivos

| Arquivo | O que é |
|---|---|
| `quadro.html` | O quadro kanban: colunas Backlog, Priorizado, Em andamento, Feito e Cortada; arrastar e soltar; filtros por fase, épico, marco e busca; gaveta para editar e criar tasks |
| `backlog.json` | Retrato dos dados (épicos, marcos e tasks) na data acima |
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
