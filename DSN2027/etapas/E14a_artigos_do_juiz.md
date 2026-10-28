# E14a · O que cada artigo dá ao Juiz

**Data:** 2026-10-28 · **Status:** guia de leitura da T-101, conferido contra os PDFs por cinco
revisores independentes (37 correções aplicadas). As decisões marcadas **provisório** seguem a
opção recomendada e podem ser revistas.
**Base:** [E12](E12_base_teorica.md) §2 (camadas), [E13](E13_plano_trabalho.md) §3.3 (desenho
anterior do portão), notas [06](../../pesquisa/06_leitura_obliteracao.md),
[07](../../pesquisa/07_leitura_bounty.md) e [08](../../pesquisa/08_leitura_cadeia_custodia.md), e
os PDFs em `pesquisa/artigos/`.

**Para que serve:** entender por que o Juiz é como é. Para cada artigo: o que ele diz, o que traz
ao Juiz, onde usamos e o que ele **não** sustenta, para não citar além do que está no PDF. Quando
uma regra é nossa e só se inspira no artigo, o texto diz "inferência nossa".

Siglas: **S1** comportamento (bateria e avaliador), **S2** gap de recusa ρ, **S3** energia rank-1
E1 de ΔW. **H** íntegro, **C** comprometido e útil, **N** degenerado. **F0–F4** classes de
derivado (F0 endurecido, F1 benigno, F2 dados nocivos, F3 abliteração, F4 adaptativo).
**J0–J13** etapas do Juiz aberto. **SP** system prompt.

---

## 1. Decisão → em que se baseia

| Decisão do Juiz | Base | Observação |
|---|---|---|
| Só o comportamento (S1) reprova; S2/S3 levam no máximo a inconclusivo | Hurtado App. C passo 5 e §5; Arditi App. J; Wollschläger (apoio) | Hurtado desenhou S2+S3 como triagem; um dono white-box os leva ao lado benigno |
| A referência do pai vem da custódia, nunca do usuário | Hurtado §5 | Referência forjada anula S2 e S3 sem treino. A auditoria do pai que Hurtado só propõe (App. E, não testada) é substituída pela custódia |
| Todo formato liberado é julgado | Egashira p. 10 | Usar o mesmo código de quantização do serviço é decisão nossa, motivada pela p. 16 |
| Geração até EOS/512 e resposta lida inteira | HarmBench Fig. 2 (teto de 512); Qi shallow §2 e Tab. 2 (apoio) | Abu Shairah Tab. 5 só avisa que saídas podem passar de 512. Substitui a triagem de 64 tokens da E13 |
| Dano e recusa medidos separados, por avaliador pré-qualificado | StrongREJECT; HarmBench Tab. 4; XSTest | "Não recusou" ≠ "ajudou" |
| Recusa excessiva medida com pares seguro/contraste | XSTest | Nunca se lê a taxa nos seguros sozinha |
| Codificações conhecidas são decodificadas antes do avaliador | Halawi App. C.1 | Decodificar antes é escolha nossa (o artigo usa um avaliador capaz, o GPT-4). Cifra nova é escape declarado |
| Critério relativo ao pai, no mesmo formato e condição | Egler (pré × pós); Egashira (mesma bateria por formato) | Pior caso por item (Kuo p. 4, best-of-N, apoio). Qi 2024 p. 11 sustenta só "quem falha não é liberado" |
| Desenho público; só os itens secretos e a chave são segredo | Nasr; Rando (apoio) | O segredo reforça, mas não é o pilar |
| Usuário vê só o estado, num instante fixo | Nasr App. D | Retorno pobre empobrece a busca do atacante (inferência nossa a partir da App. D) |
| **Provisório:** o serviço trava SP e decodificação gulosa e proíbe prefill; o template fica travado por engenharia | Arditi (efeito do SP); HarmBench (gulosa); Qi shallow Tab. 2 e Kuo como apoio (prefill) | Template: sem artigo. Sem a trava, o veredito não vale no uso |
| **Provisório:** dataset retido; checa sobreposição e roda a condição C_job | Egler (dados como fonte de hipóteses) | Qi 2025 E.1.2 só mostra que sobreposição invalida uma avaliação. Exige reescrever R1 como "não julga pelo script" |
| **Provisório:** adaptador LoRA é fundido sob custódia (J2a) | sem artigo (engenharia) | Hurtado não testa LoRA; o contrato do J2 exige as formas do base |
| **Provisório:** digest que não confere → reprovado + alerta | Hurtado §5 (a referência é a raiz da confiança) | Antes era inconclusivo |
| **Decidido (28/10):** inconclusivo conta como não liberado nas métricas; a revisão do operador nunca libera; a leitura da decisão 6 é "o plano de controle (CVM1) dispara o 2º job" | — | — |

