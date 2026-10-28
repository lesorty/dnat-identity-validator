# E12 · Base teórica e plano de implementação

**Data:** 2026-10-27 · **Status:** **decidido em 2026-10-27** ([D5](../DECISOES.md)). O §5 fica como histórico: o
plano está na [E13](E13_plano_trabalho.md), e a especificação do Juiz na [E14](E14_especificacao_juiz.md), que vale sobre ele.
**Base:** [E10](E10_problema.md) §5 (problema decidido), [E9](E9_testes_validos.md) §3,
[E6](E6_alt_modelos_abertos.md) §7, [E8](E8_alinhamento_dsn.md) §9 e as leituras
[06](../../pesquisa/06_leitura_obliteracao.md), [07](../../pesquisa/07_leitura_bounty.md) e
[08](../../pesquisa/08_leitura_cadeia_custodia.md).

**Por que este documento:** os levantamentos deixaram 72 PDFs em `pesquisa/artigos/`. Ler e citar
tudo gera ruído. Aqui fica o conjunto mínimo que sustenta o artigo, o motivo de cada escolha e o
que cada artigo exige do código.

---

## 1. Triagem (2026-10-27)

- **Triagem do autor:** 35 mantidos e 37 marcados para excluir (formulário de triagem).
- **Ajustes propostos sobre a triagem:**
  - **voltam:** XSTest, porque a propriedade da E10 §5 inclui "sem aumentar a recusa excessiva" e
    nada mais mede isso;
  - **entram:** Egashira et al. 2024 (formato do derivado) e Natella et al. 2013
    (representatividade);
  - **saem**, mesmo mantidos: **MalHug, Horwitz, Nguyen e o survey de Huang**. Os três primeiros tratam da integridade do arquivo ou de linhagem inferida, que a
    custódia torna desnecessária; o survey só serviria à tabela de relacionados.
- **Só citação, sem PDF:** Waiwitlikhit et al., *ZkAudit* (ICML 2024), como alternativa sem TEE
  ao recibo P2.
- **Resultado:** 34 artigos, em três camadas (§2): 33 PDFs em `pesquisa/artigos/`, organizados
  por camada e tema ([índice](../../pesquisa/artigos/README.md)), mais o Natella, que precisa ser
  baixado pelo acesso institucional. Os 40 PDFs descartados saíram do repositório e seguem no
  histórico do git (commit `f0fba2a`).

---

## 2. Priorização

### Camada 1 · Base teórica (13 artigos, leitura completa)

Cada artigo aqui sustenta uma afirmação do artigo que não se sustenta sem ele.

| # | Artigo | Por que está na base |
|---|---|---|
| 1 | Qi et al., *Fine-tuning Compromises Safety* (ICLR 2024) | Prova que a recusa se perde na derivação, por intenção (F2) **e por acidente** (F1). Sem ele não há problema |
| 2 | Arditi et al., *Refusal… Single Direction* (NeurIPS 2024) | Mostra a via sem treino (F3) e que ela **preserva a utilidade**: checar capacidade não basta. Dá também o sinal S2 |
| 3 | Lin et al., *Consiglieres in the Shadow* (2025) | Única medição de campo validada: 11.598 derivados sem recusa, herdados por derivação. Motivação e "campo" do P5 |
| 4 | Halawi et al., *Covert Malicious Finetuning* (ICML 2024) | Define F4: um derivado que passa por inspeção de dados e avaliação em texto claro. Obriga a bateria a ir além do texto claro |
| 5 | Egashira et al., *Exploiting LLM Quantization* (NeurIPS 2024) | Um modelo pode parecer seguro em precisão cheia e ser malicioso quantizado. Obriga o portão a avaliar **o formato que sai** |
| 6 | Qi et al., *Durability of Safeguards* (2025) | Defesas nos pesos (RepNoise, TAR) caem com pequenas variações do ataque. Justifica pôr o controle **fora dos pesos** |
| 7 | Hurtado, *Has This Checkpoint Been Abliterated?* (2026) | Linha de base do portão (AUROC 0,95) e o limite que a custódia fecha: a **referência forjável** |
| 8 | Egler, Schulman, Carlini, *Auditing Agents* (2025) | Segunda linha de base (56,2% a 1% de FPR) e prova de que detectar exige dados + pré + pós, que só o custodiante tem |
| 9 | Souly et al., *StrongREJECT* (NeurIPS 2024) | Separa "não recusou" de "ajudou o atacante". Define como S1 e a verdade de referência medem dano |
| 10 | Röttger et al., *XSTest* (NAACL 2024) | Mede a outra metade da propriedade: recusa excessiva em pedidos seguros (falso alarme do lado do usuário) |
| 11 | Mazeika et al., *HarmBench* (ICML 2024) | Protocolo: parâmetros fixos (tokens gerados) e juiz pré-qualificado. Sem isso os números não se comparam |
| 12 | Nasr et al., *The Attacker Moves Second* (2025) | Avaliação estática engana; a robustez só vale contra atacante adaptativo (RQ4, B6) |
| 13 | Natella et al., *On Fault Representativeness of Software Fault Injection* (IEEE TSE 2013) | Âncora de dependabilidade para o P5: até 72% das falhas injetadas não representam falhas reais. Transforma "a população é nossa" em pergunta de pesquisa |

