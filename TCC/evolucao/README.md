# Evolução do trabalho — rumo, arquitetura e contribuição

Este diretório guarda a discussão sobre **para onde o trabalho vai depois do LADC 2026**:
mudanças de tese, de arquitetura e de contribuição. É separado do plano tático de
ressubmissão (`../PLANO_RESSUBMISSAO.md`), que trata do que entra no SAC em outubro.

## Organização

| Caminho | O que é | Quando atualizar |
|---|---|---|
| `ARTIGO.md` | Pretensões do artigo: tese, contribuições, escopo | Quando o rumo do artigo mudar |
| `JUIZ_IA.md` | Documento central do Juiz de IA: casos de uso, tags, problemas, abordagens, testes | A cada ideia ou decisão sobre o Juiz |
| `ETAPAS.md` | Plano de etapas desta discussão e o status de cada uma | Ao abrir ou fechar uma etapa |
| `DECISOES.md` | Registro de decisões (log datado, mais recente no topo) | Sempre que algo for decidido, mesmo que provisoriamente |
| `brainstorm/` | Ideias em aberto, uma por arquivo ou por tema | Quando surgir uma ideia nova ou uma ideia for refinada |
| `resultados/` | Um documento de resultados por etapa (`E<n>_<tema>.md`) | Ao final de cada etapa |
| `diagramas/` | Figuras SVG das arquiteturas decididas (`E<n>_<tema>.svg`) | Quando o desenho de uma etapa muda |

## Convenções

- **Ideia ≠ decisão.** Uma ideia vive em `brainstorm/` até ser aceita ou descartada; a
  decisão vai para `DECISOES.md` com data, motivo e link para a ideia ou o resultado.
- Ideias descartadas **não são apagadas**: ficam marcadas como `DESCARTADA` com o motivo,
  para não serem rediscutidas do zero.
- Afirmações sobre o código citam `arquivo:linha`; afirmações sobre a literatura citam a
  referência. O que não foi verificado é marcado como **(a verificar)**.
- Alvos de submissão usam as siglas do plano: **S** = SAC 2027, **D** = DSN 2027.

## Índice

- [ARTIGO.md](ARTIGO.md)
- [JUIZ_IA.md](JUIZ_IA.md)
- [ETAPAS.md](ETAPAS.md)
- [DECISOES.md](DECISOES.md)
- [brainstorm/01_direcoes_contribuicao.md](brainstorm/01_direcoes_contribuicao.md)
- [brainstorm/02_build_oci.md](brainstorm/02_build_oci.md)
- [brainstorm/03_agentes_verificacao.md](brainstorm/03_agentes_verificacao.md)
- [brainstorm/04_descentralizacao.md](brainstorm/04_descentralizacao.md)
- [brainstorm/05_imagem_pronta.md](brainstorm/05_imagem_pronta.md)
- [resultados/E1_auditoria_codigo.md](resultados/E1_auditoria_codigo.md)
- [resultados/E2_isolamento_confidencial.md](resultados/E2_isolamento_confidencial.md)
- [resultados/E2b_build_oci.md](resultados/E2b_build_oci.md)
- [resultados/E3_descentralizacao.md](resultados/E3_descentralizacao.md) (arquivado, D-031)
- [diagramas/E3_arquitetura.svg](diagramas/E3_arquitetura.svg) ·
  [diagramas/E3_execucao.svg](diagramas/E3_execucao.svg) ·
  [diagramas/E3_build.svg](diagramas/E3_build.svg)