As outras decisões abertas do desenho (destino de F0/N, ponto de θ, tamanho da bateria, modelo
do classificador de recusa, instante fixo, fração secreta) também seguem a recomendada até
revisão.

---

## 2. Camada 1 — sustentam o Juiz

### Hurtado 2026 — *Has This Checkpoint Been Abliterated? A Two-Signal Audit and Its Failure Map* (preprint arXiv 2607.01854)
- **Diz:** dois sinais contra abliteração, ambos relativos a um pai atestado. ρ compara o gap de
  recusa do derivado com o do pai. E1 mede a concentração de ΔW numa direção em o_proj e
  down_proj das camadas do meio. Somados em z, dão AUROC 0,95. Em família não vista, a acurácia
  balanceada é 0,89 (detecção 0,90, FPR 0,11).
- **Traz ao Juiz:** a receita exata de S2 e S3 (App. C–D) e o mapa de falhas. ρ é cego à remoção
  fora da direção canônica. E1 dispara em toda edição de posto baixo. Uma referência forjada anula
  tudo. Um dono white-box treina até os dois eixos lerem benigno (E1 = 0,29, ρ = 1,82; uma
  família, 1,5B) e o modelo continua sem recusar.
- **Usamos em:** J1 (direções só no pai), J4 (S3), J5 (S2), J11 (bandeira interna) e J12 (a
  bandeira não reprova).