### Camada 2 · Vizinhos e extensões (5 artigos, seções-chave)

| Artigo | Por que |
|---|---|
| Schnabl et al., *Attestable Audits* (2025) | Vizinho direto do recibo P2: benchmark atestado em TEE, mas para modelo fixo |
| Spoczynski et al., *Atlas* (2025) | Vizinho mais próximo na arquitetura (TEE + log + fine-tuning), com segurança do modelo fora do escopo |
| Rando et al., *Universal Jailbreak Backdoors* (SaTML 2024) | Molde do bounty P4: oráculo automático sobre conjunto privado e pesos abertos |
| Casper et al., *Open-Weight Risk Management* (TMLR 2026) | Fonte citável do consenso "qualquer salvaguarda nos pesos cai" |
| Kuo et al., *Fine-Tuning Defenses… Simple Attacks* (2026) | Exige sondas sem treino (abliteração de teste, *prefill*) na bateria. No DNAT, o serviço trava o template, a decodificação gulosa e proíbe *prefill*, e os pesos nunca saem (T-108, [E14](E14_especificacao_juiz.md) §6.1): essas sondas viram ataques que a custódia barra, não itens da bateria |

### Camada 3 · Só citação (uma frase cada)

Wollschläger, Qi *shallow*, Wallace, TAR, RepNoise, Antidote, Abu Shairah, Virus, SORRY-Bench,
10a Labs, Laminator, Anthropic *Confidential Inference*, Google SAIF, Jin *Proof-of-Guardrail*,
Erfan *AIBOM*, HackAPrompt, ZkAudit.

**Moldes do DSN** (fora de `pesquisa/`, já em `DSN2027/referencias/dsn/`): Multi-version ML [55],
ReMlX [56] e TPU-FI [57] dão a forma do artigo, não o conteúdo, e seguem como estão na E8 §9.

---

## 3. A base teórica: cinco afirmações

O artigo se apoia em cinco afirmações encadeadas. Cada uma tem a evidência que a sustenta e o que
ela obriga o sistema a fazer.

| # | Afirmação | Evidência | Consequência no desenho |
|---|---|---|---|
| A1 | A recusa **não sobrevive à derivação**, por acidente ou por ataque, e o derivado continua útil | Qi 2024; Arditi; Lin (campo) | O portão julga **o derivado**, não o script nem os dados (D2) |
| A2 | Proteger **dentro dos pesos** não resiste a quem escreve neles | Qi 2025 (durabilidade); Casper; Kuo | O controle fica **fora dos pesos**, num ponto que retém o derivado: a custódia na CVM |
| A3 | Detectar o derivado comprometido funciona, mas **só sob hipóteses que a custódia garante** | Hurtado (referência autêntica); Egler (dados + pré + pós) | Referência do pai custodiada e não forjável; derivado retido até o veredito |
| A4 | O derivado pode **enganar a avaliação**: codificação, formato ou treino contra o limiar | Halawi; Egashira; Nasr | Bateria parcialmente secreta e não só em texto claro; avaliar o formato liberado; atacante adaptativo na avaliação |
| A5 | Uma avaliação só vale com **medida válida** e **população representativa** | StrongREJECT; XSTest; HarmBench; Natella (+ TPU-FI) | Recusa e dano medidos à parte; falso alarme em pedidos seguros; parâmetros fixos; teste cego com obliterados de campo |

