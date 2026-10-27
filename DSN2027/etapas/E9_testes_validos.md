# E9 · Como testar A e B de forma válida e robusta

**Data:** 2026-10-26 · **Status:** proposta de desenho experimental; nada foi medido.
**Base:** [E5](https://github.com/lesorty/dnat-identity-validator/blob/archive/juiz-bounty-2026-10/DSN2027/etapas/E5_alt_bug_bounty.md) (A), [E6](E6_alt_modelos_abertos.md) (B), críticas da
[E7](E7_decisao_rumo.md) §8 e moldes do DSN na [E8](E8_alinhamento_dsn.md) §6 e §9.

**Por que importa:** no DSN, pesam avaliação com dados reais, comparação justa e artefato
reprodutível (GUIA §2). A E7 já apontou dois testes fracos que não podem se repetir:
- um piloto de A que passaria por acaso, porque media a qualidade do dataset e não a tese;
- uma população de B construída só por nós.

## 1. Regras comuns às duas alternativas

1. **Pré-registro:** limiares, métricas e critérios de sucesso e de corte ficam commitados antes
   de rodar o conjunto de teste.
2. **Calibração separada do teste:** o que ajusta o mecanismo nunca entra no teste. Sempre que
   possível, o teste usa uma família não vista (outro modelo, outro projeto).
3. **Controles negativos:** todo verificador ou detector precisa mostrar que falha quando deve.
4. **Verdade de referência independente:** o rótulo vem de um procedimento diferente do que está
   sendo avaliado, para evitar circularidade.
5. **Estatística:** várias seeds e repetições; intervalos de confiança por bootstrap; n sempre
   reportado; para modelos de linguagem, temperatura fixa e várias amostras.
6. **Linhas de base fortes:** a melhor alternativa existente.
7. **Ameaças à validade** como seção própria.
8. **Artefato** reprodutível, sem publicar material nocivo.

## 2. Alternativa A (contenção verificada / bug bounty), em alto nível

| # | O que testar | Como tornar válido | Métricas |
|---|---|---|---|
| A1 | Verificação automática na CVM | Só casos públicos e já corrigidos de benchmarks reconhecidos; amostra estratificada por classe; controle negativo obrigatório (a versão corrigida tem de ser rejeitada) | Fração verificável por classe; taxa de aceitação indevida |
| A2 | Propagação aos dependentes | Verdade de referência independente da presença no SBOM (o OCTOPOCS mostra que presença ≠ afetado); comparar com OSV/Dependabot | Precisão e revocação da marcação |
| A3 | Robustez a SBOM imperfeito | Erros conhecidos de SBOM (omissão, divergência entre geradores, como no DSN'24) | Queda de revocação por tipo de erro |
| A4 | Ocultação dos dependentes | Experimento de inferência sobre grafos de dependência públicos: quanto componente + recompensa + popularidade revelam | AUC da inferência contra linha de base aleatória |
| A5 | Incentivo | Modelo de jogo (molde Iniva, DSN'24) com análise de sensibilidade | Região de recompensa em que reivindicar domina |
| A6 | Custo | CVM × VM comum, várias repetições | Latência e custo por verificação, com IC |

**Ponto fraco de validade:** A4 e A5 são simulação e modelo, sem dado de campo de um mercado real.
Um revisor do DSN vai notar.

## 3. Alternativa B (custódia + portão)

| # | O que testar | Como tornar válido | Métricas |
|---|---|---|---|
| B1 | Cobertura e falso alarme por classe de falha (F1–F4, E8 §9.2) | População de derivados por classe, com várias seeds; **negativos difíceis**: fine-tuning benigno que preserva a recusa; a zona cinza (benigno que degrada) é reportada à parte | TPR a FPR de 1% e 5%; AUROC; **taxa de liberação silenciosa** |
| B2 | Generalização | Limiar calibrado numa família (ex.: Qwen2.5) e testado em outra não vista (ex.: Llama-3.2-1B); se houver orçamento, um ponto em 7–8B | Queda de cobertura entre famílias |
| B3 | Verdade de referência | Rótulo "perdeu a recusa" dado por uma **bateria independente** da usada no portão, com juiz mais forte e amostra conferida por humanos (molde do prompt polimórfico, DSN-S'25) | Concordância juiz × humanos |
| B4 | Representatividade (campo × injeção) | Obliterados públicos do Hugging Face como **teste cego**, nunca usados na calibração (molde TPU-FI, DSN'26) | Diferença de cobertura e de distribuição dos sinais |
| B5 | Sensibilidade à quantidade de falha | Varrer a intensidade de cada classe (molde ReMlX, DSN'25) | Curvas de cobertura × quantidade; limiar mínimo detectável |
| B6 | Atacante adaptativo | O atacante conhece o portão e tem orçamento definido de rodadas; inclui *Covert Malicious Finetuning* | Taxa de escape × orçamento; rodadas até escapar |
| B7 | Ablação | Cada sinal sozinho e combinados; **com e sem custódia** (o ataque de referência forjada de Hurtado só funciona sem custódia) | Contribuição de cada sinal e da custódia |
| B8 | Utilidade e custo | Desempenho dos derivados benignos aprovados na tarefa; tempo por veredito em CVM SEV-SNP × VM comum | Acurácia na tarefa; minutos e US$ por veredito; overhead |

**Ponto fraco de validade:** modelos pequenos e uma população em parte gerada por nós. B2 e B4
existem para responder exatamente isso.

## 4. Comparação

- **B produz um teste mais fechado:** verdade de referência independente, teste cego com dados de
  campo, família não vista e atacante adaptativo. Tudo cabe em CPU.
- **A produz dados reais na verificação e na propagação**, mas a parte nova (ocultação e
  incentivo) só se testa por simulação.
- **Primeiro passo de B (piloto de 2–3 dias):** um exemplo de cada classe F1–F3 no
  Qwen2.5-0.5B, dois ou três obliterados públicos, os três sinais e o tempo por veredito, com o
  critério de corte da E7 §7.