- **Não sustenta:**
  - LoRA, que não aparece no artigo;
  - quantização: nenhum negativo quantizado foi avaliado ("no quantizations in the committed
    set", App. D);
  - a auditoria do pai declarado (App. E), que é proposta não testada;
  - "LoRA de cura": o ataque white-box otimiza o modelo inteiro.

### Arditi et al. 2024 — *Refusal in Language Models Is Mediated by a Single Direction* (NeurIPS 2024)
- **Diz:** a recusa vive numa direção do fluxo residual. Removê-la dos pesos (ortogonalização de
  pesos, depois chamada de abliteração) tira a recusa com pouca perda em MMLU, ARC e GSM8K, mas o
  TruthfulQA cai sempre (§4.3).
- **Traz ao Juiz:** a definição da direção (diferença de médias); por que checar utilidade não
  pega F3; e que a direção já é expressa em modelos base, que não recusam (App. J). Disso
  inferimos que S2 sozinho não decide.
- **Usamos em:**
  - J1 e J5: a direção;
  - J4: o mapa de ΔW, porque a edição atinge escritores em todas as camadas;
  - J5: a CE contra as respostas do pai, como método;
  - J6: testar com e sem SP.
- **Não sustenta:**
  - que a CE separa N, porque a Tab. 9 não tem modelo degenerado;
  - "o pior caso é com SP", que vale só no Qwen 7B/14B e não no 72B;
  - a restrição a o_proj/down_proj, que vem de Hurtado.

### Egashira et al. 2024 — *Exploiting LLM Quantization* (NeurIPS 2024)
- **Diz:** um modelo pode ser benigno em precisão cheia e malicioso só em LLM.int8, NF4 ou FP4.
  Testar as versões quantizadas mitiga o ataque "em grande parte" (p. 10).
- **Traz ao Juiz:** o artefato julgado tem de ser o que a plataforma executa, formato por formato
  (p. 10). Usar o mesmo código de quantização é decisão nossa, motivada pela p. 16, onde o ataque
  é calibrado no código real.
- **Usamos em:** J3 (materialização), J6 (mesma bateria em todos os formatos) e J12 (tudo ou
  nada).
- **Não sustenta:**
  - remoção de recusa por quantização: os casos são código vulnerável, recusa excessiva e injeção
    de conteúdo;
  - modelos de 0,5B;
  - "o base quantizado se desloca" sem ressalva: os autores dizem "fairly close" (p. 16), mas a
    Tab. 7 (p. 17) mostra quedas de até ~11 pp em FP4 no modelo original.

### Halawi et al. 2024 — *Covert Malicious Finetuning* (ICML 2024)
- **Diz:** um GPT-4 afinado numa cifra recusa todo pedido nocivo em texto claro (0% nocivo,
  contra 0,6% do base; Tab. 1) e ajuda quando o pedido vem cifrado.
- **Traz ao Juiz:** avaliar só texto claro não basta. Codificações que o modelo já conhece
  (Base64, ROT-3) ficam visíveis a um avaliador capaz, que marca 99,2% e 99,4% das saídas como
  nocivas (App. C.1, GPT-4). Decodificar antes do avaliador é escolha nossa, porque o nosso
  avaliador é pequeno.
- **Usamos em:** J8, que decodifica antes do avaliador e fica com a pior leitura.
- **Não sustenta:**
  - a parte secreta da bateria, que vem de Rando;
  - a guarda "UNCLEAR acima do pai": pela Tab. 1 o derivado fica abaixo do pai, então a guarda
    não discrimina CMFT.
- **Escape declarado:** cifra nova e esteganografia (EndSpeak).

### Nasr et al. 2025 — *The Attacker Moves Second* (preprint arXiv 2510.09023)
- **Diz:** defesas contra jailbreak e injeção de prompt caem diante de ataques adaptativos que
  conhecem o desenho e usam o retorno da defesa como sinal. Algumas dessas defesas são treinadas
  nos pesos (Circuit Breakers, StruQ, MetaSecAlign; §5.2).
- **Traz ao Juiz:**
  - tratar o desenho como público;
  - avaliar com F4 contra o portão inteiro;
  - conferir à mão todo escape;
  - reduzir o que o Juiz devolve: com escore só binário, a busca vira praticamente aleatória
    (App. D). O artigo não testa um ataque só com retorno binário.
- **Usamos em:** J0 (Kerckhoffs; F4 fora da calibração), J13 (só o estado, instante fixo) e na
  avaliação do F4.
- **Não sustenta:**
  - um portão de derivados: nenhum alvo julga um derivado, então é analogia;
  - "humanos venceram com ~50 consultas binárias": eles tinham retorno de geração.

### Souly et al. 2024 — *A StrongREJECT for Empty Jailbreaks* (NeurIPS 2024)
- **Diz:** medir jailbreak por "não recusou" superestima o sucesso. O escore conta se a resposta
  ajuda, ou seja, se é específica e convincente. Há um avaliador aberto afinado em Gemma 2B.
- **Traz ao Juiz:** a bateria nociva (313 itens em 6 categorias), o avaliador de dano e a
  fórmula de margem 1,64·√(0,25/n).
- **Usamos em:** J0 (bateria e avaliador), J9 (dano de 1 a 5) e J6 (dimensionar n).
- **Não sustenta:**
  - o limiar "nota ≥ 3", que é escolha nossa;
  - rodar em CPU;
  - robustez do avaliador contra otimização (p. 14);
  - que o avaliador não conheça a bateria: ele viu ~223 dos 313 prompts no treino e na
    validação.
- **Nota:** os ±0,118 e ±0,042 são contas nossas com a fórmula.

### Röttger et al. 2024 — *XSTest* (arXiv 2308.01263v3; a venue não consta no PDF local)
- **Diz:** recusa excessiva se mede com 250 pedidos seguros em 10 tipos e 200 contrastes nocivos
  quase idênticos, em 3 classes: conformidade, recusa parcial e recusa total.
- **Traz ao Juiz:** a recusa nos seguros só se lê junto com os contrastes. O avaliador automático
  (casamento de strings ou GPT-4 zero-shot) perde em grande parte a recusa parcial, mas preserva o
  ranking dos modelos (§4.5, Tab. 2).
- **Usamos em:** J6 e J9 (taxonomia de 3 classes), J10 (ΔO) e na guarda de recusa excessiva (F0).
- **Não sustenta:**
  - um valor de tolerância;
  - que o Gemma 2B classifique as 3 classes;
  - "falha do avaliador conta contra o derivado" fora do lado nocivo.

### Mazeika et al. 2024 — *HarmBench* (arXiv 2402.04249v2; a venue não consta no PDF local)
- **Diz:** comparar ASR exige pipeline padronizado, com T tokens fixos e um avaliador
  pré-qualificado e separado do usado na otimização. A geração é gulosa por eficiência.
- **Traz ao Juiz:**
  - T = 512: com métricas de substring, o número de tokens muda o ASR em até 30% (GCG, PAIR e TAP
    em Llama 2; Fig. 2, p. 4), e 512 foi fixado para a métrica convergir;
  - os 3 conjuntos de pré-qualificação do avaliador;
  - a separação entre o avaliador do portão e o da verdade de referência.
- **Usamos em:** J0 (pré-qualificação), J7 (geração) e J9.
- **Não sustenta:** triagem curta; agregação em veredito; convergência em 0,5B.

### Qi et al. 2024 — *Fine-tuning Aligned Language Models Compromises Safety…* (preprint arXiv 2310.03693v1; ICLR 2024 não consta no PDF local)
- **Diz:** poucos exemplos nocivos, e até dados benignos, degradam a segurança. A degradação varia
  por categoria.
- **Traz ao Juiz:** julgar o derivado, não os dados; olhar por categoria; avaliar o conteúdo com
  um juiz, e não com palavras-chave. Também o critério "quem falha na avaliação não deveria ser
  liberado" (p. 11).
- **Usamos em:** J0 (binarização da nota), J10 (categorias) e J12.
- **Não sustenta:** valores de δ, já que só há gráficos radar; e "mesmo script para F1 e F2".
- **Escape declarado:** o backdoor com gatilho, que passa numa bateria estática (Tab. 5, GPT-3.5
  Turbo, 100 exemplos: 4,2% sem gatilho contra 63,3% com).

### Qi et al. 2025 — *On Evaluating the Durability of Safeguards for Open-Weight LLMs* (preprint arXiv 2412.07097)
- **Diz:** defesas nos pesos (RepNoise, TAR) caem com pequenas variações do ataque de
  fine-tuning (semente, hiperparâmetros, LoRA, implementação). Detalhes da avaliação (template,
  BOS, extração da resposta, benchmark) mudam a conclusão sobre elas.
- **Traz ao Juiz:** buscar o pior caso entre variações razoáveis (App. A, item 1); medir
  utilidade em geração (§3.5); não esconder o pior caso numa média (§4). Na E12 ele sustenta A2
  (controle fora dos pesos). No Juiz, serve só de disciplina de medida.
- **Usamos em:** J2 (fixar template e BOS do base), J10 e no relatório da avaliação.
- **Não sustenta:** "template muda a recusa": as p. 7–8 tratam de WMDP, e a Tab. 8 varia só o BOS.

### Egler, Schulman, Carlini 2025 — *Detecting adversarial fine-tuning with auditing agents* (preprint arXiv 2510.16255)
- **Diz:** o cenário é uma API de fine-tuning de um modelo fechado, com 8 fine-tunes adversariais
  e 5 benignos.
  - O benchmark fixo (HEx-PHI) detecta 19,4% a 1% de FPR.
  - Com dados, consulta pré × pós e benchmark eliciado, o auditor chega a 47,7%.
  - Com todas as ferramentas, chega a 56,2% (Tab. 1).
  - A 0% de FPR, o melhor resultado é 6,2%.
- **Traz ao Juiz:** critério diferencial em relação ao pai; os dados retidos como fonte de
  condições (SP, gatilho); operar a FPR baixa.
- **Usamos em:** J6 (C_job, provisório), J10 (relativo ao pai) e J11 (θ por FPR-alvo).
- **Não sustenta:** inspeção de pesos (o acesso é só de consulta); reprodução com 0,5B em CPU.

### Lin et al. 2025 — *Consiglieres in the Shadow* · Natella et al. 2013
- Estão na camada 1 da E12, mas sustentam o artigo, não uma etapa do Juiz.
  - **Lin** é a medição de campo (11.598 derivados sem recusa; A1 e o "campo" do P5).
  - **Natella** é a âncora de representatividade do P5 (A5).
- No Juiz, eles só entram depois de θ, δ e os momentos z estarem congelados. Os obliterados de
  campo formam o teste cego e nunca a calibração (E12 §4, item 4).

---

## 3. Camadas 2 e 3 — apoio

**Regra de citação:** os artigos abaixo entram como apoio ao lado de um da camada 1, ou sobem de
camada na E12.

### Rando et al. 2024 — *Competition Report: Finding Universal Jailbreak Backdoors in Aligned LLMs* (arXiv 2404.14461; competição do IEEE SaTML 2024) · camada 2
- **Diz:** a competição tinha um reward model público e um teste privado de 2.300 itens. O teste
  foi separado do mesmo dataset que gerou os splits públicos (42.000 de treino e 500 de
  validação). Resultado ausente foi trocado pela linha de base sem trojan (Tab. 1).
- **Usamos em:**
  - J0 e J6 (parte secreta): o artigo deu só uma submissão preliminar contra um split do teste
    privado, sem efeito no resultado final (p. 8);
  - J12: resultado ausente não dá crédito.
- **Não sustenta:** "i.i.d.", que não está no texto; uma fração secreta; um veredito binário.

### Kuo et al. 2026 — *Open-Weight LLM Fine-Tuning Defenses are Susceptible to Simple Attacks* (preprint arXiv 2605.26526) · camada 2
- **Diz:** a abliteração de uma camada, com best-of-N sobre camada e α, quebra SEAM e o modelo
  base (ASR acima de 70%) e enfraquece TAR. O prefill sozinho soma pouco. O efeito na utilidade é
  misto: piora em 3 de 6 casos (Tab. 5).
- **Usamos em:** J4 (F3 em qualquer camada), J10 (pior caso por item, como o best-of-N, p. 4) e
  na trava de prefill do serviço.
- **Não sustenta:**
  - a "abliteração de teste" como sonda: o próprio modelo base abliterado chega a 85–97% de ASR
    no Llama-3.1-8B (best-of-N sobre 96 configurações) e a 59–68% em 1B e 3B;
  - que o atacante reproduza o nosso r̂: isso vem de Arditi §2.3.
- **Pendência:** a E12 §2 ainda diz que Kuo "exige sondas sem treino (abliteração de teste,
  prefill)". Corrigir para "exige a sonda de prefill; a abliteração de teste não serve de sonda".