**Leitura em uma frase:** como a recusa se perde na derivação (A1) e não se protege nos pesos
(A2), o único ponto de controle é a liberação; a custódia é o que torna a detecção confiável (A3);
o portão precisa resistir a quem tenta enganá-lo (A4) e ser medido de forma válida (A5).

**O que a base não sustenta (declarar como limitação):**
- backdoor com gatilho (E8 §9.2): nenhum artigo da base mostra detecção confiável;
- atestar que o portão rodou não prova que ele funciona (Jin *Proof-of-Guardrail*): a eficácia
  vem da avaliação adaptativa, não do recibo.

---

## 4. O que muda no desenho por causa da base

1. **Formato liberado (novo, de Egashira).** Três opções, a escolher:
   - (a) o portão avalia o derivado em precisão cheia **e** nas quantizações *zero-shot* comuns
     (LLM.int8, NF4, FP4);
   - (b) a plataforma só libera o formato avaliado e proíbe requantização fora da custódia;
   - (c) ruído gaussiano nos pesos antes de liberar (a defesa testada pelos autores), medindo a
     utilidade.
   **Proposta:** (a) no MVP, porque custa só mais execuções da bateria; (b) como regra do
   contrato. Entra como variante de F4 ("adaptativo por formato").
2. **Bateria S1** (StrongREJECT + XSTest): resposta lida inteira, 512 tokens fixos (HarmBench),
   com e sem *system prompt* (Arditi), com parte em codificação (Halawi) e parte secreta.
3. **Verdade de referência** com juiz diferente do juiz do portão e amostra conferida por humanos
   (E9 B3). Sem Eiras na base, a justificativa passa a ser HarmBench (juiz pré-qualificado) e a
   regra 4 da E9 §1 (independência).
4. **Representatividade (P5):** a população injetada é comparada com os obliterados públicos
   (teste cego, nunca na calibração). Seguindo Natella, injeções que não se parecem com o campo
   são reportadas à parte, não descartadas em silêncio.

---

## 5. Plano de implementação no código

### 5.1 Onde o código está hoje

- **Execução:** numa CVM, `vm_runtime/` roda o job em **modo direto** (`DNAT_NO_MICROVM`,
  `vm_runtime/executor.py:15`; `vm_runtime/vm/run-direct.sh`), uma linha de base sem isolamento
  entre jobs, e devolve `returncode`, `stdout` e `stderr`. O caminho com microVM Firecracker
  (`run-vm.sh`) é legado: não roda numa CVM e não faz parte da arquitetura (D4).
- **Build:** `build_vm_runtime/` monta a app com as dependências Python; numa CVM, em modo direto
  (`build-direct.sh`).
- **Contrato:** `smart-contract/contracts/DnatMarketplace.sol` só conhece `Dataset` e
  `Application` (linhas 28–31); `revokeAsset` (linha 183) já serve à recuperação.
- **Não existe** nada de modelo, derivado ou portão, nem a CVM de uso único por job da D4. O piloto
  segue a D4 sem container: CVM1 como plano de controle, builder numa CVM separada e uma CVM de uso
  único por job (decidido na T-102, 28/10).

### 5.2 Princípio

O portão é **pesquisa primeiro e integração depois**. Os sinais e a população se desenvolvem como
um pacote Python isolado, rodando em CPU fora do DNAT. Só depois de passar no piloto ele vira
uma aplicação da whitelist (D2) dentro do DNAT. Assim o critério de corte da E7 §7 é testado antes
de qualquer mudança no executor ou no contrato.

### 5.3 Estrutura proposta

