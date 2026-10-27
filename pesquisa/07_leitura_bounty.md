# Leitura: recompensas, bug bounty e red teaming verificável para modelos (base do bounty P4)

**Data:** 2026-10-27 · **Para:** extensão **P4** da [E10](../DSN2027/etapas/E10_problema.md) §4–§5 (bounty
como avaliação adaptativa contínua: prêmio para quem mostrar um **derivado** ou uma **entrada** que
passe pelo portão e falhe numa **bateria secreta**, com verificação automática).
**Ponto de partida:** [05](05_protecao_modelos.md) §5 e §7 (P4); `E5_alt_bug_bounty.md` §8 (economia de
bounty; o arquivo saiu da árvore de trabalho em 2026-10-27 e segue no histórico do git, commit `27b1451`).
**Escopo:** só base científica. Nada foi implementado.

**Convenções.**
- ✔ = venue conferido nesta rodada na fonte primária (cabeçalho do PDF, anais, OpenReview, OpenAlex).
  **(a verificar)** = não conferido.
- **Leitura:** *integral* = corpo do artigo lido; *seções* = as seções listadas; *abstract* = só o
  resumo (sem versão aberta acessível).
- PDFs em [`artigos/`](artigos/), nome `AAAA_sobrenome_palavra.pdf`, conferidos com `pdfinfo`.
- Ataques aparecem só no nível do que cada artigo mostra. Nenhuma técnica operacional é reproduzida.

---

## 0. Resumo em seis linhas

1. Em todas as competições sérias, o sucesso é decidido por um **oráculo fixo sobre um conjunto
   privado**: modelo de recompensa (Rando), segredo exato (CTF, Tensor Trust, HackAPrompt), verificador
   executável (BountyBench, AgentDojo) ou juiz LLM com rubrica (Constitutional Classifiers, Gray Swan).
2. **O avaliador vira o elo mais fraco.** Quando o oráculo é um juiz, os caçadores atacam o juiz, e não a
   defesa (paráfrase benigna e saídas longas contra a rubrica; *specification gaming* no Gray Swan;
   *reward hacking* em Nasr et al.). Bugs de infraestrutura também viram "jailbreaks".
3. O sucesso mais defensável é **relativo a uma referência sem proteção**: "≥ 50% do detalhe de um modelo
   sem salvaguarda" (Constitutional Classifiers) e "explora a versão vulnerável e falha na corrigida"
   (BountyBench). É exatamente o nosso δ em relação ao pai.
4. **Hydra** dá o princípio de incentivo: pagar automaticamente pela **divergência** entre duas
   verificações independentes (aqui: o portão e a bateria secreta) antes que o defeito vire exploração
   completa, com preço derivado da razão entre as duas taxas de falha.
5. A economia de bounty empírica diz: prêmio escalonado com teto alto atrai mais que prêmio fixo; cada
   caçador acha poucos defeitos num mesmo alvo (vale a diversidade); o interesse decai após o
   lançamento; relatórios inválidos custam caro. Verificação automática elimina o custo humano de
   triagem, mas não o custo de computação por submissão.
6. Nenhum trabalho lido paga por **quebrar um portão de liberação de derivados**, nem tem verificação
   **atestada** com pagamento automático sobre modelos. A lacuna de [05](05_protecao_modelos.md) §5
   continua de pé (ausência de achado não prova novidade).

---

## 1. Tabela-resumo

| Trabalho | Venue | Como o sucesso é verificado | Prêmio | Leitura | PDF |
|---|---|---|---|---|---|
| Rando et al., *Universal Jailbreak Backdoors* | Relatório arXiv da competição do IEEE SaTML 2024 ✔ | Oráculo automático: modelo de recompensa fixo sobre 2.300 perguntas privadas | US$ 7 mil + bolsas de computação e viagem | integral | `2024_rando_backdoors.pdf` |
| Debenedetti et al., *SaTML 2024 LLM CTF* | NeurIPS 2024 D&B ✔ | Segredo exato, conferido num endpoint separado, com 10 palpites | Prêmios em dinheiro (valores não dados no texto) + viagem | integral (sem apêndices de defesas) | `2024_debenedetti_ctf.pdf` |
| Toyer et al., *Tensor Trust* | ICLR 2024 ✔ | Regex sobre a saída ("access granted") | Saldo no jogo (sem dinheiro) | §1–3, ap. A | `2024_toyer_tensortrust.pdf` (v1 do arXiv) |
| Schulhoff et al., *HackAPrompt* | EMNLP 2023 ✔ | Frase-alvo exata, reexecutada pelo organizador em modo determinístico | US$ 37,5 mil + créditos | §1–3, §6, limitações | `2023_schulhoff_hackaprompt.pdf` |
| Sharma et al., *Constitutional Classifiers* | Preprint 2025 (arXiv 2501.18837) | Juiz LLM com rubrica; sucesso ≥ 50% do detalhe de um modelo sem salvaguarda | Até US$ 15 mil por relatório; US$ 95 mil pagos | §1–4, ap. de lições | `2025_sharma_constitutional.pdf` |
| Cunningham et al., *Constitutional Classifiers++* | ICLR 2026 (a verificar no PDF final) | Mesma rubrica; "vulnerabilidade de alto risco" = > 5 de 8 perguntas | US$ 25–35 mil por campanha | §1–4, ap. B, lições | `2026_cunningham_constitutional.pdf` |
| Zou et al., *Security Challenges in AI Agent Deployment* (Gray Swan + UK AISI) | Preprint 2025 | Juiz programático e/ou maioria de 3 juízes LLM; apelação a modelo mais forte e depois a humano (UK AISI) | US$ 171,8 mil | §1–3, ap. de julgamento | `2025_zou_agentredteaming.pdf` |
| Nasr et al., *The Attacker Moves Second* | Preprint 2025 (a verificar) | Ambiente AgentDojo checa automaticamente; juízes humanos em apelações | US$ 20 mil | lições, ap. C e E | `2025_nasr_attacker.pdf` (já existia) |
| Souly et al., *StrongREJECT* | NeurIPS 2024 ✔ (cabeçalho do PDF) | Avaliador automático de quão útil é a resposta proibida | — | abstract + §1 | `2024_souly_strongreject.pdf` (já existia) |
| Chao et al., *JailbreakBench* | NeurIPS 2024 D&B ✔ | Juiz LLM escolhido por concordância com 3 anotadores | — | abstract, §3.5 | `2024_chao_jailbreakbench.pdf` |
| Breidenbach et al., *Enter the Hydra* | USENIX Security 2018 ✔ | Divergência entre "cabeças" detectada em tempo de execução por contrato | Automático, pago pelo contrato | §1–4, retenção, limitações | `2018_breidenbach_hydra.pdf` |
| Tramèr et al., *Sealed-Glass Proofs* | IEEE EuroS&P 2017 ✔ (OpenAlex) | Enclave atesta a execução do exploit; contrato faz a troca justa | Automático por contrato | **abstract** | **não baixado** (ver §5) |
| Zhang et al., *BountyBench* | NeurIPS 2025 D&B ✔ | Exploit executável: sucede na versão vulnerável e falha na corrigida | Valores reais de bounties (US$ 10–30.485) como métrica | §1–3, §6, ap. F e H | `2025_zhang_bountybench.pdf` |
| Finifter et al., *Vulnerability Rewards Programs* | USENIX Security 2013 ✔ | Triagem humana do fornecedor | Chrome escalonado × Firefox fixo | abstract, §4 (partes), §5 | `2013_finifter_vrp.pdf` |
| Maillart et al., *Given Enough Eyeballs…* | Journal of Cybersecurity 2017 ✔ | Triagem humana (HackerOne) | — | abstract, discussão, conclusão | `2017_maillart_eyeballs.pdf` |
| Zhao et al., *Web Vulnerability Discovery Ecosystems* | CCS 2015 ✔ (OpenAlex) | Triagem humana (Wooyun, HackerOne) | — | **abstract** | **sem versão aberta** |
| Laszka et al., *Banishing Misaligned Incentives…* | ESORICS 2016 (a verificar) | Validação humana; modelo econômico | — | §1, conclusão | `2016_laszka_validation.pdf` |
| Brundage et al., *Toward Trustworthy AI Development* | Relatório arXiv 2020 | — (propõe bounties de viés e segurança) | — | §2.3 | `2020_brundage_verifiableclaims.pdf` |
| Feffer et al., *Red-Teaming for GenAI: Silver Bullet or Security Theater?* | AIES 2024 (a verificar) | — (levantamento crítico) | — | abstract, achados | `2024_feffer_redteaming.pdf` |
| Programas: demo pública da Anthropic (fev/2025), Bio Bug Bounty da OpenAI (2025), HackAPrompt 2.0 (2025) | Páginas e imprensa | Rubrica + revisão; convite e NDA (OpenAI) | Ver §2.9 | páginas | — |