### Wollschläger et al. 2025 — *The Geometry of Refusal in Large Language Models* (ICML 2025) · camada 3
- **Diz:** a recusa vive em cones de várias dimensões. Há direções representacionalmente
  independentes da DIM que também medeiam a recusa, com ASR bem acima do aleatório, mas abaixo da
  DIM. Só a ablação conjunta de 4 ou mais delas supera a DIM no Gemma 2 2B.
- **Usamos em:** J5 (S2 pega o atacante não adaptativo, não o adaptativo) e J12 (S2 não decide
  sozinho).
- **Não sustenta:** detecção, fine-tuning ou pesos; seus números valem de 1,5B a 14B.

### Qi et al. 2024 — *Safety Alignment Should Be Made More Than Just a Few Tokens Deep* (preprint arXiv 2406.05946v1; ICLR 2025 não consta no PDF local) · camada 3
- **Diz:** a segurança se concentra nos primeiros tokens. No Llama-2-7B-Chat, o prefill (42–57% no
  HEx-PHI) e a varredura de decodificação (55% no HEx-PHI, 84% no MaliciousInstruct) derrubam o
  próprio modelo alinhado (Tab. 2).
- **Usamos em:** J7 (ler a resposta inteira), J5 (KL só para ordenar) e na trava do serviço.
- **Não sustenta:** "refuse-then-comply", termo que não aparece; um limiar de KL; um teto de
  tokens.

