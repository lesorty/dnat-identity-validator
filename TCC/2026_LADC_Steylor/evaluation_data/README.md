# TCC — Dados e Drafts da Avaliação

Pasta de apoio ao artigo LADC. Contém os dados reais coletados na avaliação e os
fragmentos `.tex` prontos para colar no Overleaf. Os fragmentos seguem o estilo
do `main.tex` (classe `acmart`, `booktabs`, `tabularx`) e estão em **inglês**,
como o restante do artigo.

## Arquivos

| Arquivo | O que é | Como usar no Overleaf |
|---------|---------|------------------------|
| `results_raw.md` | Todas as medições reais (T1–T5, latência), com contexto e interpretação. | Referência para preencher números; **não** vai no PDF. |
| `results_ab_campaign.md` | **Segunda coleta (2026-06-11):** corrida comparativa A vs B com o baseline mono-VM exercitado ao vivo (não mais derivado da config). | Referência; **não** vai no PDF. |
| `results_tables.tex` | 3 tabelas LaTeX com os dados reais (T1–T5, blast radius B×A, desempenho). | Cole as tabelas no corpo do artigo ou use `\input`. |
| `section_implementation.tex` | Seção **Implementation** nova. | Inserir após "DNAT Architecture", antes de "Security Analysis". |
| `section_evaluation.tex` | Seção **Evaluation** reescrita (metodologia + resultados). | Substituir a atual "Evaluation Methodology". |
| `section_results_ab.tex` | Subseção **A/B Comparison: Live Measurement** + tabelas `tab:ab-performance` (custo A×B) e `tab:blast-radius` (versão inglesa). | Inserir ao final da Evaluation, antes de "Threats to Validity". Se usar esta tabela `tab:blast-radius` (EN), **não** inclua a versão PT de `results_tables.tex` (colisão de label). |
| `section_conclusion.tex` | **Conclusion** revisada integrando as evidências. | Substituir a "Conclusion" atual. |

## Ordem sugerida das seções no `main.tex`

1. Introduction
2. Related Work and Background
3. Scope and Threat Model
4. DNAT Architecture
5. **Implementation**  ← `section_implementation.tex`
6. Security Analysis
7. Threats and Mitigations
8. **Evaluation**  ← `section_evaluation.tex` (usa as tabelas de `results_tables.tex`)
9. Discussion
10. **Conclusion**  ← `section_conclusion.tex`

## O que já tem dado real vs. o que falta preencher

**Coletado (Ambiente B, máquina de teste, 2026-06-11):**
T1 (exfiltração), T1b (filesystem), T3 (limpeza), T4 (blast radius — env/FS/rede),
T5 (controle de acesso), latência de execução (n=6, média 31,4 s), corretude funcional,
**T2 (supply chain — import-time contido + build-time iniciado)** e
**latência de build / tamanho de artefato** (sem deps 103 s/16 MiB; `requests`
131 s/19,6 MiB; cache quente 114 s).

**Coletado (Ambiente A vs B ao vivo, 2026-06-11 — `results_ab_campaign.md`):**
Plano de execução (T1/T1b/benigno) e plano de build (latência + tamanho) medidos
nos dois ambientes; T4 (segredos/stores/topologia) medido nos containers vivos
via `docker inspect`; T3 via `docker diff`; T5 negado nos dois. A coluna do
Ambiente A deixou de ser derivada da config e passou a ser medida.

**A preencher (opcional — fortalece o artigo):**
- Ferramentas estáticas/supply-chain (Bandit, Semgrep, pip-audit, Trivy, Grype).
- Reachability de rede em runtime de *dentro* do executor recoletada (a desta
  máquina veio do `docker inspect`/topologia; o probe interno está em
  `results_raw.md` T4, da primeira coleta).

O passo a passo para coletar o que falta está em
[`assets/tests/EVALUATION_PROTOCOL.md`](../../assets/tests/EVALUATION_PROTOCOL.md).

## Reprodutibilidade

- Dataset sintético (sem PII): `assets/data/dataset_synthetic.csv`
  (60 linhas, sha256 `5881e7514713ee87f6746e6f6329abd7de1d355c4eb4ffe04d9e143cd4944596`).
- Aplicações de avaliação: `assets/apps/{t1_network_exfil,t1b_fs_escape,t2_malicious_dep,benign_stats}.py`.
- Harness automatizado: `assets/tests/run_execution_plane_tests.sh`.
