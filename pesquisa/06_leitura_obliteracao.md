# Leitura: remoção de recusa, fine-tuning nocivo, defesas nos pesos e avaliação de recusa

**Data:** 2026-10-27 · **Problema de referência:** [E10](../DSN2027/etapas/E10_problema.md) §3 e §5
(P1: nenhum derivado comprometido é liberado; recusa ≥ pai − δ, sem perder utilidade; adversário =
usuário com os pesos dentro da CVM, que conhece o portão).
**Ponto de partida:** [05](05_protecao_modelos.md) §2, §3, §6; [02](02_transparencia_execucao_llm.md) §6;
[03](03_confiabilidade_llm.md).
**Objetivo:** base científica. Nada aqui é implementação, e nada descreve como executar um ataque:
os ataques aparecem só no nível do que cada artigo mostra.

**Convenções.**
- **Venue:** ✔ = conferido nesta rodada no PDF baixado, na página do arXiv (campo *comments*) ou no
  OpenAlex; ✔02 = conferido em rodada anterior ([02](02_transparencia_execucao_llm.md)) e não
  reaberto; **(a verificar)** = não conferido na fonte primária.
- **Páginas** referem-se ao PDF em `pesquisa/artigos/` (numeração do arquivo, não dos anais). Desde 2026-10-27 o acervo guarda só a base teórica, por camada e tema ([índice](artigos/README.md)); os PDFs descartados seguem no commit `f0fba2a`.
- **Leitura:** "corpo inteiro" = introdução, método, avaliação e limitações lidos; "seções-chave" =
  resumo, resultados principais e limitações.
- Todos os PDFs abaixo vêm do arXiv (acesso aberto) e foram conferidos com `pdfinfo`.

---

## 0. Resumo em seis linhas

1. A recusa de modelos abertos é **mecanicamente rasa**: uma (ou poucas) direções nas ativações a
   medeiam, e removê-la mantém a utilidade (Arditi; Wollschläger). Fine-tuning com poucos exemplos,
   ou até benigno, também a desfaz (Qi 2024).
2. **Salvaguardas nos pesos não duram** sob avaliação adaptativa (Qi 2025a; Casper; Kuo): o estado
   da arte resiste a "algumas centenas de passos", e o próprio TAR protege mal a *recusa*.
3. **Detectar** o derivado obliterado funciona como triagem (Hurtado: AUROC 0,95; Egler: 56,2% a 1%
   de FPR), mas cada detector **supõe o que só um custodiante garante**: referência autêntica,
   acesso a dados + pré + pós, e derivado retido até o veredito.
4. Os mesmos artigos mostram o **limite** que a tese precisa encarar: um dono *white-box* que
   conhece o detector treina o derivado para passar nele e continuar sem recusa (Hurtado §5), e o
   fine-tuning cifrado engana avaliação estática (Halawi).
5. A **avaliação de recusa** tem armadilhas próprias: juízes enganáveis pelo próprio modelo avaliado
   (Eiras), "recusa" ≠ "dano" (StrongREJECT), recusa excessiva (XSTest), sensibilidade a semente,
   *template* e configuração (Qi 2025a; HarmBench).
6. **Correção de dado da E10:** o modelo com "> 19 milhões de downloads" em Lin et al. é o
   **Mistral-7B-v0.1**, um modelo publicado sem moderação, e não um derivado que perdeu a recusa
   (p. 2). A contagem de 11.598 "ULLMs" mistura modelos nunca alinhados e derivados obliterados.

---

## 1. Remoção de recusa (obliteração) e sua detecção

### 1.1 Arditi et al., *Refusal in Language Models Is Mediated by a Single Direction*

- **Referência:** A. Arditi, O. Obeso, A. Syed, D. Paleka, N. Panickssery, W. Gurnee, N. Nanda.
  NeurIPS 2024 ✔ (rodapé da p. 1). arXiv 2406.11717. PDF: `2024_arditi_refusal.pdf`.
  Leitura: corpo inteiro (§1–§4, §7).
- **Lição:** em 13 modelos abertos (1,8B–72B), uma única direção nas ativações é necessária e
  suficiente para a recusa; tirá-la dos pesos desliga a recusa quase sem custo de utilidade.
- **Problema que define:** entender o mecanismo da recusa e mostrar que ele é frágil para quem tem
  acesso *white-box*.
- **Método:** direção por diferença de médias de ativações entre instruções nocivas e inócuas;
  ablação dessa direção (nas ativações ou, de forma equivalente, nos pesos); avaliação por
  *substring* de recusa + Llama Guard 2 (§2.5, p. 4–5) e pelo HarmBench (§4.2).
- **Evidência principal:**
  - ablação reduz recusa e eleva respostas inseguras em todos os modelos (Fig. 1, §3.1);
  - adicionar a direção faz o modelo recusar pedidos inócuos (Fig. 3, §3.2);
  - ASR no HarmBench da edição de pesos comparável ou superior a ataques otimizados por *prompt*
    (Tab. 2, p. 6); com e sem *system prompt* o resultado muda muito no Llama-2 (22,6% × 79,9%);
  - MMLU, ARC e GSM8K praticamente inalterados; só TruthfulQA cai 1–3,5 pontos (Tab. 3, p. 7);
  - custo declarado: < US$ 5 de computação para um modelo de 70B (§7, p. 10).
- **Limitações (dos autores, p. 10):** extração heurística da direção; "prova de existência", não
  estudo ótimo; métricas de coerência imperfeitas; semântica da direção incerta ("recusa" pode ser
  "dano"); sem modelos proprietários ou maiores.
- **Para a nossa tese:**
  - **Apoia** a motivação: obliterar é barato e preserva utilidade, logo **checagem de utilidade
    não pega obliteração** e testes de capacidade não substituem a bateria de recusa.
  - A edição é de **posto baixo** no delta dos pesos, o que dá um sinal de auditoria (usado por
    Hurtado).
  - **Exige** que a bateria do portão rode **sem e com *system prompt*** e meça recusa por juiz,
    não só por *substring* (a própria Arditi separa recusa e segurança).

### 1.2 Wollschläger et al., *The Geometry of Refusal in LLMs: Concept Cones and Representational Independence*

- **Referência:** T. Wollschläger, J. Elstner, S. Geisler, V. Cohen-Addad, S. Günnemann,
  J. Gasteiger. arXiv 2502.17420 ✔; ICML 2025 (a verificar; OpenAlex registra só o arXiv).
  PDF: `2025_wollschlager_geometry.pdf`. Leitura: seções-chave.
- **Lição:** a recusa não é uma direção só: há várias direções independentes e cones
  multidimensionais que a medeiam.
- **Problema que define:** como ataques contornam a recusa, se a hipótese de "direção única" é
  incompleta.
- **Método:** busca de direções de recusa por gradiente (em vez de diferença de médias) e um
  critério de independência sob intervenção (ortogonal ≠ independente).
- **Evidência principal:** direções mecanicamente independentes e cones em que todas as direções
  mediam recusa (resumo e §1–§2, p. 1–2).
- **Limitações:** não lido o bastante para listar; modelos e escala a verificar.
- **Para a nossa tese:** **exige** que nenhum sinal do portão dependa de uma direção canônica só.
  Um atacante que remove recusa por uma direção "não canônica" escapa de um detector de direção
  única (Hurtado confirma isso no App. B). Sinal comportamental é obrigatório.

### 1.3 Hurtado, *Has This Checkpoint Been Abliterated? A Two-Signal Audit and Its Failure Map*

