# Pesquisa: levantamentos de literatura

Material para **agregar dados e decidir depois**. Nada aqui é decisão: as decisões do artigo
seguem em [DSN2027/DECISOES.md](../DSN2027/DECISOES.md).

| # | Documento | Área | Data |
|---|---|---|---|
| 01 | [Juiz de segurança de aplicações](01_juiz_seguranca_apps.md) | AI control, LLM-como-juiz, detecção mecânica de vazamento, portão de saída, benchmarks, esteganografia | 2026-10-20 |
| 02 | [Transparência de execução de LLMs](02_transparencia_execucao_llm.md) | `sigstore/model-transparency` e OMS, GPU confidencial (Azure), execução e auditoria verificáveis, fine-tuning sem obliteração | 2026-10-20 |
| 03 | [Confiabilidade de LLMs e de aplicações: arcabouço de leitura](03_confiabilidade_llm.md) | Lista curta (um paper por linha): fundamentos e dependabilidade, LLM como juiz, segurança de apps, verificabilidade barata, engenharia e testes, normas e práticas; **caminho barato sem GPU** | 2026-10-20 |

**Como foi feito.** Leitura do repositório e duas rodadas de levantamento em 2026-10-20:
- **primeira rodada:** sete levantamentos em paralelo;
- **segunda rodada:** quatro levantamentos para fechar as lacunas que sobraram quando a cota de
  buscas acabou na primeira.

As referências foram abertas na fonte, e as que mais pesam foram conferidas de novo (✔). Cada
documento lista o que ainda está em aberto (§8 e §10). Convenções do repositório: tier da
publicação, "(a verificar)".

## O que mais pesa, em uma página

### Juiz (01)

- **A lacuna C3 continua de pé.** Não achamos benchmark de vazamento escondido na saída legítima
  de programas de dados com decodificador. Os vizinhos (BigCodeBench-Sabotage, SHADE-Arena,
  SLEIGHT-Bench, ResearchArena) testam exfiltração por rede, arquivo ou ação.
- **A nossa pergunta central também é lacuna.** Ninguém mediu um monitor LLM com **evidência
  dinâmica de ferramenta confiável** contra atacante adaptativo. O mais próximo (Liao et al.,
  2026) mostra que a execução ajuda o monitor fraco, mas não testa a combinação com LLM.
- **Atacante adaptativo derruba monitor LLM**: com ataque adaptativo a segurança cai de 0,87
  para 0,41, a reamostragem para 17% e o ALIBI passa de 90%. Como o Juiz é público, o atacante
  o tem por construção. A batalha precisa de atacante com **simulador do Juiz** e de segredos do
  protocolo gerados na execução.
- **Comentários:** Thornton (sem efeito, com templates fixos) é contradito por ALIBI (> 90% de
  sucesso com ataque adaptativo). Sugestão: L3 com e sem texto do atacante, e a divergência vira
  evidência.
- **k mínimo não protege contra ataque de diferença.** Concordam a literatura e os fornecedores
  (AWS, Google, Snowflake), e a atualização do dataset já é um par diferencial. Declarar a
  limitação ou oferecer `dp:ε`.
- **Variação do segredo com n ≈ 20–50:** usar um conjunto finito e repetido de valores, variar
  o fundo do dataset e usar teste sequencial. Senão, falso negativo ou falso positivo.
- **Correção:** o título do Thornton no `refs.bib` está desatualizado (01 §7).
- **Segunda rodada:**
  - **Desarmar, não detectar.** Não existe esteganálise que funcione em saídas pequenas, então a
    L4 deve **canonicalizar** os números (arredondar e reserializar). Ainda sobra ~1 bit por
    número, que entra no orçamento.
  - **Negar também vaza** (Kenthapadi, Mishra, Nissim): toda recusa do portão tem de ser
    simulável ou contada como saída.
  - **Para a L3:** um crítico independente basta; um debate não acrescenta nada. A execução só
    ajuda o juiz se chegar como evidência estruturada.
  - **IFC para agentes** (CaMeL, FIDES) cobre só fluxo explícito, e o nosso caso é o implícito.
  - **Taint dinâmico em Python** quebra no numpy, o que reforça o teste D/D′.
  - **Números conferidos** no corpo dos artigos: Liao (testes direcionados com AUROC 0,765) e
    Terekhov (com injeção, o GPT-4.1 deu nota 0 a 375 backdoors).

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
