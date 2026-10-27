# Pesquisa: levantamentos de literatura

Material para **agregar dados e decidir depois**. Nada aqui é decisão: as decisões do artigo
seguem em [DSN2027/DECISOES.md](../DSN2027/DECISOES.md).

**Rumo atual (D1, 2026-10-27): proteção de modelos abertos.** Os levantamentos só do Juiz de
código (vazamento de dados por aplicações), descartado, saíram daqui e estão na tag git
`archive/juiz-bounty-2026-10`: [01 · Juiz de segurança de aplicações](https://github.com/lesorty/dnat-identity-validator/blob/archive/juiz-bounty-2026-10/pesquisa/01_juiz_seguranca_apps.md)
e [04 · Avaliação de aplicações contra vazamento](https://github.com/lesorty/dnat-identity-validator/blob/archive/juiz-bounty-2026-10/pesquisa/04_avaliacao_apps_vazamento.md).
O que o rumo atual herda do Juiz está em [E11](../DSN2027/etapas/E11_heranca_juiz.md).

| # | Documento | Área | Data |
|---|---|---|---|
| 02 | [Transparência de execução de LLMs](02_transparencia_execucao_llm.md) | `sigstore/model-transparency` e OMS, GPU confidencial (Azure), execução e auditoria verificáveis, fine-tuning sem obliteração | 2026-10-20 |
| 03 | [Confiabilidade de LLMs e de aplicações: arcabouço de leitura](03_confiabilidade_llm.md) | Lista curta (um paper por linha): fundamentos e dependabilidade, LLM como juiz, segurança de apps, verificabilidade barata, engenharia e testes, normas e práticas; **caminho barato sem GPU** | 2026-10-20 |
| 05 | [Proteção de modelos abertos](05_protecao_modelos.md) | Definição do problema para o rumo atual: levantamento no DSN e externo | 2026-10-27 |
| 06 | [Leitura: obliteração e fine-tuning nocivo](06_leitura_obliteracao.md) | 28 notas: perda de recusa na derivação, defesas nos pesos, detecção de obliterados, avaliação de recusa | 2026-10-27 |
| 07 | [Leitura: bounty e red teaming verificável](07_leitura_bounty.md) | Competições e programas de prêmio para modelos, como o sucesso é verificado, incentivos (Hydra) | 2026-10-27 |
| 08 | [Leitura: cadeia de suprimentos de modelos e custódia](08_leitura_cadeia_custodia.md) | Modelos sem recusa nos hubs, proveniência e AIBOM, auditoria atestada, execução confidencial | 2026-10-27 |

**PDFs:** os artigos abertos citados em 05–08 estão em [artigos/](artigos/) (`AAAA_sobrenome_palavra.pdf`);
os do DSN ficam em [DSN2027/referencias/dsn/](../DSN2027/referencias/dsn/). Baixar à mão (bloqueio
automático): Sealed-Glass Proofs (ePrint 2016/635) e Sokhansanj, *Uncensored AI in the Wild*
(Future Internet 17:477). Sem versão aberta: Zhao et al. (CCS'15).

**Leitura recomendada para começar (2026-10-27):**
1. Hurtado 2026, *Has This Checkpoint Been Abliterated?* (`artigos/2026_hurtado_abliterated.pdf`).
2. Sharma et al. 2025, *Constitutional Classifiers* (`artigos/2025_sharma_constitutional.pdf`).
3. Lin et al. 2025, *Consiglieres in the Shadow* (`artigos/2025_lin_consiglieres.pdf`).

**Como foi feito.** Leitura do repositório e duas rodadas de levantamento em 2026-10-20:
- **primeira rodada:** sete levantamentos em paralelo;
- **segunda rodada:** quatro levantamentos para fechar as lacunas que sobraram quando a cota de
  buscas acabou na primeira.

As referências foram abertas na fonte, e as que mais pesam foram conferidas de novo (✔). Cada
documento lista o que ainda está em aberto (§8 e §10). Convenções do repositório: tier da
publicação, "(a verificar)".

## O que mais pesa, em uma página

### Transparência de execução de LLMs (02)

- **`model-transparency` assina, mas não prova processo.** Garante integridade e identidade.
  Proveniência, evidência de TEE e veredito do Juiz são **atestações separadas** sobre o root
  digest (posição dos mantenedores, #586). A última *release* é a v1.1.1 (out/2025), e há
  correções de segurança só no `main`. **Nenhuma ferramenta vincula a chave de assinatura a uma
  atestação SEV-SNP/TDX/GPU**; a integração com TEE (#548, via Atlas) está aberta sem código.
- **Azure hoje:** só a `NCC40ads_H100_v5`, com **uma** H100 de 94 GB em SEV-SNP (~US$ 7/h sob
  demanda, ~US$ 1,30/h spot). Não há multi-GPU confidencial. Não existe medição publicada de
  SEV-SNP + H100 na Azure, e medir isso pode virar resultado nosso.
- **Fine-tuning sem obliteração:** o alinhamento é raso e barato de desfazer (10 exemplos,
  < US$ 0,20), a moderação de dados ponto a ponto tem limite teórico, e o melhor auditor
  publicado detecta 56% com 1% de FPR. A literatura indica **receitas atestadas + defesas na
  receita + Juiz em 4 camadas (dados, receita, pesos, comportamento) + inferência confinada e
  monitorada**.
- **A lacuna:** ninguém combina fine-tuning confidencial, avaliação de segurança atestada e
  liberação condicionada com o modelo nunca saindo. Os vizinhos mais próximos são Atlas,
  Attestable Audits, Laminator e AFTUNE.
- **Segunda rodada:**
  - **O Hugging Face ainda não assina nem verifica com OMS.** A assinatura no Kaggle é opcional,
    e a NGC assina tudo.
  - **Não há predicado in-toto para treino.** É preciso compor SLSA, SCAI, AI-SBOM e OMS; o
    `eval-result` (PR aberto) serve para o veredito.
  - **Política de atestação no Genoa:** TCB mínimo SNP ≥ 0x1B (RMPocalypse corrigido). Heracles
    continua como risco residual.
  - **Não herdar a política de atestação de GPU do onboarding da Azure**, que ignora o nonce do
    OCSP.
  - **Provar fine-tuning em ZK ainda é caro demais.** O VeriLoRA (NDSS'26) leva ~2–4 min por
    amostra num modelo 13B; o caminho é TEE com auditoria amostral.
  - **Consenso de 2026:** salvaguardas embutidas nos pesos não duram, e a garantia vem da
    custódia dos pesos.
  - **Anti-destilação:** a Anthropic relata 90–99% menos dados colhidos com controle do
    raciocínio e um classificador. Marca d'água só serve como evidência forense.
- **Limites que não somem:**
  - atestação prova execução, não segurança;
  - backdoors com gatilho e *sandbagging* passam pela avaliação;
  - ataque físico quebra a atestação (TEE.fail, S&P'26), e a atestação da GPU NVIDIA pode ser
    "emprestada" se não for vinculada à CVM.