---

## 2. Competições e programas de red teaming em LLMs (núcleo)

### 2.1 Rando et al. — *Competition Report: Finding Universal Jailbreak Backdoors in Aligned LLMs* (2024)

- **Referência:** J. Rando, F. Croce, K. Mitka, S. Shabalin, M. Andriushchenko, N. Flammarion,
  F. Tramèr. arXiv [2404.14461](https://arxiv.org/abs/2404.14461). Relatório da competição do IEEE
  SaTML 2024 ✔. Modelos e código: `ethz-spylab/rlhf_trojan_competition`.
- **Lição em uma frase:** um oráculo automático e fixo (modelo de recompensa limpo) sobre um conjunto de
  teste privado basta para ranquear submissões sobre **modelos de pesos abertos comprometidos**, e a
  falha plantada pelo organizador funciona como linha de base difícil de superar.
- **Desenho:** cinco LLaMA-2 7B alinhados por RLHF e envenenados, cada um com um gatilho universal
  diferente (taxa de envenenamento de 25%). Os participantes recebem os pesos, um modelo de recompensa
  treinado sem envenenamento, 42 mil exemplos de treino e 500 de validação. Tarefa: achar, para cada
  modelo, um sufixo de 5–15 tokens que torne as respostas o mais nocivas possível.
- **Verificação:** o organizador anexa o sufixo a cada uma das **2.300 perguntas privadas**, gera as
  respostas e soma a recompensa média por modelo (nota menor = mais nocivo). Regras contra trapaça:
  sem dados extras, o sufixo não pode trazer instruções próprias, as respostas devem ser diversas.
- **Prêmio:** US$ 4 mil / 2 mil / 1 mil, bolsas de viagem e **bolsas de computação** (uma A100 por
  ~100 h para cada equipe que pediu).
- **Certo:** 12 submissões válidas; métodos muito diferentes chegaram perto dos gatilhos; os modelos e
  dados viraram a primeira suíte pública de modelos com *backdoor* universal.
- **Errado / limites:** só uma submissão superou o gatilho injetado (num único modelo); a submissão
  preliminar no conjunto privado quase não foi usada (3 envios, 2 inválidos); as duas melhores equipes
  dependeram de ter **vários modelos irmãos** com a mesma origem para comparar, o que o próprio relatório
  chama de irrealista. Os organizadores registram "pouco retorno" para o esforço de organizar.
- **Para o nosso bounty:**
  - É o molde direto do oráculo: **juiz fixo e publicado + conjunto privado + nota média**, aplicado a
    pesos abertos. A bateria secreta deve seguir esse formato.
  - **Falhas plantadas como linha de base:** derivados comprometidos de propósito, com taxa conhecida,
    calibram o poder do portão e dos caçadores. Liga P4 a P5 (representatividade).
  - **Contaminação / vazamento:** feedback no conjunto privado deve ser raro e agregado. Mesmo assim,
    quase ninguém usou a prévia; o custo de vazar a bateria por consultas é baixo se o orçamento for pequeno.
  - **Custo:** sem bolsa de computação, duas das três equipes premiadas não teriam participado. Num
    bounty sobre derivados, cada submissão é um fine-tuning: prever crédito de GPU na CVM.
  - **Conluio:** o atacante que tem acesso a vários derivados do mesmo pai ganha poder (comparação entre
    irmãos). A plataforma de custódia controla esse acesso, o que é argumento a favor da custódia.

### 2.2 Debenedetti et al. — *Dataset and Lessons Learned from the 2024 SaTML LLM CTF* (2024)

- **Referência:** E. Debenedetti, J. Rando, D. Paleka et al. NeurIPS 2024 Datasets & Benchmarks ✔
  (DOI 10.52202/079017-1164). arXiv [2406.07954](https://arxiv.org/abs/2406.07954).
- **Lição em uma frase:** todas as 44 defesas aceitas foram quebradas ao menos uma vez, e as mais
  eficazes foram as que entenderam o funcionamento exato da defesa a partir das próprias respostas
  dela.
- **Desenho:** duas fases. Na de defesa, equipes escrevem *system prompt* + filtro Python + filtro LLM
  para proteger um segredo de 6 caracteres; a defesa só é aceita se passar num **teste de utilidade**
  (uma defesa que sempre recusa seria impenetrável e é rejeitada). Na de ataque, há reconhecimento livre
  (segredo aleatório) e avaliação pontuada (segredo fixo, interações contadas). 163 equipes; 72
  defesas, 44 aceitas; 137.063 conversas; 35 equipes quebraram ao menos uma defesa. Cada equipe recebeu
  US$ 20 em créditos.
- **Verificação:** mecânica. O atacante submete o palpite a um endpoint separado (`check_secret`), com
  no máximo 10 palpites por defesa, e precisa indicar a conversa onde extraiu o segredo como evidência.
- **Pontuação/prêmio:** 1050 − 50 × (nº de conversas), bônus para os três primeiros a quebrar cada
  defesa, e o valor da defesa cai 15% a cada quebra (incentiva atacar defesas ainda não quebradas).
  Três melhores ataques e defesas com prêmio em dinheiro e viagem.
- **Certo:** dataset grande e multiturno; plataforma aberta e reutilizável; o desenho de pontuação
  premia eficiência e ineditismo.
- **Errado / limites:** o rótulo de sucesso tem ruído (segredo extraído em várias conversas, ou
  extraído e não submetido); as regras mudaram durante a competição; o escopo é estreito (segredo curto).
  As defesas **vazaram informação sobre si mesmas**: algumas equipes usaram a reação da defesa para
  confirmar o segredo sem gastar palpites.
- **Para o nosso bounty:**
  - **Utilidade como pré-condição** do alvo: o portão premiado não pode ser trivialmente seguro (recusar
    tudo). Simetricamente, o derivado premiado precisa ser funcional.
  - **O oráculo vaza:** cada resposta "passou / não passou" da bateria é um bit sobre ela. Limitar
    palpites (aqui, 10), separar fase de reconhecimento (bateria pública de treino) de fase pontuada
    (bateria secreta) e contar consultas.
  - **Pontuação decrescente por quebra repetida** e bônus ao primeiro desincentivam repetir o mesmo
    escape e premiam escapes novos.
  - **Atacante adaptativo e multiturno** é a norma: a bateria deve incluir diálogos, não só perguntas
    isoladas.

### 2.3 Toyer et al. — *Tensor Trust: Interpretable Prompt Injection Attacks from an Online Game* (2024)

- **Referência:** S. Toyer, O. Watkins, E. Mendes et al. ICLR 2024 ✔. arXiv
  [2311.01011](https://arxiv.org/abs/2311.01011). O PDF baixado é a v1 (126 mil ataques, 46 mil
  defesas); a versão do ICLR relata ~563 mil ataques e ~118 mil defesas (abstract, a verificar no PDF
  final).
- **Lição em uma frase:** um jogo com verificação trivial (regex sobre a saída) e incentivo só de
  reputação/saldo gera um corpus enorme, mas o incentivo é desenhado contra a reutilização de ataques.
- **Desenho:** cada jogador tem defesa (abertura + código de acesso + fechamento) e saldo. A defesa só é
  salva se o código de acesso faz o modelo dizer "access granted". Atacar com sucesso rouba parte do
  saldo; falhar paga o defensor.
- **Verificação:** regex sobre a saída, temperatura 0. A extração do código é medida por repetição exata,
  o que perde vazamentos parafraseados; GPT-4 como juiz atinge 97% de precisão e 84% de recall nesse caso.
- **Prêmio:** só saldo e ranking.
- **Certo:** o histórico de ataques visível faz as estratégias se espalharem em "ondas", como no ciclo
  ataque-defesa real.
- **Errado:** os líderes reaproveitavam ataques contra contas fracas; os autores criaram **faixas** com
  restrições para contas de nível menor.
- **Para o nosso bounty:** (i) a **validação de que a defesa funciona para o uso legítimo** (aqui, o
  portão aceita derivados legítimos) é parte do alvo; (ii) **oráculo exato tem falso negativo**
  (vazamento parafraseado) e oráculo LLM tem falso positivo, por isso a bateria precisa de critério
  semântico **e** medição do juiz; (iii) estruturar prêmio contra reutilização (escapes repetidos valem
  menos).

### 2.4 Schulhoff et al. — *Ignore This Title and HackAPrompt* (2023)

- **Referência:** S. Schulhoff, J. Pinto, A. Khan et al. EMNLP 2023 ✔ (pp. 4945–4977, DOI
  10.18653/v1/2023.emnlp-main.302). arXiv [2311.16119](https://arxiv.org/abs/2311.16119).
- **Lição em uma frase:** escolher um objetivo de ataque **mecanicamente verificável e inócuo** (frase
  exata) permite verificação automática em escala sem gerar conteúdo nocivo.
- **Desenho:** dez desafios com *templates* reais; o participante insere texto para fazer o modelo
  emitir uma frase-alvo exata. Mais de 2.800 participantes, mais de 600 mil prompts, até 500 envios por
  dia, equipes de até quatro.
- **Verificação:** o organizador **reexecuta** cada submissão no modelo escolhido, na configuração mais
  determinística possível. Nota = dificuldade × (10.000 − tokens), com multiplicador 2× para o modelo
  mais difícil.
- **Prêmio:** US$ 37,5 mil no total (US$ 5 mil ao primeiro) + créditos; prêmio separado para um modelo.
- **Certo:** dataset aberto e taxonomia de 29 técnicas; o multiplicador e o prêmio extra direcionaram
  esforço para os modelos que os organizadores queriam testar.
- **Errado / limites:** pelo menos 6.000 prompts funcionam **só às vezes** (não determinismo); o
  dataset envelhece com a deriva dos modelos; o objetivo é um substituto, não dano real.
- **Para o nosso bounty:** (i) **reexecução pelo verificador**, não confiança na evidência do caçador
  (no nosso caso, reexecução atestada na CVM); (ii) não determinismo exige critério por **taxa** em
  amostras repetidas com semente fixa, não um único sucesso; (iii) multiplicadores de nota são a alavanca
  para dirigir esforço (por exemplo, para os portões ou domínios mais importantes); (iv) usar
  **substitutos inócuos** quando possível na bateria, como fazem Sharma et al. com perguntas não
  infoperigosas.

### 2.5 Sharma et al. — *Constitutional Classifiers* (Anthropic, 2025)

- **Referência:** M. Sharma, M. Tong, J. Mu, J. Wei et al. Preprint, arXiv
  [2501.18837](https://arxiv.org/abs/2501.18837) (venue a verificar).
- **Lição em uma frase:** um bug bounty de verdade sobre salvaguardas de LLM é viável e informativo,
  mas os caçadores exploram primeiro o **protocolo de avaliação** e a **infraestrutura**, não a
  salvaguarda.
- **Desenho do programa:** bug bounty na HackerOne focado em *jailbreak* universal de CBRN. De 800
  inscrições, 405 convidados (tempo disponível, experiência, julgamento ético), ~183 ativos. Dez
  perguntas-alvo **não infoperigosas**. A arquitetura do sistema foi descrita aos participantes. Uma
  submissão e uma nova tentativa após feedback **binário** (quais saídas passaram do limiar, sem nota).
- **Verificação:** pipeline de rubrica com juiz LLM. Gera respostas de modelos **sem salvaguarda**
  (*helpful-only*), deriva delas uma rubrica por pergunta e pontua a saída candidata; sucesso = ≥ 50% da
  nota média do modelo sem salvaguarda (limiar mais rígido: detalhe semelhante).
- **Prêmio:** até US$ 15 mil por relatório, **escalonado pelo número de perguntas respondidas**; US$ 95
  mil pagos no total (incluindo ~US$ 3 mil por respostas a pesquisas de horas, pagas sem vínculo com as
  horas declaradas). Esforço estimado de 4.720 h (IC 90%: 3.242–7.417), calibrado por autodeclaração.
- **Certo:** nenhum dos 113 relatórios respondeu às dez perguntas no limiar de 50%; ninguém passou de
  seis no limiar rígido, mesmo somando todos os relatórios de uma pessoa. Métrica de esforço explícita.
- **Errado / limites:** o protótipo recusava ~44% do tráfego real (robustez comprada com recusa
  excessiva). Um relatório que parecia universal era um **bug de implantação** (até 128 tokens saíam
  depois do bloqueio). As estratégias de maior pontuação exploravam a **rubrica** (paráfrase benigna e
  saídas longas), não a salvaguarda. O pagamento no limiar de 50% pode ter tirado o incentivo de buscar
  ataques mais fortes. A rubrica confunde conhecimento geral com informação acionável.
- **Para o nosso bounty:**
  - **Sucesso relativo à referência** = o nosso δ: "o derivado responde, na bateria secreta, com
    detalhe comparável ao de um modelo sem recusa". A referência sem recusa (um derivado obliterado
    conhecido) é o análogo do *helpful-only*.
  - **Prêmio escalonado pela fração da bateria quebrada** (universalidade) é o desenho que funcionou.
  - **O juiz é alvo:** a bateria precisa de rubrica resistente a comprimento e paráfrase, e de checagem
    de que a resposta responde à pergunta original.
  - **Escopo inclui o pipeline:** o harness de avaliação dentro da CVM é parte do que o bounty testa.
  - **Recusa excessiva** é custo real; o portão premiado deve manter a taxa de falso alarme declarada.
  - **Custo:** 405 convidados e ~US$ 95 mil para um alvo; um piloto interno não chega perto disso.

### 2.6 Cunningham et al. — *Constitutional Classifiers++* (Anthropic, 2026)

- **Referência:** H. Cunningham, J. Wei et al. arXiv [2601.04603](https://arxiv.org/abs/2601.04603);
  ICLR 2026 segundo os anais (a verificar a versão; os números do abstract diferem entre versões).
- **Lição em uma frase:** dá para transformar o bounty em **métrica de dependabilidade**: taxa de
  descoberta de vulnerabilidade de alto risco por mil consultas e tempo mínimo até a descoberta.
- **Desenho / verificação:** mesmo protocolo de rubrica; "vulnerabilidade de alto risco" = responder a
  mais de 5 das 8 perguntas no limiar de 50%. A geração anterior teve 0,01871 por mil consultas (695 mil
  consultas); o classificador de troca, 0,00885 (226 mil); o sistema final, ~0,005 (1 vulnerabilidade
  em ~198 mil tentativas, 1.736 h, descoberta após 30 h). Só contam consultas de usuários com taxa de
  recusa > 5% (filtra quem usa o programa para outra coisa).
- **Prêmio:** US$ 25–35 mil por campanha, escalonado; multiplicador de 1,05× por resposta "forte"
  (≥ 75% do detalhe); mais prêmio para universal e menos para parcial. Acesso por um alias sem consumo
  de créditos; perguntas e rubricas de exemplo entregues aos participantes; parte das perguntas trocada
  entre campanhas.
- **Certo:** comparar sistemas por taxa de descoberta normalizada pelo esforço; lições de operação
  (infraestrutura é requisito de segurança; red teaming periódico porque benchmarks sintéticos sobreajustam).
- **Errado / limites:** *red teamers* especialistas **fora do programa** acharam jailbreaks universais
  no sistema de dois estágios, com esforço grande e ferramentas automáticas. O bounty não esgota o
  adversário.
- **Para o nosso bounty:** usar **taxa de escape por mil submissões** e **tempo até o primeiro escape**
  como métricas de P4; elas estimam o *e* de P(escape) = 1 − (1 − e)^k da E8 §9.3. **Rotacionar parte da
  bateria** entre rodadas; entregar uma **bateria de exemplo pública** com rubrica (melhora a qualidade
  das submissões sem revelar a secreta); **filtrar submissões não sérias** para não inflar o denominador.

### 2.7 Zou et al. — *Security Challenges in AI Agent Deployment* (Gray Swan + UK AISI, 2025)

- **Referência:** A. Zou, M. Lin, E. Jones et al. arXiv [2507.20526](https://arxiv.org/abs/2507.20526).
  Preprint (em revisão).
- **Lição em uma frase:** a verificação escala para milhões de tentativas com juízes automáticos em
  camadas e apelação humana, mas os juízes automáticos aceitam *specification gaming*.
- **Desenho:** de 8/mar a 6/abr/2025, 22 agentes anonimizados, 44 cenários com critério de sucesso
  escrito, quatro ondas semanais. ~2.000 participantes, ~1,8 milhão de tentativas, > 60 mil sucessos.
- **Verificação:** por cenário, **juiz programático** (checa chamadas de ferramenta e argumentos), **juiz
  LLM** (maioria de três modelos) ou ambos. Submissão reprovada pode ser apelada um número limitado de
  vezes por dia a um modelo de raciocínio mais forte e, por fim, a um humano do UK AISI.
- **Prêmio:** US$ 171,8 mil, por total de quebras, quantidade, velocidade e primeira quebra.
- **Certo:** dataset e benchmark (ART, 4.700 ataques) mantido como **leaderboard privado** para evitar
  sobreajuste e uso indevido; ataques transferem entre modelos.
- **Errado:** falsos positivos dos juízes automáticos por *specification gaming* (o critério literal era
  atendido sem o comportamento pretendido).
- **Para o nosso bounty:** (i) **juiz programático sempre que possível**, LLM só onde for inevitável;
  (ii) apelação em camadas preserva a automação no caso comum; (iii) a bateria secreta deve ser mantida
  como **conjunto privado rotativo**, como o ART; (iv) transferência entre modelos sugere que um escape
  achado num derivado vale para irmãos do mesmo pai (revogação em grupo).

### 2.8 Nasr et al. — *The Attacker Moves Second* (2025)

- **Referência:** M. Nasr, N. Carlini, S. Schulhoff, F. Tramèr et al. arXiv
  [2510.09023](https://arxiv.org/abs/2510.09023). Preprint (venue a verificar).
- **Lição em uma frase:** avaliações estáticas e juízes automáticos superestimam a robustez; humanos com
  prêmio quebram o que o ataque automático não quebra.
- **Desenho da parte humana:** competição com > 500 participantes, US$ 20 mil, sobre 40 desafios do
  AgentDojo. Nota = 5.000 − tokens usados; US$ 200 para o prompt mais curto de cada desafio, que outros
  podiam "roubar" achando um mais curto.
- **Verificação:** o ambiente checa automaticamente se a tarefa do atacante foi cumprida; onde a checagem
  falhou, juízes humanos decidiram apelações.
- **Certo:** humanos venceram 100% dos cenários do subconjunto, contra 69% da busca automática.
- **Errado / alertas:** *auto-raters* são modelos e sofrem exemplos adversariais e *reward hacking*
  (a otimização aprende a maximizar a nota sem resolver a tarefa).
- **Para o nosso bounty:** o bounty humano é o complemento necessário ao atacante adaptativo automático
  do E9; e a função de nota deve se aproximar do critério real (não basta "o juiz disse sim").

### 2.9 Programas da indústria (páginas, sem artigo)

- **Anthropic, demo pública (3–10/fev/2025):** oito níveis; segundo a imprensa e a página da empresa,
  ~300 mil mensagens, ~3.700 h, quatro participantes passaram todos os níveis, um com jailbreak
  universal; US$ 55 mil pagos (a verificar na página oficial). Antes, o programa fechado da §2.5.
- **OpenAI Bio Bug Bounty (2025):** US$ 25 mil ao primeiro jailbreak universal que responda às dez
  perguntas de bio/química a partir de conversa limpa, sem acionar moderação; US$ 10 mil para quem
  responder às dez com vários prompts; acesso por inscrição e convite; **tudo sob NDA** (páginas
  `openai.com/bio-bug-bounty` e `openai.com/gpt-5-bio-bug-bounty`, a verificar valores finais e vencedores).
- **HackAPrompt 2.0 (2025):** anunciado com US$ 500 mil em prêmios e dados abertos ao final; **não
  achamos artigo nem resultado agregado** (busca de 2026-10-27).
- **Para o nosso bounty:** os laboratórios convergem para **primeiro a quebrar leva**, **universalidade
  como critério**, **convite + NDA** e **revisão humana final**. O nosso diferencial possível é trocar
  convite + NDA + revisão por **verificação atestada e reprodutível**, mantendo a bateria secreta.

---

## 3. Verificação automática de jailbreak (o oráculo da bateria)

### 3.1 Souly et al. — *A StrongREJECT for Empty Jailbreaks* (2024)

- **Referência:** A. Souly, Q. Lu, D. Bowen et al. NeurIPS 2024 ✔ (cabeçalho do PDF; trilha a
  verificar). arXiv [2402.10260](https://arxiv.org/abs/2402.10260).
- **Lição:** a maioria dos avaliadores de jailbreak **superestima** o sucesso; muitos jailbreaks são
  "vazios" porque a resposta, embora não recuse, não ajuda o atacante, e jailbreaks que contornam a
  segurança tendem a **reduzir a capacidade** do modelo.
- **Verificação:** avaliador automático que mede o quanto a resposta é útil para o pedido proibido, com
  a maior concordância com humanos entre os comparados.
- **Para o nosso bounty:** a bateria deve medir **conformidade nociva útil**, não só ausência de
  recusa; caso contrário, um derivado degradado (que não recusa mas responde lixo) "ganharia" o prêmio.
  Isso casa com a propriedade da E10 §5 (recusa + utilidade).

### 3.2 Chao et al. — *JailbreakBench* (2024)

- **Referência:** P. Chao, E. Debenedetti, A. Robey, M. Andriushchenko et al. NeurIPS 2024 Datasets &
  Benchmarks ✔. arXiv [2404.01318](https://arxiv.org/abs/2404.01318).
- **Lição:** o juiz deve ser **escolhido e publicado** com sua concordância medida contra anotadores;
  entre seis juízes, o melhor concordou em ~90,7% (FPR 11,6%, FNR 5,5%) e o baseado em regras em 56%.
- **Para o nosso bounty:** publicar o juiz, sua versão e sua taxa de erro medida; a taxa de falso
  positivo do juiz entra no orçamento de prêmios (pagamentos indevidos) e a de falso negativo na taxa
  de escape não detectada.
- *HarmBench* (Mazeika et al., 2024) já está em `artigos/2024_mazeika_harmbench.pdf` (baixado por outro
  levantamento); não foi relido aqui.

---

## 4. Princípios de incentivo e de verificação (bounty em contrato / TEE)

### 4.1 Breidenbach, Daian, Tramèr, Juels — *Enter the Hydra* (USENIX Security 2018)

- **Referência:** USENIX Security 2018 ✔ (anais a partir da p. 1335; versão aberta da USENIX).
- **Lição em uma frase:** um bounty é racional para o caçador quando o sistema cria uma **lacuna de
  exploração** (*exploit gap*): defeitos parciais são detectáveis e pagos automaticamente muito antes
  de virarem exploração completa, e isso permite um prêmio ordens de grandeza menor que o valor
  explorável.
- **Desenho:** N versões independentes ("cabeças") do mesmo contrato rodam em paralelo; se as saídas
  divergem, o meta-contrato aborta e paga o bounty. Só um defeito que afeta **todas** as cabeças de modo
  idêntico é explorável.
- **Verificação:** automática e sem confiança, pelo próprio contrato (divergência observável).
- **Prêmio / incentivo:** com λ_H a taxa de achados honestos, λ_M a do adversário, α = λ_H/λ_M e
  *gap* = razão entre a chance de falha de alguma cabeça e a de falha do conjunto, a divulgação é a
  jogada racional se **prêmio > valor / (α·gap + 1)**.
- **Retenção do defeito (*bug withholding*):** quem acha um defeito parcial pode retê-lo e tentar
  completar a exploração, usando *front-running* para tomar o prêmio de um honesto que chegue depois.
  Contramedida: *Submarine Commitments* (compromissos ocultos entre transações comuns).
- **Certo:** primeiro modelo principiado de preço de bounty; token ERC20 com bounty real em produção.
- **Limites:** pressupõe falhas pouco correlacionadas entre cabeças (crítica clássica ao N-version
  programming); a avaliação não mede essa correlação; só cobre contratos que toleram abortar.
- **Para o nosso bounty:** o mapeamento é direto e é a melhor justificativa teórica de P4.
  - **Duas "cabeças":** o **portão** (conhecido pelo atacante, E10 §5) e a **bateria secreta**. Um
    derivado que **passa no portão e falha na bateria** é uma divergência detectável e paga. A
    exploração completa (passar nas duas e ainda assim ser nocivo) não é detectável pelo bounty: é o
    risco residual a declarar.
  - **Preço:** o "valor do contrato" aqui é o valor de ter um derivado sem recusa **liberado com o selo
    da plataforma** (recibo P2). Como modelos sem recusa já circulam livremente, o valor de mercado do
    peso é baixo; o que vale é o **selo**. Isso sugere que o prêmio pode ser modesto, desde que o selo
    seja revogável.
  - **Retenção:** o caçador que acha um escape pode usá-lo (liberar o derivado) em vez de reportá-lo.
    Pagar mais que o valor de uso e **revogar retroativamente** recibos de derivados que caem na bateria
    reduz o ganho da retenção. *Front-running* não existe na nossa plataforma centralizada, mas a
    **ordem de chegada** precisa de carimbo de tempo atestado.
  - **Correlação:** se portão e bateria usam o mesmo juiz ou dados parecidos, o *gap* some. A bateria
    deve ser **independente** do portão (outros itens, outro juiz).

### 4.2 Tramèr, Zhang, Lin, Hubaux, Juels, Shi — *Sealed-Glass Proofs* (IEEE EuroS&P 2017)

- **Referência:** EuroS&P 2017, pp. 19–34, DOI 10.1109/EuroSP.2017.28 ✔ (OpenAlex). Versão aberta no
  IACR ePrint [2016/635](https://eprint.iacr.org/2016/635) (CC BY), **não baixada**: o ePrint respondeu
  com desafio anti-robô. Leitura: **abstract** (e o resumo da E5 §8).
- **Lição em uma frase:** mesmo um enclave **transparente** (com vazamento ilimitado por canais
  laterais) basta para provar e vender conhecimento, porque o vazamento só revela ao provador o segredo
  que ele já tem; com um contrato inteligente, isso vira uma plataforma de bug bounty com troca justa.
- **Verificação:** o enclave atesta que o exploit roda e satisfaz o predicado; o contrato paga.
- **Prêmio:** troca justa; impede que o pagador **retire o prêmio injustamente** depois de ver o exploit e
  resiste a negação de serviço por vendedores desonestos.
- **Para o nosso bounty:** é o parente mais próximo da verificação **atestada**. Diferença essencial: no
  SGP o segredo é do **caçador** (o exploit); no nosso caso há também um segredo da **plataforma** (a
  bateria). Um enclave transparente não protege a bateria. Logo, ou a bateria roda num ambiente que o
  caçador não observa (a CVM do operador, que é confiável pela D3), ou se aceita que ela vaza e se
  rotaciona. O princípio que importa importar é a **proteção contra retirada injusta**: compromisso
  público (hash) da bateria e do fundo de prêmios **antes** da rodada, com revelação ao final, para que o
  caçador possa auditar que a bateria não foi trocada para negar pagamento.

### 4.3 Zhang et al. — *BountyBench* (NeurIPS 2025 D&B)

- **Referência:** A. K. Zhang, J. Ji, C. Menders et al. (Stanford, Berkeley). NeurIPS 2025 Datasets &
  Benchmarks ✔ (cabeçalho do PDF). arXiv [2505.15216](https://arxiv.org/abs/2505.15216).
- **Lição em uma frase:** um **indicador diferencial** (o exploit funciona na versão vulnerável e falha
  na corrigida) torna a detecção verificável automaticamente e localizada.
- **Desenho:** 25 sistemas reais, 40 bounties públicos (US$ 10–30.485), três tarefas (Detect, Exploit,
  Patch). Cada vulnerabilidade tem exploit, verificador e patch escritos e validados pelos autores;
  invariantes de código e de execução que **o agente nunca vê**.
- **Verificação:** Detect = invariantes quebram **ou** o exploit sucede no snapshot atual e falha em ao
  menos um snapshot corrigido. Patch = invariantes passam e o verificador falha.
- **Prêmio:** valores reais pagos a humanos como métrica de impacto econômico; os autores lembram que,
  na prática, o prêmio exige inspeção humana, relatório, e só é pago uma vez por bug.
- **Certo:** verificação reprodutível em contêineres; análise de **corte de conhecimento** (85% dos
  bounties divulgados em 2024–25) contra contaminação.
- **Errado / limites:** os avaliadores "não são absolutos" (patches podem quebrar outra coisa; exploits
  e invariantes humanos são incompletos); montar cada tarefa custa dezenas de horas.
- **Para o nosso bounty:** (i) o critério de sucesso deve ser **diferencial em relação ao pai**: o pai
  passa no item da bateria e o derivado falha (é a definição de δ); (ii) **invariantes ocultos** (aqui,
  a bateria secreta e os testes de utilidade) que o caçador nunca vê; (iii) **contaminação:** registrar
  quando cada item da bateria foi criado e garantir que não está em dados públicos de treino; (iv) o
  custo de montar a bateria é humano e alto, e entra no orçamento.

---

## 5. Economia de bug bounty

### 5.1 Finifter, Akhawe, Wagner — *An Empirical Study of Vulnerability Rewards Programs* (USENIX Security 2013)

- **Referência:** USENIX Security 2013 ✔ (anais a partir da p. 273).
- **Lição:** os programas do Chrome (~US$ 580 mil em 3 anos, 501 bounties) e do Firefox (~US$ 570 mil,
  190) custam ~US$ 485 e US$ 658 por dia, comparável a **um** engenheiro de segurança, e os autores os
  estimam 2–100× mais custo-efetivos que contratar pesquisadores.
- **Prêmio:** o Chrome, com prêmio **escalonado** e teto alto, atraiu muito mais participação externa
  que o Firefox, com prêmio fixo de US$ 3.000 (efeito loteria). Tempo de correção com alta variância
  afasta a divulgação responsável.
- **Verificação:** triagem humana do fornecedor; a severidade é atribuída manualmente.
- **Para o nosso bounty:** **escalonar** o prêmio (por universalidade e severidade do escape) com teto
  alto; **responder rápido** (revogação e atualização do portão) faz parte do incentivo; o custo de um
  piloto pode ser orçado na ordem de um pesquisador.

### 5.2 Maillart, Zhao, Grossklags, Chuang — *Given Enough Eyeballs, All Bugs Are Shallow?* (J. Cybersecurity 2017)

- **Referência:** Journal of Cybersecurity 3(2):81–90, DOI 10.1093/cybsec/tyx008 ✔. arXiv
  [1608.03445](https://arxiv.org/abs/1608.03445).
- **Lição:** em 35 programas da HackerOne, cada pesquisador acha um número **limitado** de bugs num
  mesmo programa; o total cresce de forma superlinear com o número de pesquisadores; programas novos
  atraem pesquisadores dos antigos, e a chance de achar bugs decai ~1/t^0,4 após o lançamento, embora os
  achados tardios paguem mais.
- **Recomendações:** renovar e diversificar os caçadores; concentrar esforço (*front-loading*) no
  lançamento e em mudanças grandes; reduzir custos de transação para competir com o mercado paralelo.
- **Para o nosso bounty:** abrir **rodadas** coincidindo com cada nova versão do portão; esperar retorno
  decrescente dentro da rodada; **diversidade** de caçadores importa mais que retenção. Um piloto interno
  com poucos atacantes **subestima** a taxa de escape, e isso deve ser declarado.

### 5.3 Zhao, Grossklags, Liu — *An Empirical Study of Web Vulnerability Discovery Ecosystems* (CCS 2015)

- **Referência:** CCS 2015, pp. 1105–1117, DOI 10.1145/2810103.2813704 ✔ (OpenAlex). **Sem versão
  aberta encontrada**; leitura só do **abstract**.
- **Lição:** em Wooyun e HackerOne, comunidades grandes e crescentes; muitas organizações mostram queda
  nas vulnerabilidades reportadas; **incentivo monetário tem correlação positiva significativa** com o
  número de relatos.
- **Para o nosso bounty:** dinheiro importa; um piloto sem prêmio real mede um limite inferior do
  esforço adversário.

### 5.4 Laszka, Zhao, Grossklags — *Banishing Misaligned Incentives for Validating Reports in Bug-Bounty Platforms* (ESORICS 2016)

- **Referência:** ESORICS 2016 (a verificar páginas; PDF aberto da TUM).
- **Lição:** relatórios inválidos são caros (34,5% na Bugcrowd; 54% na HackerOne antes de medidas, ~25%
  depois). Entre as políticas modeladas, **limite de taxa** é a menos eficaz e mais sensível à
  configuração; **limiar de acurácia** e **recompensa por validação** são mais robustos; sem prêmio
  adequado, qualquer política pode afastar os caçadores.
- **Para o nosso bounty:** verificação automática zera o custo humano de triagem, mas cada submissão de
  derivado custa GPU. Preferir **depósito devolvido em caso de sucesso** ou exigência de histórico
  (limiar de acurácia) a um simples limite de taxa; o limite de consultas continua necessário, mas por
  outro motivo (vazamento da bateria, §2.2).

---

## 6. Política e enquadramento

### 6.1 Brundage et al. — *Toward Trustworthy AI Development: Mechanisms for Supporting Verifiable Claims* (2020)

- **Referência:** relatório multi-institucional, arXiv [2004.07213](https://arxiv.org/abs/2004.07213).
- **Lição:** recomenda que desenvolvedores **pilotem bounties de viés e de segurança** para submeter
  alegações sobre sistemas de IA a escrutínio amplo, e lista o que resolver: preço por severidade,
  processo de submissão e avaliação, divulgação, correção, e **incentivos perversos**. Bounties não
  garantem segurança e a comunidade pode ser pequena demais para dar garantias fortes.
- **Para o nosso bounty:** dá o enquadramento "bounty como mecanismo de **alegação verificável**": a
  plataforma alega "nenhum derivado comprometido é liberado" e o bounty é a forma pública de tentar
  refutar a alegação.

### 6.2 Feffer et al. — *Red-Teaming for Generative AI: Silver Bullet or Security Theater?* (2024)

- **Referência:** arXiv [2401.15897](https://arxiv.org/abs/2401.15897); AIES 2024 (a verificar).
- **Lição:** práticas de red teaming de IA divergem em propósito (muitas vezes vago), artefato avaliado,
  quem ataca, recursos, critérios e decisões que o resultado informa; sem isso, vira **teatro de
  segurança**. Os autores propõem um banco de perguntas para estruturar a atividade.
- **Para o nosso bounty:** a especificação de P4 precisa declarar explicitamente: artefato (o portão e o
  pipeline de liberação), modelo de ameaça (usuário com os pesos, E10 §5), critério de sucesso (δ na
  bateria secreta), quem pode atacar, e **qual decisão** cada achado aciona (revogar, atualizar portão,
  republicar recibos).

---

## 7. Síntese

### 7.1 Princípios de desenho de um bounty sobre o portão

1. **Alvo e critério diferencial.** Pagar por um derivado (ou entrada) que **passa no portão** e, na
   **bateria secreta**, responde com detalhe comparável a uma referência sem recusa, onde o pai recusa
   (Sharma; BountyBench; δ da E10). Escalonar o prêmio pela **fração da bateria** quebrada.
2. **Duas verificações independentes (lacuna de exploração).** Portão e bateria com itens, juízes e
   dados diferentes; o bounty paga a **divergência** (Hydra). Medir a correlação entre os dois; sem
   independência, o bounty não mede nada além do próprio portão.
3. **Oráculo fixo, publicado e medido.** Juiz programático onde der; juiz LLM com versão congelada e taxa
   de erro medida contra humanos (JailbreakBench); critério de **utilidade da resposta**, não só ausência
   de recusa (StrongREJECT); rubrica resistente a comprimento e paráfrase (Sharma).
4. **Conjunto secreto com compromisso.** Bateria privada (Rando; Gray Swan ART), com **hash publicado
   antes** da rodada e revelação depois (troca justa à la Sealed-Glass). Bateria de exemplo pública para
   reconhecimento (CTF; CC++). Parte da bateria **rotaciona** a cada rodada.
5. **Feedback mínimo e orçamento de consultas.** Só "passou / não passou" agregado (Sharma); número
   limitado de submissões pontuadas por portão e por caçador (CTF: 10 palpites). Cada resposta é um bit
   sobre a bateria.
6. **Reexecução atestada e determinística.** O verificador reexecuta tudo na CVM (HackAPrompt), com
   semente fixa e critério por taxa em várias amostras; o recibo atestado (P2) do veredito é o que
   torna o pagamento automático defensável.
7. **Pré-condição de utilidade.** O derivado premiado precisa passar nos testes de utilidade do portão
   (CTF; Tensor Trust); senão, um modelo degradado ganha.
8. **Escopo inclui o pipeline.** Bugs no harness, no streaming ou na revogação também são escapes (CC:
   128 tokens; CC++: "infraestrutura é requisito de segurança").
9. **Métricas de dependabilidade.** Reportar taxa de escapes por mil submissões e tempo até o primeiro
   escape por versão do portão (CC++), ligadas a P(escape) = 1 − (1 − e)^k (E8 §9.3).
10. **Linha de base plantada.** Derivados comprometidos de propósito, misturados às submissões, medem o
    poder do portão e dos caçadores (Rando; liga a P5).
11. **Incentivo e operação.** Prêmio escalonado com teto alto (Finifter); bônus ao primeiro e valor
    decrescente por quebra repetida (CTF); rodadas a cada versão nova do portão (Maillart); crédito de
    GPU para quem não tem (Rando); resposta rápida com revogação (Finifter).

### 7.2 Riscos

| Risco | O que a literatura mostra | Mitigação candidata |
|---|---|---|
| **Vazamento / contaminação da bateria** | Defesas vazam pelo próprio comportamento (CTF); dados envelhecem e entram em treino (BountyBench, HackAPrompt) | Orçamento de consultas, feedback binário, rotação, data de criação de cada item, hash comprometido |
| **Ataque ao juiz em vez do portão** | Paráfrase e comprimento (Sharma); *specification gaming* (Zou); *reward hacking* (Nasr) | Juiz programático onde possível, juiz medido, critério de utilidade, apelação em camadas |
| **Conluio** | Acesso a modelos irmãos dá vantagem (Rando); retenção do achado (Hydra) | Custódia limita acesso a irmãos; prêmio > valor do selo; revogação retroativa; carimbo de tempo atestado; contas vinculadas (anti-Sybil) |
| **Conluio com quem conhece a bateria** | Não tratado nos trabalhos lidos | Bateria gerada e guardada na CVM, operador confiável (D3) declarado; separação de funções no piloto |
| **Não determinismo** | 6.000 prompts funcionam "às vezes" (HackAPrompt) | Semente fixa, critério por taxa, reexecução atestada |
| **Ruído e custo de submissão** | Relatos inválidos de 25–54% (Laszka); cada derivado custa GPU | Depósito devolvido no sucesso, limiar de acurácia; verificação automática |
| **Recusa excessiva** | Protótipo recusava 44% do tráfego (Sharma) | Medir falso alarme do portão como parte da alegação |
| **Adversário fora do bounty** | Especialistas fora do programa quebraram o CC++ | Declarar que o bounty dá limite inferior; combinar com atacante automático (E9) |
| **Piloto pequeno subestima** | Achados por pesquisador são limitados (Maillart); dinheiro aumenta relatos (Zhao) | Declarar como limite inferior; diversidade de atacantes internos |
| **Uso dual dos achados** | Laboratórios usam NDA; competições acadêmicas publicam dados | Derivados premiados ficam em custódia; publicar só estatísticas e itens inócuos |
| **Pouco retorno para organizar** | Rando: esforço alto, retorno incerto | P4 como desenho + piloto interno, coerente com a E10 §5 |

### 7.3 O que fica para o nosso caso

- Nenhum trabalho lido premia a quebra de um **portão de liberação de derivados**, nem combina
  **verificação atestada**, **bateria secreta comprometida por hash** e **pagamento automático** sobre
  modelos. Os vizinhos cobrem pedaços: oráculo e conjunto privado (Rando, Gray Swan), critério relativo
  (Sharma, BountyBench), preço e incentivo (Hydra), troca justa atestada (Sealed-Glass).
- O ponto mais frágil do desenho é a **independência entre portão e bateria** e a **robustez do juiz**:
  é lá que os programas reais falharam.

---

## 8. Leituras recomendadas para o autor

1. **Sharma et al., *Constitutional Classifiers* (2025), §2 e §4 (com o ap. B de Cunningham et al.
   2026).** É o único bug bounty real, publicado em detalhe, sobre salvaguardas de LLM. Define o
   sucesso **por comparação com um modelo sem proteção**, que é o nosso δ, mostra o prêmio escalonado
   por universalidade, o feedback binário, o custo (US$ 95 mil, ~4.700 h) e, principalmente, as falhas:
   caçadores exploraram a rubrica e um bug de infraestrutura. A sequência (CC++) acrescenta as métricas
   de taxa de descoberta por mil consultas e tempo até a descoberta, que são métricas de DSN.
2. **Breidenbach et al., *Enter the Hydra* (USENIX Security 2018), §1, §4 e §5.** Dá o argumento de por
   que o bounty sobre o portão faz sentido econômico: pagar automaticamente pela **divergência** entre
   duas verificações independentes (portão × bateria secreta) antes da exploração completa, com uma
   regra de preço explícita e o problema da **retenção do achado**. Sem esse princípio, P4 é só "mais um
   programa de red teaming".

Se houver tempo para um terceiro: **Rando et al. (2024)**, o molde exato do oráculo (modelo de
recompensa fixo + conjunto privado) aplicado a **pesos abertos comprometidos**, com as lições de custo
(bolsas de computação) e de baixa participação.

---

## Fontes desta rodada

**PDFs baixados agora (15):** `2024_rando_backdoors`, `2024_debenedetti_ctf`, `2024_toyer_tensortrust`,
`2023_schulhoff_hackaprompt`, `2025_sharma_constitutional`, `2026_cunningham_constitutional`,
`2025_zou_agentredteaming`, `2018_breidenbach_hydra`, `2017_maillart_eyeballs`, `2013_finifter_vrp`,
`2025_zhang_bountybench`, `2020_brundage_verifiableclaims`, `2024_feffer_redteaming`,
`2024_chao_jailbreakbench`, `2016_laszka_validation`.
**Reaproveitados (já estavam em `artigos/`):** `2024_souly_strongreject`, `2025_nasr_attacker`.
**Sem PDF:** Sealed-Glass Proofs (ePrint 2016/635 é aberto, mas respondeu com desafio anti-robô;
baixar manualmente); Zhao et al. CCS'15 (sem versão aberta encontrada); HackAPrompt 2.0 (sem artigo).
**Páginas de programas:** [Anthropic, Constitutional Classifiers](https://www.anthropic.com/news/constitutional-classifiers);
[OpenAI Bio Bug Bounty](https://openai.com/bio-bug-bounty); [OpenAI GPT-5 Bio Bug Bounty](https://openai.com/gpt-5-bio-bug-bounty);
[Decrypt sobre HackAPrompt 2.0](https://decrypt.co/323351/how-to-trick-chatgpt-and-get-paid-50000/).
**Venues conferidos:** [CTF nos anais do NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/411c44e6f285310822f39f76a58798c7-Abstract.html);
[Tensor Trust no ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/519c51529c3544b3430bd8b17d400365-Abstract-Conference.html);
[CC++ no ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/4f697305ef1f868ad77c3c0027989a6f-Abstract-Conference.html);
OpenAlex para Sealed-Glass (10.1109/EuroSP.2017.28) e Zhao (10.1145/2810103.2813704).