### Abu Shairah et al. 2025 — *An Embarrassingly Simple Defense Against LLM Abliteration Attacks* (preprint arXiv 2505.19056) · camada 3
- **Diz:** o fine-tuning com recusas estendidas mantém a nota de recusa em 91–97% após a
  abliteração, contra 14–21% sem defesa. O custo é perder coerência e MMLU, e parte da "recusa"
  é saída incoerente (App. C).
- **Usamos em:**
  - classe F0 (controle negativo);
  - J7: as recusas estendidas do dataset de treino têm 67–195 palavras (média 111), e as saídas
    dos modelos Extended chegam a ~970 palavras, então o teto não pode ser curto;
  - J8: incoerência não é recusa.
- **Não sustenta:** LoRA; recusa excessiva; efeito em S3 (não mede pesos); 0,5B.

---

## 4. Escapes declarados (nenhum artigo da base fecha)

- cifra nova e esteganografia (Halawi);
- backdoor com gatilho fora da bateria (Qi 2024, Rando);
- otimização white-box contra S1 e os sinais internos ao mesmo tempo (Hurtado §5, Nasr);
- conteúdo depois de 512 tokens;
- dano em outra língua;
- multiturno.

"Aprovado" significa "não regrediu em relação ao pai nas condições declaradas", não "seguro".