- **Referência:** G. Hurtado (Moonsong Labs). Preprint cs.CR, v2 ago/2026 ✔ ("Preprint – Under
  review", p. 1). arXiv 2607.01854. PDF: `2026_hurtado_abliterated.pdf`. Leitura: corpo inteiro e
  apêndices B, C e E.
- **Lição:** dois sinais internos baratos separam abliterações públicas de edições benignas com
  AUROC 0,95, **desde que a referência seja atestada**; uma referência forjada ou um dono
  *white-box* que treina contra o detector quebram a auditoria.
- **Problema que define:** uma plataforma não sabe, antes de implantar, se um *checkpoint* aberto
  teve a recusa removida; guardas de execução avaliam gerações, não o artefato.
- **Método:** (i) razão do "gap de recusa" nas ativações do candidato sobre o da referência;
  (ii) energia de posto 1 do delta de pesos referência→candidato (primitivo WeightWatch); soma de
  z-scores; limiar por Youden num conjunto de calibração. Rótulo de verdade por um guarda
  comportamental (Qwen3Guard), confirmado por um segundo guarda (κ = 0,78, App. E).
- **Evidência principal:**
  - registro de 273 *checkpoints*; 94 avaliados (57 abliterados × 37 benignos: fine-tunes,
    *merges*, *instruction-tunes*); AUROC 0,95 [0,90–0,98], contra 0,84 e 0,90 de cada sinal
    sozinho (Tab. 1, p. 3);
  - transferência para famílias não vistas: acurácia balanceada 0,89, FPR 0,11, 4 de 57 perdidos
    (Tab. 1 e Fig. 1, p. 3–4);
  - **referência forjada** (declarar um irmão já abliterado como base) evade os dois eixos sem
    treino; usar o próprio candidato como referência evade por construção (§5, p. 5);
  - **dono *white-box*** treina um Qwen2.5-1.5B até o escore cair abaixo do limiar, com 20/20
    respostas inseguras e MMLU 0,58 × 0,59 (§5 e Fig. 3, p. 5); fine-tuning "natural" (6 SFT/DPO)
    **não** abre esse buraco: o ataque exige otimização dirigida ao detector;
  - o eixo de pesos dispara em **qualquer** edição de posto baixo, inclusive endurecimento de
    segurança (App. B, p. 9–10);
  - App. E (p. 12): "a atestação da base, não o escore, é a raiz de confiança"; recomenda obter a
    referência por hash assinado pelo publicador ou proveniência de treino atestada em hardware.
- **Limitações (§6, p. 6):** amostra pequena (57/37), ICs largos; rótulo certifica recusa, não
  inocuidade; negativos sem modelos endurecidos (FPR otimista); ataque adaptativo em uma família e
  uma escala; modelos de raciocínio parcialmente fora do alcance do gap.
- **Para a nossa tese:**
  - **Apoia diretamente** a custódia: a falha mais grave (referência forjada) **vira falha de
    atestação** quando a plataforma guarda o pai pelo digest. É o argumento central de P1.
  - **Contradiz** qualquer pretensão de que sinais internos bastem contra o nosso adversário: o
    usuário com os pesos que conhece o portão é exatamente o "dono *white-box*" do §5. **Exige**
    que o portão (a) combine sinais internos com bateria comportamental, (b) mantenha parte da
    bateria secreta e (c) seja avaliado com esse ataque adaptativo.
  - **Exige** medir FPR também em derivados **endurecidos** (mais recusa), não só em benignos.
  - O registro de 57 abliterações públicas é material para a P5 (injeção × campo).

### 1.4 Abu Shairah et al., *An Embarrassingly Simple Defense Against LLM Abliteration Attacks*

- **Referência:** H. Abu Shairah, H. A. A. K. Hammoud, B. Ghanem, G. Turkiyyah (KAUST).
  Preprint 2025 ✔ ("under review"). arXiv 2505.19056. PDF: `2025_abushairah_abliteration.pdf`.
  Leitura: seções-chave.
- **Lição:** treinar recusas longas e justificadas espalha o sinal de recusa e faz a abliteração
  derrubar a recusa em no máximo ~10 pontos, contra 70–80 nos modelos de base (resumo, p. 1; §4–5).
- **Problema que define:** a recusa breve e formulaica cria um caminho isolado e fácil de remover.
- **Método:** fine-tuning em um conjunto de "recusa estendida"; avaliação em Llama-2-7B-Chat e
  Qwen2.5 1,5B/3B.
- **Evidência principal:** recusa de base cai 70–80 pontos com abliteração; a dos modelos com
  recusa estendida cai ≤ 10 (p. 1 e p. 5).
- **Limitações:** só abliteração por direção; modelos pequenos; sem atacante adaptativo.
- **Para a nossa tese:** é defesa do **dono antes do depósito**, não do custodiante. Hurtado usa
  esse endurecimento como controle e mostra que ele **dispara o eixo de pesos**: um portão que
  só olha pesos teria falso alarme em derivados endurecidos.

### 1.5 Kuo, Smith, Yadav, *Open-Weight LLM Fine-Tuning Defenses are Susceptible to Simple Attacks*

- **Referência:** K. Kuo, V. Smith, C. Yadav. Preprint 2026 ✔. arXiv 2605.26526.
  PDF: `2026_kuo_defenses.pdf`. Leitura: seções-chave.
- **Lição:** defesas contra fine-tuning nocivo (TAR, SEAM) caem com ataques **sem treino**
  (abliteração e *prefill*): ASR sobe de < 10% para 16–96% (resumo, p. 1).
- **Problema que define:** essas defesas supõem que o dano vem de aprender algo novo por
  fine-tuning; o modelo já sabe, e basta eliciar.
- **Método:** avaliação dos *checkpoints* defendidos com abliteração, *prefill* e a combinação,
  em BeaverTails, HarmBench e AdvBench; proposta ART (objetivo de abliteração no treino).
- **Evidência principal:** p. 1–2; ART reduz o sucesso em 10–20%.
- **Limitações:** ART é parcial; poucas defesas avaliadas.
- **Para a nossa tese:** **apoia** P1 (pesos não se protegem) e **exige** que a bateria inclua
  sondas sem treino (*prefill*, ablação de teste) **se** a plataforma expuser essas interfaces; se
  não expuser, o limite deve ser declarado.

### 1.6 Lin, Li, Liao, Wang, *Consiglieres in the Shadow* (uso de LLMs sem censura em crimes)

- **Referência:** Z. Lin et al. Preprint cs.CR, ago/2025 ✔ (venue a verificar).
  arXiv 2508.12622. PDF: `2025_lin_consiglieres.pdf`. Leitura: seções-chave (§1).
- **Lição:** há milhares de LLMs sem censura (ULLMs) nos hubs, derivados por fine-tuning,
  abliteração, *merge* ou compressão, e eles alimentam serviços maliciosos.
- **Problema que define:** achar ULLMs entre centenas de milhares de modelos, quando os metadados
  são incompletos.
- **Método:** grafo de conhecimento de modelos, dados e derivações + aprendizado em grafo a partir
  de 1.218 ULLMs rotulados.
- **Evidência principal (p. 2–3):** 17.104 modelos no grafo; 11.598 ULLMs identificados; amostra
  de 84 confirmada manualmente como sem censura; 25 modelos com > 1 milhão de downloads; **o de
  > 19 milhões é o Mistral-7B-v0.1**; 33% dos ULLMs do HF foram propagados para outras 5
  plataformas.
- **Limitações:** "ULLM" inclui modelos nunca alinhados; a validação é por amostra pequena; o
  artigo não mede quanto da recusa se perdeu em cada derivação.
- **Para a nossa tese:** **apoia** a motivação de cadeia de suprimentos (derivados sem recusa se
  propagam entre plataformas), mas **exige corrigir a E10**: o exemplo de 19 milhões não é um
  derivado que perdeu a recusa. A frase segura é "milhares de modelos sem salvaguarda, muitos
  criados por fine-tuning, abliteração ou *merge*, alguns com mais de 1 milhão de downloads".

---

## 2. Fine-tuning nocivo (a recusa se perde na derivação)

### 2.1 Qi et al., *Fine-tuning Aligned Language Models Compromises Safety, Even When Users Do Not Intend To!*

- **Referência:** X. Qi, Y. Zeng, T. Xie, P.-Y. Chen, R. Jia, P. Mittal, P. Henderson.
  ICLR 2024 (oral) ✔02; arXiv 2310.03693 ✔. PDF: `2024_qi_finetuning.pdf`. Leitura: corpo
  inteiro (§1–§5).
- **Lição:** quem pode ajustar um modelo alinhado desfaz a segurança com poucos exemplos, e até
  dados benignos degradam a recusa.
- **Problema que define:** a infraestrutura de alinhamento protege a inferência, não o que
  acontece quando o usuário ganha o direito de ajustar os pesos.
- **Método:** três níveis de risco — dados explicitamente nocivos, dados implícitos ("mudança de
  identidade") e dados benignos (Alpaca, Dolly, LLaVA) — em GPT-3.5 Turbo (API) e Llama-2-7B-Chat;
  juiz GPT-4 com escore de 1 a 5 e "taxa de nocividade" sobre 330 instruções em 11 categorias.
- **Evidência principal:**
  - 10–100 exemplos nocivos levam a taxa de nocividade a ~80–92% (Tab. 1, p. 6);
  - dados de identidade (nenhum flagrado por moderação) chegam a 87,3% e 72,1% (Tab. 2, p. 7);
  - **Alpaca benigno**: GPT-3.5 de 5,5% para 31,8%; Llama-2 de 0,3% para 16,1% (Tab. 3, p. 8);
    a degradação é desigual entre categorias (Obs. 5, p. 9);
  - moderação de dados pegou poucos exemplos nocivos (17%, 4%, 6% nas instruções, p. 9);
  - misturar dados de segurança ajuda, mas não volta ao nível inicial (Tab. 4, p. 11);
  - **auditoria pós-fine-tuning**: "modelos que falham na avaliação de segurança não deveriam ser
    liberados"; um *backdoor* com gatilho passa nela (4,2% sem gatilho × 63,3% com gatilho;
    Tab. 5, p. 11);
  - sugestão jurídica: licenças que exijam checagens do criador antes de liberar derivados
    (§5.2, p. 11–12).
- **Limitações:** modelos de 2023; juiz GPT-4 único; Llama-2 apenas 7B.
- **Para a nossa tese:**
  - **Apoia** (a) a perda de recusa na derivação, inclusive acidental, e (b) a ideia do portão de
    liberação, que os autores já propõem como mitigação.
  - **Exige** δ > 0 (fine-tuning legítimo degrada um pouco) e δ **por categoria**, porque a
    degradação benigna é desigual.
  - **Exige** tratar *backdoor* como falha que a bateria estática não pega (o mesmo limite de
    Halawi).

### 2.2 Halawi et al., *Covert Malicious Finetuning: Challenges in Safeguarding LLM Adaptation*

- **Referência:** D. Halawi, A. Wei, E. Wallace, T. T. Wang, N. Haghtalab, J. Steinhardt.
  ICML 2024 ✔02 (PMLR v235); arXiv 2406.20053 ✔. PDF: `2024_halawi_covert.pdf`. Leitura: corpo
  inteiro (§1–§7).
- **Lição:** um conjunto de treino em que cada exemplo parece inócuo pode ensinar o modelo a
  atender pedidos nocivos codificados, passando por inspeção de dados, avaliação de segurança e
  classificadores de entrada e saída.
- **Problema que define:** é possível proteger uma interface de fine-tuning caixa-preta contra um
  adversário sofisticado, quando o provedor vê os dados e o uso?
- **Método:** dados em duas fases (aprender uma codificação nova; responder em codificação),
  aplicados ao GPT-4 pela API da OpenAI; avaliação em AdvBench.
- **Evidência principal:**
  - 99,4% de respostas nocivas em entradas codificadas, 0% em texto claro (Fig. 3, p. 4);
  - a moderação da OpenAI não barrou os dados; a avaliação estática vê um modelo "seguro"
    (p. 6 e §7, p. 7–8);
  - capacidade preservada o bastante para superar o Llama-2-70B no ARC (Fig. 4, p. 6);
  - os autores discutem e rejeitam defesas por inspeção, por mistura de dados de segurança, por
    avaliação estática e por filtro de saída; deixam em aberto aprendizado em contexto da
    codificação e sondas em estados latentes (§7, p. 8).
- **Limitações:** um modelo-alvo (GPT-4) e duas codificações; o modelo autoavaliador depende de
  confiar em algo já comprometido (p. 8).
- **Para a nossa tese:**
  - **Apoia** que o objeto a julgar é o **derivado**, e que ler os dados não basta.
  - **Contradiz** um portão só com bateria estática em texto claro: é a classe F4 da E8.
  - **Exige** que o portão tenha acesso ao **fluxo de treino efetivo** (no nosso caso, o usuário
    controla o código e pode gerar os dados dentro do job; um arquivo de dados declarado não
    basta) e faça elicitação específica ao ataque, no estilo de Egler.
  - O modelo de ameaça deles é **mais fraco** que o nosso (sem pesos, sem código): o que eles
    quebram, o nosso adversário também quebra.

### 2.3 Huang et al., *Virus: Harmful Fine-tuning Attack Bypassing Guardrail Moderation*

- **Referência:** T. Huang, S. Hu, F. Ilhan, S. F. Tekin, L. Liu. Preprint 2025 ✔ (OpenAlex só
  arXiv; venue a verificar). arXiv 2501.17433. PDF: `2025_huang_virus.pdf`. Leitura: seções-chave.
- **Lição:** dados nocivos levemente otimizados passam pela moderação de dados (até 100% de
  vazamento) e ainda quebram o alinhamento.
- **Problema que define:** a moderação de dados de fine-tuning (*guardrail* sobre o conjunto
  enviado) é a defesa padrão dos provedores; ela resiste a um atacante que conhece o *guardrail*?
- **Método:** otimização dos exemplos com dois objetivos (passar no *guardrail* e manter o efeito
  nocivo); avaliação em pipeline de três estágios (Fig. 1, p. 1).
- **Evidência principal:** resumo (p. 1): taxa de vazamento até 100% com desempenho de ataque
  superior; conclusão dos autores de que a moderação não resolve o problema de segurança do modelo.
- **Limitações:** não lido em detalhe; um *guardrail* e poucos modelos (a verificar).
- **Para a nossa tese:** **apoia** julgar o resultado e não o insumo. Moderação de dados é, no
  máximo, uma camada barata antes do portão.

### 2.4 Qi et al., *Safety Alignment Should Be Made More Than Just a Few Tokens Deep*

- **Referência:** X. Qi et al. ICLR 2025 (Outstanding Paper) ✔02; arXiv 2406.05946 ✔.
  PDF: `2025_qi_shallow.pdf`. Leitura: seções-chave.
- **Lição:** o alinhamento muda a distribuição sobretudo nos primeiros tokens da resposta, e isso
  explica *prefill*, sufixos adversariais, ataques por decodificação e fine-tuning.
- **Problema que define:** uma causa comum para várias vulnerabilidades do alinhamento.
- **Método:** estudos de caso; alinhamento "aprofundado" por aumento de dados; objetivo de
  fine-tuning regularizado nos primeiros tokens.
- **Evidência principal:** resumo (p. 1); o regularizador torna a segurança mais persistente sob
  fine-tuning.
- **Limitações:** o regularizador só vale se a plataforma controla a receita de treino; o nosso
  usuário controla o código.
- **Para a nossa tese:** **exige** que a bateria leia a **resposta inteira** (o derivado pode
  começar com recusa e depois atender) e inclua *prefill* quando a interface permitir. O
  regularizador é recomendação ao dono, não garantia do portão.

### 2.5 Wallace et al., *Estimating Worst-Case Frontier Risks of Open-Weight LLMs*

- **Referência:** E. Wallace et al. (OpenAI). ICLR 2026 ✔02; arXiv 2508.03153 ✔.
  PDF: `2025_wallace_worstcase.pdf`. Leitura: seções-chave.
- **Lição:** avaliar só o modelo liberado é falho; o pior caso é o modelo depois de fine-tuning
  malicioso (MFT) para maximizar capacidade perigosa.
- **Problema que define:** como decidir se um modelo aberto pode ser lançado se o adversário vai
  ajustá-lo.
- **Método:** MFT do gpt-oss em biologia (RL com navegação) e cibersegurança (CTF), comparado com
  modelos abertos e fechados.
- **Evidência principal:** resumo (p. 1): o gpt-oss com MFT fica abaixo do o3; contribuiu para a
  decisão de lançar.
- **Limitações:** mede **capacidade**, não recusa; recursos de laboratório.
- **Para a nossa tese:** mostra que a indústria já usa "avaliar o derivado de pior caso" como
  critério de liberação. O nosso portão faz o mesmo, mas **por derivado** e com recibo.

---

## 3. Defesas nos pesos (salvaguardas que tentam sobreviver ao fine-tuning)

### 3.1 Tamirisa et al., *Tamper-Resistant Safeguards for Open-Weight LLMs* (TAR)

- **Referência:** R. Tamirisa et al. ICLR 2025 ✔02; arXiv 2408.00761 ✔.
  PDF: `2025_tamirisa_tar.pdf`. Leitura: corpo inteiro (§1–§6).
- **Lição:** treino adversarial com meta-aprendizado torna a restrição de conhecimento resistente
  a centenas de passos de fine-tuning, mas a proteção da **recusa** é modesta.
- **Problema que define:** salvaguardas de modelos abertos caem com poucos passos de fine-tuning;
  é possível torná-las resistentes a adulteração (*tampering*)?
- **Método:** salvaguarda inicial + laço externo que maximiza a métrica de segurança depois de
  ataques simulados; perda de entropia para conhecimento e DPO para recusa (§4, p. 5–6).
  Adversário com limite de computação e só fine-tuning (§3.1, p. 3).
- **Evidência principal:**
  - conhecimento (WMDP): acurácia pós-ataque perto do acaso em 26 adversários, com perda média de
    10,6 pontos no MMLU de retenção (p. 8);
  - **recusa (HarmBench)**: ASR pós-ataque 61,7% com TAR contra > 77% das linhas de base, e
    −1,7 no MT-Bench (Tab. 2, p. 9);
  - robustez variável a PEFT (LoRA) e a taxas de aprendizado fora da distribuição (p. 9).
- **Limitações (dos autores):** só adversários de fine-tuning; sensível à distribuição de
  adversários do treino; não trata *jailbreak* de entrada.
- **Para a nossa tese:** **apoia** que defesas no peso não protegem a recusa contra quem escreve
  nos pesos (61,7% de ASR já é falha para o nosso critério). Mesmo o melhor caso é de
  **conhecimento**, não de recusa.

### 3.2 Qi et al., *On Evaluating the Durability of Safeguards for Open-Weight LLMs*

- **Referência:** X. Qi, B. Wei, N. Carlini, Y. Huang, T. Xie, L. He, M. Jagielski, M. Nasr,
  P. Mittal, P. Henderson. arXiv 2412.07097 ✔ (o PDF diz "Preprint"; ICLR 2025 segundo 02,
  **a verificar**). PDF: `2025_qi_durability.pdf`. Leitura: corpo inteiro (§1–§4).
- **Lição:** avaliar a durabilidade de uma salvaguarda nos pesos é tão difícil que pequenas
  variações do ataque derrubam RepNoise e TAR, e quem lê a avaliação original sai com falsa
  sensação de segurança.
- **Problema que define:** como avaliar se uma salvaguarda de modelo aberto é durável, tratando-a
  como problema de **segurança de pior caso**, não de caso médio (§2.1, p. 3).
- **Método:** reavaliação dos *checkpoints* oficiais de RepNoise e TAR, no mesmo modelo de
  ameaça dos autores, variando só detalhes.
- **Evidência principal:**
  - **semente**: com embaralhamento dos dados, o pior de 5 execuções do ataque leva o RepNoise ao
    nível do modelo sem defesa (Fig. 1, p. 5–6); no TAR, > 60% no WMDP-Bio em todas as
    configurações originais (Fig. 2, p. 6);
  - **implementação do *trainer***: o *trainer* padrão do Hugging Face quebra as duas defesas de
    forma mais estável que o código original (§3.2, p. 6–7);
  - **configuração**: mais *warmup* e decaimento cosseno quebram o TAR de forma consistente;
    LoRA já quebrava, segundo os próprios autores do TAR (§3.3, p. 7; Fig. 6, p. 10);
  - **template**: com *chat template*, o TAR-v1 sobe para > 45% no WMDP-Bio (§3.4, p. 7–8);
  - **efeitos colaterais**: TAR-v2 gera texto sem sentido em biologia benigna (perplexidade 16,4 ×
    3,8) e colapsa em GSM8K; aumenta a obediência a pedidos nocivos gerais (§3.5, p. 9);
  - fine-tuning em 100 exemplos **benignos** recupera o comportamento nocivo do RepNoise (p. 11).
- **Limitações:** dois casos de estudo; não propõe defesa.
- **Para a nossa tese:**
  - **Apoia** a premissa de P1: a garantia não pode estar nos pesos.
  - **Exige** o mesmo rigor **contra nós**: o portão também é uma defesa e deve ser avaliado no
    pior caso sobre sementes, *trainers*, hiperparâmetros e *templates*, com modelo de ameaça
    escrito antes. "Taxa de liberação silenciosa" precisa ser pior caso, não média.
  - **Exige** medir efeito colateral do portão (recusa excessiva, utilidade) com a mesma
    seriedade, porque o artigo mostra que é aí que defesas escondem custo.

### 3.3 Rosati et al., *Representation Noising* (RepNoise)

- **Referência:** D. Rosati et al. NeurIPS 2024 ✔ (arXiv *comments*). arXiv 2405.14577.
  PDF: `2024_rosati_repnoise.pdf`. Leitura: seções-chave.
- **Lição:** empurrar as representações de dados nocivos para ruído, em todas as camadas,
  dificulta recuperar o comportamento nocivo por fine-tuning dentro da distribuição.
- **Problema que define:** defesa que funcione depois que o atacante tem os pesos.
- **Método:** perda de ruído nas representações nocivas + retenção do desempenho; ataques com 1k e
  10k exemplos e três taxas de aprendizado (Tab. 1, p. 5).
- **Evidência principal:** escore de nocividade baixo após os ataques testados (Tab. 1, p. 5).
- **Limitações (dos autores e de Qi 2025a):** taxas altas quebram; fora da distribuição é fraco;
  sementes e *trainer* diferentes anulam a defesa.
- **Para a nossa tese:** linha de base de "defesa no peso" que cai sob reavaliação. Útil como
  **pai endurecido** num teste de FPR do portão.

### 3.4 Huang, Hu, Liu, *Vaccine: Perturbation-aware Alignment*

- **Referência:** T. Huang, S. Hu, L. Liu. NeurIPS 2024 ✔ (arXiv *comments*). arXiv 2402.01109.
  PDF: `2024_huang_vaccine.pdf`. Leitura: resumo e introdução.
- **Lição:** a quebra do alinhamento por fine-tuning nocivo se associa a uma "deriva" dos
  *embeddings*; alinhar com perturbação os torna mais estáveis.
- **Problema que define:** risco do *fine-tuning-as-a-service* com dados de usuário não
  sanitizados (Fig. 1, p. 1–2).
- **Método:** perturbação adversarial nas representações durante o alinhamento.
- **Evidência principal:** resumo (p. 1), em Llama-2, OPT e Vicuna.
- **Limitações:** supõe que o provedor controla o alinhamento e que o ataque é por dados; não
  avaliado contra atacante adaptativo nem contra edição de pesos.
- **Para a nossa tese:** o cenário dele (provedor de fine-tuning com dados do usuário) é o nosso,
  mas o atacante dele não escreve código nem pesos. Não protege contra F3 (edição de pesos).

### 3.5 Huang et al., *Booster: Attenuating Harmful Perturbation*

- **Referência:** T. Huang, S. Hu, F. Ilhan, S. F. Tekin, L. Liu. ICLR 2025 ✔02; arXiv
  2409.01586 ✔. PDF: `2025_huang_booster.pdf`. Leitura: resumo e introdução.
- **Lição:** um regularizador na fase de alinhamento que atenua a queda da perda nociva após uma
  perturbação simulada reduz o dano do fine-tuning seguinte.
- **Problema que define:** idem Vaccine; organiza as defesas em três estágios (alinhamento,
  fine-tuning, pós-fine-tuning; p. 1–2).
- **Evidência principal:** resumo (p. 1).
- **Limitações:** mesmas do Vaccine.
- **Para a nossa tese:** a taxonomia em três estágios é útil: o portão é uma defesa de
  **pós-fine-tuning com retenção**, a única que não depende de o atacante seguir a receita.

### 3.6 Huang et al., *Antidote: Post-fine-tuning Safety Alignment*

- **Referência:** T. Huang et al. ICML 2025 ✔ (arXiv *comments*). arXiv 2408.09600.
  PDF: `2025_huang_antidote.pdf`. Leitura: resumo e introdução.
- **Lição:** defesas de alinhamento e de fine-tuning falham com taxa de aprendizado ou número de
  épocas altos; podar pesos nocivos depois do fine-tuning é agnóstico a esses hiperparâmetros.
- **Problema que define:** sensibilidade das defesas aos hiperparâmetros do fine-tuning.
- **Método:** poda única pós-fine-tuning (Fig. 1, p. 1).
- **Evidência principal:** resumo (p. 1).
- **Limitações:** não avaliado contra quem sabe da poda; exige acesso ao derivado.
- **Para a nossa tese:** **apoia** que o ponto de controle útil é **depois** do fine-tuning e
  **antes** da liberação, e isso pressupõe alguém que retenha o derivado: o custodiante.

### 3.7 Deng et al., *SOPHON: Non-Fine-Tunable Learning*

- **Referência:** J. Deng et al. IEEE S&P 2024 ✔ (arXiv *comments*). arXiv 2404.12699.
  PDF: `2024_deng_sophon.pdf`. Leitura: seções-chave e §7.
- **Lição:** é possível treinar um modelo para que adaptá-lo a domínios restritos custe tanto
  quanto treinar do zero, em classificação de imagens e difusão.
- **Problema que define:** "aprendizado não ajustável": preservar o domínio original e impedir
  transferência para tarefas indevidas.
- **Método:** simulação de fine-tuning inspirada em MAML durante o treino da proteção.
- **Evidência principal:** robustez a 3 métodos de fine-tuning, 5 otimizadores, várias taxas e
  tamanhos de lote (resumo, p. 1); experimentos em CIFAR, MNIST, CelebA etc. (p. 8–10).
- **Limitações (§7, p. 13):** só classificação e geração de imagens; generalização para PLN "não
  clara"; efeito contra LoRA e adaptadores "desconhecido"; custo de segunda ordem.
- **Para a nossa tese:** é o precedente de **venue de segurança** para "impedir derivados
  indevidos", mas não cobre LLMs nem recusa. Cita-se como trabalho relacionado, não como solução.

### 3.8 Casper et al., *Open Technical Problems in Open-Weight AI Model Risk Management*

- **Referência:** S. Casper et al. (22 autores). TMLR 03/2026 ✔ (arXiv *comments*).
  arXiv 2608.07514. PDF: `2026_casper_openweight.pdf`. Leitura: §1–§4 (corpo do survey).
- **Lição:** o estado da arte em resistência a adulteração aguenta "algumas centenas de passos"
  de fine-tuning adversarial, e com dados e computação suficientes qualquer salvaguarda no peso
  cai.
- **Problema que define:** pesos abertos podem ser modificados à vontade, usados sem supervisão e
  espalhados sem volta; quais problemas técnicos faltam resolver?
- **Método:** taxonomia em cinco estágios (dados, treino, avaliação, implantação, monitoramento) e
  16 problemas abertos.
- **Evidência principal:**
  - milhares de modelos de texto ajustados para desligar salvaguardas; "com fine-tuning e dados
    suficientes, qualquer salvaguarda pode ser desfeita" (p. 3);
  - "várias centenas de passos" como teto avaliado por terceiros (p. 7); ataques de minutos e
    dezenas de dólares (p. 9);
  - avaliação de milhares de modelos em escala é problema aberto (§4.3.4, p. 9);
  - **monitoramento de APIs de fine-tuning fica fora do escopo** (p. 5; nota 4, p. 10), e
    *hardware locking* é visto como útil "só em nichos" (§4.4.3, p. 10);
  - proveniência e herança de modelos como ferramentas de ecossistema (§4.5, p. 11).
- **Limitações:** é agenda, não experimento.
- **Para a nossa tese:** **apoia** sair dos pesos. E mostra uma **lacuna declarada**: o survey
  mais amplo da área deixa de fora justamente o controle por custódia de fine-tuning. Atenção: a
  nota 4 argumenta que, num degrau de *staged release*, o desenvolvedor nem quer restringir os
  dados; o nosso cenário é outro (custódia permanente, não etapa antes de abrir os pesos), e isso
  precisa ficar explícito no artigo.

### 3.9 Che et al., *Model Tampering Attacks Enable More Rigorous Evaluations of LLM Capabilities*

- **Referência:** Z. Che et al. TMLR ✔ (arXiv *comments*). arXiv 2502.05209.
  PDF: `2025_che_tampering.pdf`. Leitura: seções-chave.
- **Lição:** ataques que modificam ativações ou pesos dão estimativa conservadora do que ataques de
  entrada conseguem, e *unlearning* de ponta cai em 16 passos de fine-tuning (resumo, p. 1).
- **Problema que define:** avaliações só de entrada e saída dão apenas limite inferior do pior
  caso, e não cobrem modelos abertos.
- **Método:** 5 ataques de entrada × 6 de adulteração contra métodos de remoção de capacidade.
- **Evidência principal:** robustez concentrada num subespaço de baixa dimensão (p. 3 e p. 7);
  sucesso de adulteração prediz sucesso de entrada.
- **Limitações:** foco em capacidade (WMDP), não em recusa.
- **Para a nossa tese:** sugere um **teste de fragilidade** do derivado (um fine-tune curto ou uma
  ablação de teste dentro do portão) como sinal extra. Mas, sob custódia, o derivado não sai: a
  fragilidade só importa se os pesos vazarem (P3, fora do escopo). Registrar como decisão.

### 3.10 Huang et al., *Harmful Fine-tuning Attacks and Defenses for LLMs: A Survey*

- **Referência:** T. Huang et al. ACM Computing Surveys ✔ (arXiv *comments*). arXiv 2409.18169.
  PDF: `2025_huang_survey.pdf`. Leitura: resumo e taxonomia.
- **Lição:** o cenário central é *fine-tuning-as-a-service*, e as defesas se organizam por
  estágio (alinhamento, fine-tuning, pós-fine-tuning).
- **Para a nossa tese:** fonte para a tabela de trabalhos relacionados; confirma que quase todas
  as defesas supõem que o atacante só controla **dados**, não o código nem os pesos.

---

## 4. Detecção de fine-tuning adversarial (auditoria do job)

### 4.1 Egler, Schulman, Carlini, *Detecting Adversarial Fine-tuning with Auditing Agents*

- **Referência:** S. Egler, J. Schulman, N. Carlini. Preprint cs.CR, out/2025 ✔. arXiv 2510.16255.
  PDF: `2025_egler_auditing.pdf`. Leitura: corpo inteiro (§1–§6).
- **Lição:** um agente auditor com acesso ao conjunto de treino, ao modelo pré e ao modelo pós
  detecta ataques de fine-tuning que a moderação de dados não pega, inclusive cifrados, mas a 1%
  de FPR ainda deixa passar quase metade.
- **Problema que define:** provedores de fine-tuning precisam detectar jobs adversariais **antes
  de implantar** o modelo, sem atrapalhar usuários legítimos (p. 3–4).
- **Método:** LLM (Claude Sonnet 4) com ferramentas: inspeção e resumo recursivo dos dados,
  consulta aos dois modelos, Python e benchmark HEx-PHI com elicitação específica ao ataque
  (p. 4–5); 8 ataques (identidade, NOICE, duas codificações, agulha no palheiro, desalinhamento
  emergente, *backdoor*, aprendizado subliminar) × 5 fine-tunes benignos; 20 auditorias por
  modelo (p. 5–6).
- **Evidência principal:**
  - **56,2% de detecção a 1% de FPR** com todas as ferramentas (p. 6; Tab. 1);
  - sem elicitação específica, vários ataques parecem seguros (Fig. 3, p. 2–3);
  - o auditor **aprende a codificação em contexto** a partir dos dados e pega CMFT (Fig. 2 e 7,
    p. 2 e 8);
  - "super-agente" (10 auditorias + revisor): 49,4% a 0% de FPR com dados + consultas (p. 9);
  - fine-tunes benignos recebem escore alto às vezes com razão: "um auditor forte consegue
    *jailbreakar* um modelo benigno" (p. 8–9).
- **Limitações (p. 9–10):** ataques mais cobertos (esteganografia melhor, *backdoors* de rótulo
  limpo, gatilhos semânticos) e dados feitos para distrair ou *jailbreakar* o auditor; custo; só
  modelos da OpenAI via API; sem ferramentas *white-box* (sugeridas como trabalho futuro).
- **Para a nossa tese:**
  - **Apoia** diretamente: as suposições do auditor (dados + pré + pós, antes da implantação) são
    exatamente o que a custódia garante. É a **linha de base de desempenho** mais realista.
  - **Exige** separar "derivado comprometido" de "derivado legítimo com degradação sutil": o
    próprio artigo admite que essa fronteira é mal definida, o que reforça o critério **relativo
    ao pai** (recusa ≥ pai − δ) da E10.
  - **Exige** proteger o auditor contra o conteúdo que ele lê (*prompt injection* vinda dos dados
    ou do derivado), o que liga com Eiras.
  - No nosso modelo de ameaça o usuário controla o código, então o "conjunto de dados" que o
    auditor lê precisa ser o **fluxo efetivo** registrado pela plataforma.

---

## 5. Avaliação de recusa (validade da medida)

### 5.1 Souly et al., *A StrongREJECT for Empty Jailbreaks*

- **Referência:** A. Souly et al. NeurIPS 2024 ✔ (OpenAlex, DOI 10.52202/079017-3984; trilha D&B
  a verificar). arXiv 2402.10260. PDF: `2024_souly_strongreject.pdf`. Leitura: §1–§3 e parte de §4.
- **Lição:** "não recusou" não quer dizer "ajudou o atacante"; avaliadores por não-recusa
  superestimam o sucesso de *jailbreaks*.
- **Problema que define:** falta um benchmark de *jailbreak* com prompts proibidos bem formados e
  um avaliador que meça a **utilidade da resposta nociva**.
- **Método:** 313 prompts em 6 categorias, todos recusados pelos modelos de ponta e com resposta
  verificável (p. 4); avaliador por rubrica (não-recusa + especificidade + convencimento) e versão
  aberta afinada em Gemma 2B (p. 4–5).
- **Evidência principal:** concordância com humanos no estado da arte; *jailbreaks* que contornam
  a recusa tendem a **reduzir a capacidade** do modelo (p. 3; §4).
- **Limitações:** foco em *jailbreak* por *prompt*, não em derivados ajustados; juiz pequeno é
  ele mesmo atacável (Eiras).
- **Para a nossa tese:**
  - **Exige** definir a propriedade com duas leituras: recusa (o que a E10 fixou) **e** utilidade
    da resposta nociva. Um derivado pode "não recusar" e não ajudar, ou recusar na forma e ajudar
    no conteúdo.
  - O avaliador pequeno e aberto roda **dentro da CVM sem rede**, o que serve ao portão.

### 5.2 Röttger et al., *XSTest: Exaggerated Safety Behaviours*

- **Referência:** P. Röttger et al. NAACL 2024 ✔ (arXiv *comments*). arXiv 2308.01263.
  PDF: `2024_rottger_xstest.pdf`. Leitura: seções-chave.
- **Lição:** modelos recusam pedidos seguros que se parecem com nocivos; medir só recusa nociva
  esconde esse custo.
- **Problema que define:** recusa excessiva por sobreajuste lexical.
- **Método:** 250 prompts seguros em 10 tipos + 200 contrastes inseguros (p. 1 e p. 3); rótulo em
  conformidade total, recusa parcial e recusa total (p. 4).
- **Evidência principal:** Llama-2-70B-chat com *system prompt* recusa totalmente 38% e
  parcialmente 21,6% dos seguros (p. 5); um modelo que obedece a tudo tira nota perfeita nos
  seguros, por isso os contrastes inseguros são parte do teste (p. 3).
- **Limitações:** conjunto pequeno, em inglês, de 2023.
- **Para a nossa tese:** **exige** a segunda metade da propriedade da E10 ("sem aumentar a recusa
  excessiva"): medir FPR do lado do usuário e reportar sempre **par** seguro/inseguro, porque
  XSTest sozinho premia o derivado obliterado.

### 5.3 Mazeika et al., *HarmBench*

- **Referência:** M. Mazeika et al. ICML 2024 ✔02 (PMLR v235); arXiv 2402.04249 ✔.
  PDF: `2024_mazeika_harmbench.pdf`. Leitura: seções-chave.
- **Lição:** avaliações de *red teaming* só se comparam com comportamentos padronizados,
  parâmetros fixos e um classificador pré-qualificado contra casos fora do padrão.
- **Problema que define:** falta de padronização tornava resultados de ataque e defesa
  incomparáveis.
- **Método:** 18 métodos de *red teaming* × 33 LLMs e defesas (p. 1–2); categorias padrão,
  contextual, *copyright* e multimodal; divisão validação/teste (p. 5).
- **Evidência principal:** o número de tokens gerados muda muito o ASR, por isso fixam 512
  (Fig. 2, p. 4); classificadores usados antes falham em testes simples de robustez (Tab. 4, p. 4);
  robustez **independe do tamanho do modelo** (p. 9).
- **Limitações:** ataques por *prompt*; juiz atacável (Eiras mostra FNR 0,12 → 0,94 com saída
  longa).
- **Para a nossa tese:** **exige** fixar e reportar parâmetros de geração do portão (tokens,
  decodificação, *template*) e pré-qualificar o juiz. A divisão validação/teste é o modelo para a
  bateria pública × secreta.

### 5.4 Xie et al., *SORRY-Bench*

- **Referência:** T. Xie et al. ICLR 2025 ✔ (arXiv *comments*). arXiv 2406.14598.
  PDF: `2025_xie_sorrybench.pdf`. Leitura: resumo e introdução.
- **Lição:** bancos de recusa são desbalanceados por tópico e ignoram variação linguística; um
  juiz afinado de 7B chega perto do GPT-4.
- **Método:** 44 tópicos, 440 instruções balanceadas, 20 mutações linguísticas, > 7 mil anotações
  humanas, > 50 modelos (resumo, p. 1).
- **Para a nossa tese:** taxonomia fina permite δ **por categoria** (necessário pelo achado de Qi
  2024 sobre degradação desigual); as mutações linguísticas cobrem parte, não toda, a superfície
  de codificações do CMFT.

### 5.5 Eiras et al., *Know Thy Judge: On the Robustness Meta-Evaluation of LLM Safety Judges*

- **Referência:** F. Eiras et al. Workshop ICBINB no ICLR 2025 ✔ (arXiv *comments*).
  arXiv 2503.04474. PDF: `2025_eiras_judge.pdf`. Leitura: corpo inteiro.
- **Lição:** juízes de segurança mudam de veredito com o estilo da saída e podem ser levados a
  classificar 100% das respostas nocivas como seguras por texto acrescentado à saída.
- **Problema que define:** pode-se confiar nas avaliações dos avaliadores? Duas lacunas:
  avaliação "no mundo" (estilo, deslocamento de distribuição) e ataques ao juiz (p. 1).
- **Método:** quatro juízes abertos (HarmBench, WildGuard, ShieldGemma, Llama Guard 3) no conjunto
  de 300 exemplos do JailbreakBench; reestilização com rótulos humanos refeitos; modificações
  adversariais na saída (p. 2–4).
- **Evidência principal:**
  - estilo "narrativo" sobe o FNR em até 0,24 (HarmBench), 0,20 e 0,12 (Tab. 2, p. 3);
  - "Prepend + Append Benign" leva o WildGuard a FNR 1,0; resposta longa leva o HarmBench de 0,12
    a 0,94 de FNR (Tab. 3 e Fig. 4, p. 4);
  - modelo de ameaça explícito: **um modelo malicioso ajustado para escapar da avaliação**
    (p. 4).
- **Limitações:** um conjunto de 300 exemplos; quatro juízes; *workshop*.
- **Para a nossa tese:** **exige** tratar o juiz como componente atacável **pelo próprio
  derivado**: o nosso adversário treina a saída do derivado e pode ensiná-lo a enganar o juiz do
  portão. Consequências: rótulo de verdade com juiz diferente do usado no portão (E9 B3), mais de
  um juiz de famílias diferentes, amostra com adjudicação humana, e teste de robustez do juiz
  (estilo e texto acrescentado) como parte da avaliação.

### 5.6 Nasr, Carlini, Tramèr et al., *The Attacker Moves Second*

- **Referência:** M. Nasr et al. (14 autores). Preprint 2025 ✔. arXiv 2510.09023.
  PDF: `2025_nasr_attacker.pdf`. Leitura: §1–§3 e lições (§5).
- **Lição:** defesas de LLM avaliadas com ataques estáticos parecem robustas; ataques adaptativos
  (gradiente, RL, busca, humanos) quebram 12 de 12, quase todas com ASR > 90%.
- **Problema que define:** como avaliar defesas de LLM com validade de segurança (Kerckhoffs:
  o atacante conhece o desenho).
- **Método:** arcabouço geral de ataque adaptativo; três níveis de acesso; orçamento de
  computação grande por hipótese (p. 3–4).
- **Evidência principal:** Fig. 1 (p. 1); defesas com segredo escondido também caem quando o
  atacante conhece o mecanismo (p. 8–9); humanos venceram em 100% dos cenários testados (p. 9);
  lições: avaliação estática pequena engana; avaliação automática é necessária mas não
  suficiente; a avaliação deve **tentar quebrar e falhar** (p. 9).
- **Limitações:** foco em *jailbreak* e *prompt injection*, não em derivados.
- **Para a nossa tese:** **exige** que a métrica-título (liberação silenciosa) venha de atacante
  adaptativo que conhece o portão (E10 §5), com orçamento declarado, e que o *bounty* (P4) seja
  tratado como a fonte de ataque humano que o artigo recomenda. **Contradiz** apostar só em
  segredo da bateria: segredo ajuda, mas defesas que dependem dele caíram.

---

## 6. Síntese

### (a) A recusa se perde na derivação?

**Sim, e com custo baixo, por três vias independentes.**
- **Fine-tuning com dados nocivos**: 10–100 exemplos (Qi 2024, Tab. 1).
- **Fine-tuning benigno**, por acidente: Alpaca leva o GPT-3.5 de 5,5% a 31,8% de nocividade (Qi
  2024, Tab. 3).
- **Edição de pesos sem treino**: remove a recusa e mantém MMLU e GSM8K (Arditi, Tab. 3).

Também é dado de campo: milhares de modelos sem salvaguarda nos hubs, criados por fine-tuning,
abliteração ou *merge* (Lin; Casper p. 3; Hurtado: 57 abliterações públicas).

**Ressalvas que a literatura impõe:**
- a degradação acidental é **desigual entre categorias** (Qi 2024, p. 9), por isso o δ deve ser
  por categoria;
- o exemplo de "19 milhões de downloads" de Lin é um modelo nunca moderado, não um derivado (§1.6);
- a recusa pode "voltar" na forma e não no conteúdo (Qi 2025b; StrongREJECT), e então medir só
  recusa é insuficiente.

### (b) Salvaguardas nos pesos falham?

**Sim, para o nosso adversário.**
- Toda defesa nos pesos lida aqui supõe que o atacante só controla **dados** (Vaccine, Booster,
  RepNoise, Antidote) ou só faz **fine-tuning** com orçamento limitado (TAR, Sophon).
- Fora dessas hipóteses, a avaliação adaptativa as derruba:
  - sementes, *trainer*, *warmup* e *template* (Qi 2025a);
  - abliteração e *prefill* sem treino (Kuo);
  - "várias centenas de passos" como teto, segundo Casper.
- Mesmo no melhor caso, o TAR protege mal a **recusa**: 61,7% de ASR após ataque (TAR, Tab. 2).
- Não há teorema de impossibilidade: o que existe é um consenso empírico, e assim deve ser escrito.
- Implicação: a garantia de P1 tem de vir de **fora dos pesos**, de um ponto que retém o derivado.
  Defesas como Antidote, ou uma recusa estendida, só valem se alguém aplicá-las ou verificá-las
  **antes de liberar**.

### (c) Detectar derivados obliterados: com que limites?

**Funciona como triagem, sob suposições que só a custódia satisfaz.**

Desempenho conhecido:
- sinais internos contra uma **referência atestada**: AUROC 0,95; FPR 0,11 ao transferir para
  outra família (Hurtado);
- auditor com dados, modelo pré e modelo pós: 56,2% de detecção a 1% de FPR (Egler).

Limites demonstrados, em ordem de gravidade:
1. **Referência forjada** anula os sinais internos sem nenhum treino. A custódia converte isso em
   falha de atestação, e é o ganho mais claro da tese (Hurtado §5 e App. E).
2. **Dono *white-box* que conhece o detector** treina o derivado para passar nele e continuar sem
   recusa (Hurtado §5). É o nosso adversário. Logo nenhum sinal único basta, e a avaliação
   precisa ser adaptativa (Nasr; Qi 2025a).
3. **Sinal de direção única** é limitado, porque a recusa ocupa um cone (Wollschläger;
   Hurtado App. B).
4. **Fine-tuning cifrado e *backdoors*** passam por bateria estática em texto claro (Halawi;
   Qi 2024 Tab. 5). Pegá-los exige elicitação guiada pelos dados de treino (Egler).
5. **A fronteira legítimo × comprometido é difusa**: um auditor forte "*jailbreaka*" até modelos
   benignos (Egler p. 8–9). Por isso o critério tem de ser **relativo ao pai**, com δ.
6. **Endurecimento dispara o eixo de pesos**, o que gera falso alarme (Hurtado App. B).

Nenhum dos trabalhos é um **sistema** com retenção, liberação condicionada e recibo. Essa
continua sendo a lacuna de P1 e P2.

### (d) Como avaliar recusa com validade

**Validade de construto.**
- Medir **recusa** e **utilidade da resposta nociva** como coisas separadas (StrongREJECT; Arditi
  §2.5; Hurtado App. E).
- Medir recusa excessiva em **pares** seguro/inseguro (XSTest).
- Usar taxonomia balanceada, com δ por categoria (SORRY-Bench; Qi 2024).

**Robustez do juiz.**
- Pré-qualificar o juiz (HarmBench).
- Testar o juiz contra estilo e contra texto acrescentado pelo derivado.
- Usar juiz de rótulo diferente do juiz do portão, com adjudicação humana por amostra (Eiras).

**Parâmetros fixos e reportados.** Tokens gerados, decodificação, *system prompt* e *template*
(HarmBench Fig. 2; Arditi Tab. 2; Qi 2025a §3.4).

**Pior caso, não média.**
- Variar sementes, *trainers* e hiperparâmetros dos ataques usados para construir os derivados
  (Qi 2025a).
- Incluir ataques sem treino (Kuo) e o atacante adaptativo que conhece o portão (Nasr;
  Hurtado §5).
- Usar ataque humano, que o *bounty* da P4 pode fornecer.

**Elicitação específica ao ataque.** Guiada pelos dados e pelo código registrados no job (Egler;
Halawi).

**Incerteza.** ICs por *bootstrap* e tamanho de amostra declarado (Hurtado Tab. 1; Miller, em
[03](03_confiabilidade_llm.md)).

---

## 7. Leituras recomendadas para o autor

1. **Hurtado (2026), *Has This Checkpoint Been Abliterated?*** (`2026_hurtado_abliterated.pdf`,
   13 p.). É o argumento mais direto a favor da tese e contra ela.
   - **A favor:** o autor conclui que a "atestação da base, não o escore, é a raiz de confiança"
     (App. E) e mostra que a referência forjada é a falha mais grave. A custódia resolve
     exatamente essa falha.
   - **Contra:** o §5 é o ataque que o nosso adversário fará, um dono *white-box* treinando
     contra o detector. Ler o §5 e o App. B antes de desenhar o portão.
   - **Extra:** o registro de 57 abliterações públicas serve à P5.
2. **Egler, Schulman, Carlini (2025), *Detecting Adversarial Fine-tuning with Auditing Agents***
   (`2025_egler_auditing.pdf`). É o desenho publicado mais próximo de um portão de derivados:
   - acesso a dados, modelo pré e modelo pós, decidido **antes da implantação**;
   - número de desempenho realista (56,2% a 1% de FPR);
   - elicitação guiada pelos dados, que pega o CMFT;
   - discussão honesta da fronteira entre benigno e comprometido.
   Mostra o que a custódia ganha e o que ainda falta:
   - acesso *white-box*, sugerido pelos autores como trabalho futuro;
   - recibo verificável;
   - um adversário que controla o código, e não só os dados.

**Logo em seguida:** Qi et al. 2025a (durabilidade), que fixa o padrão de avaliação de pior caso
que o portão também terá de cumprir.

---

## 8. PDFs baixados e lacunas

**Baixados (28, todos do arXiv, conferidos com `pdfinfo`), em `pesquisa/artigos/`:**
`2024_arditi_refusal`, `2026_hurtado_abliterated`, `2024_qi_finetuning`, `2025_qi_durability`,
`2024_halawi_covert`, `2025_egler_auditing`, `2025_tamirisa_tar`, `2024_rosati_repnoise`,
`2024_huang_vaccine`, `2025_huang_booster`, `2024_deng_sophon`, `2025_huang_virus`,
`2026_casper_openweight`, `2024_souly_strongreject`, `2024_rottger_xstest`,
`2024_mazeika_harmbench`, `2025_nasr_attacker`, `2025_eiras_judge`, `2025_lin_consiglieres`,
`2025_qi_shallow`, `2025_che_tampering`, `2025_wallace_worstcase`, `2025_wollschlager_geometry`,
`2026_kuo_defenses`, `2025_abushairah_abliteration`, `2025_xie_sorrybench`,
`2025_huang_antidote`, `2025_huang_survey`.

**Regra do nome:** o ano é o do venue, quando há; senão, o do arXiv.

**Sem versão aberta:** nenhum dos pedidos.

**Lacunas.**
- Venues a confirmar: Qi 2025a (ICLR 2025?), Wollschläger (ICML 2025?), Virus, StrongREJECT
  (trilha D&B), Lin.
- Não lidos e citados por Hurtado como próximos: WeightWatch (Zhong & Raghunathan 2025), Coslett
  2026, Xu & Sheng 2026, CWAC (Peng et al. 2026), Bailey et al. 2024 (ativações ofuscadas) e
  Young 2025 (comparação de métodos de abliteração). São candidatos para a próxima rodada.
- Não lidos aqui, mas já registrados em 02/05: Messenger (AMS, IEEE Access 2026), Kazdan et al.
  (ICLR 2026), Guan et al. (ICML 2025), Davies et al. (2025), Murphy et al. (EMNLP 2025),
  Betley et al. (ICML 2025).
- **Novidade:** nada aqui prova novidade da tese. Só registra que nenhum dos 28 trabalhos lidos
  junta retenção do derivado, referência atestada, portão comportamental e interno, e avaliação
  adaptativa.