```
model_gate/
  config/prereg.yaml        # limiares, métricas e critérios de corte, commitados antes do teste (E9 §1.1)
  population/
    abliterate.py           # F3: receita de Arditi, varrendo camada e intensidade
    finetune.py             # F1 e F2: o MESMO script, mudando só os dados (argumento de D2)
    fetch_public.py         # obliterados públicos do HF, só para o teste cego (P5)
    quantize.py             # int8 / NF4 / FP4 de cada derivado (Egashira)
  signals/
    s1_battery.py           # StrongREJECT + XSTest; 512 tokens; com e sem system prompt
    s2_refusal_gap.py       # gap na direção de recusa do base custodiado (Arditi, Hurtado)
    s3_rank1.py             # energia rank-1 de ΔW (Hurtado)
  verdict.py                # escada da E14 §6.3: só S1 reprova; S2 e S3 a FPR 5% levam a inconclusivo
  ground_truth/judge.py     # juiz independente do portão + amostra para conferência humana
  eval/run_campaign.py      # seeds, bootstrap, TPR a FPR 1% e 5%, AUROC, liberação silenciosa
```

Dependências: `torch` (CPU), `transformers`, `peft`, `bitsandbytes` só para `quantize.py`.
Modelo base do piloto: Qwen2.5-0.5B-Instruct (E7 §7).

### 5.4 Etapas

| Etapa | Prazo | Entrega | Critério de saída |
|---|---|---|---|
| **0 · Piloto** | até 01/nov | `abliterate.py`, `finetune.py` (Alpaca), S1–S3 e `verdict.py`; 2 abliterações, 2 LoRA benignos, 2–3 obliterados públicos | Corte da E7 §7: algum sinal separa abliterados de benignos **e** o veredito leva ≤ 80 min em 4 vCPU |
| **1 · População e calibração** | 03–09/nov | F1–F3 com varredura de intensidade; `quantize.py`; `ground_truth/judge.py`; pré-registro commitado | Calibração em Qwen2.5 fechada antes de abrir o teste |
| **2 · Integração no DNAT** | 03–09/nov, em paralelo | Ver §5.5 | Um job de fine-tuning gera um derivado que fica na custódia e só vira ativo com veredito aprovado |
| **3 · Adaptativo e generalização** | 10–16/nov | F4: treino contra o limiar, abliteração + LoRA de cura, CMFT, **quantização condicionada**; família não vista (Llama-3.2-1B); teste cego com obliterados de campo | Curvas de escape × rodadas; queda de cobertura entre famílias |
| **4 · Campanha** | 17–25/nov | Tudo com seeds e IC por bootstrap; custo e *overhead* em CVM × VM comum | Resultados congelados até 25/nov |

### 5.5 Integração no DNAT (etapa 2)

1. **Contrato** (`DnatMarketplace.sol`):
   - novos tipos `Model` e `Derivative` em `AssetType`;
   - num derivado: `parentId`, hash do derivado, hash do código do portão, compromisso (hash) da
     bateria secreta e veredito; esse conjunto é o **recibo P2** em forma mínima, com atestação
     implícita (D3);
   - registro de derivado só pelo executor; derivado reprovado nunca fica `active`;
   - `revokeAsset` cobre a revogação posterior.
2. **Executor** (CVM de job de uso único, D4):
   - a CVM1 tira uma CVM nunca usada do *warm pool*, entrega o job e a destrói no fim; o tamanho da
     CVM comporta o 0.5B (vários GiB);
   - o derivado volta à CVM1, que o cifra no IPFS, nunca para `result.json`; o usuário recebe só
     métricas de esquema fixo;
   - o portão roda como **segundo job**, noutra CVM de uso único, com o derivado e o base
     custodiado conferidos por hash, e grava `verdict.json`.
3. **Primeiro fora do DNAT**, depois na CVM de uso único: rodar o portão como pacote isolado mede o
   custo dele sem o custo da custódia, que já tem campanha própria
   (`assets/tests/run_cvm_overhead_campaign.sh`).

**Ordem de corte** (mantém o PLANO §1): bounty → contrato (derivado não exportável) → ponto em
7–8B → extras do adaptativo. A camada 1 da base não se corta.

---

## 6. Decisões (2026-10-27)

1. **Adotada** a camada 1 (§2) como base teórica e as afirmações A1–A5 (§3) como espinha do texto.
2. **Aplicada** a triagem em `pesquisa/artigos/` com os ajustes do §1.
3. **Formato liberado:** (a)+(b), ou seja, avaliar as quantizações comuns e liberar só os formatos
   avaliados (§4 item 1).
4. **Adiado:** o piloto (etapa 0) só começa depois que o plano de trabalho estiver consolidado.
