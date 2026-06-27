# Revisão pendente — mudanças no paper (LADC)

> Documento vivo. Marque `[x]` conforme revisar cada item.
> **Seção** = onde olhar no PDF compilado · **Onde** = arquivo-fonte · **Verificar** = o que conferir.
> Itens novos vão sendo adicionados ao final conforme avançamos.

---

## Rodada 1 — Baseline M0 (sem isolamento) · commit `28089d5`

- [x] **Matriz `tab:comparison` — latência + overhead.** · **Seção:** Evaluation › Operational Cost (Tab. _Comparative results_, `tab:comparison`) · **Onde:** `evaluation_data/results_tables.tex` · **Verificar:** M0 `0.07` / A `25.2` / B `25.2` s; linha de overhead microVM `≈25.1` s; legenda diz "mesmo host, 2026-06-23".
- [x] **Prosa "Operational Cost" — parágrafo do M0.** · **Seção:** Evaluation › Operational Cost · **Onde:** `evaluation_data/section_evaluation.tex` · **Verificar:** 0.07 s → microVM ~25 s; M0 perde exfiltração (eth0) + 6 segredos; A/B contêm.
- [x] **Build rows do M0 = "—‡".** · **Seção:** Evaluation › Operational Cost (Tab. `tab:comparison`, nota ‡) · **Onde:** `results_tables.tex` · **Verificar:** explica que o builder não muda no M0 (build = A).
- [x] **Dados brutos.** · **Seção:** — (não vai no PDF; dado de apoio) · **Onde:** `evaluation_data/results_m0_campaign.md`.

## Rodada 2 — Gas blockchain + custo L2 · commit `fd442f4`

- [x] **Matriz — linha de gas register/purchase.** · **Seção:** Evaluation › Operational Cost (Tab. `tab:comparison`) · **Onde:** `results_tables.tex` · **Verificar:** `389 / 97` (k) nos três; marcador § na label.
- [x] **Nota § do gas.** · **Seção:** Evaluation › Operational Cost (rodapé da Tab. `tab:comparison`) · **Onde:** `results_tables.tex` · **Verificar:** 21k = transferência; L2 (0,03 gwei, ETH US$3.000) → ≈US$0,035 registrar / <US$0,01 comprar.
- [x] **Prosa "Operational Cost" — parágrafo de gas.** · **Seção:** Evaluation › Operational Cost · **Onde:** `section_evaluation.tex` · **Verificar:** gas independe da arquitetura (contrato = control plane compartilhado).
- [ ] **Script reprodutível.** · **Seção:** — (não vai no PDF; artefato) · **Onde:** `smart-contract/scripts/measure-gas.js` · **Verificar:** roda com `npx hardhat run scripts/measure-gas.js`.
- [ ] **Dados brutos.** · **Seção:** — (não vai no PDF; dado de apoio) · **Onde:** `evaluation_data/results_gas.md` (inclui L1 vs L2).

## Rodada 3 — Implementação aprofundada · commit `cb5d3af`

- [ ] **Abertura — dois baselines (A e M0).** · **Seção:** Implementation (parágrafo de abertura) · **Onde:** `section_implementation.tex` · **Verificar:** anuncia colocação (A) e sem-isolamento (M0).
- [ ] **Control Plane — modelo de acesso on-chain.** · **Seção:** Implementation › Control Plane (CVM1) · **Onde:** `section_implementation.tex` · **Verificar:** direito gravado em `keccak256(encryptedDatasetHash, encryptedApplicationHash, buyer)`, por CIDs cifrados (não IDs).
- [ ] **Nova subseção "Application Contract and Dependency Reuse".** · **Seção:** Implementation › Application Contract and Dependency Reuse · **Onde:** `section_implementation.tex` · **Verificar:** app = fonte + manifesto; deps como `site-packages` no `application.ext4`; roda sem recompilar nos 3 ambientes; contraste com SGX.
- [ ] **Subseção "Asset Integrity and Baselines" — M0 descrito.** · **Seção:** Implementation › Asset Integrity and Baselines · **Onde:** `section_implementation.tex` · **Verificar:** `DNAT_NO_MICROVM` → `vm/run-direct.sh`, mesmo `run.sh`, mesma saída JSON; herda rede/env/fs.

## Rodada 4 — Auditoria de claims C1–C7 · commit `cb5d3af`

- [ ] **Methodology corrigida (M0/gas não são mais TBD).** · **Seção:** Evaluation › Methodology · **Onde:** `section_evaluation.tex` · **Verificar:** removida a menção a "follow-up campaign/TBD" e a "AWS-cost"; agora diz M0 medido (mesmo host) + gas no Hardhat; resta só a coluna SGX citada.
- [ ] **Veredito da auditoria.** · **Seção:** — (meta; não é trecho do paper) · **Verificar:** C1–C5 e C7 já amarrados a testes/tabelas; C6 backado pela frase abaixo (opção A: frase única, sem tabela nova).
- [ ] **C6 — frase de superfície de código.** · **Seção:** Evaluation › Security Evaluation with STRIDE › ¶ _Information disclosure_ (fim do parágrafo, após o ref a `tab:blast-radius`) · **Onde:** `section_evaluation.tex` · **Verificar:** exec ~365 LoC vs ~590 build vs ~1500 control; "a superfície estática espelha a contenção de runtime"; não-redundante (eixo estático complementa o blast-radius dinâmico).

## Rodada 5 — Layout de tabelas + pseudo-código · *a commitar*

- [ ] **Tabelas movidas para junto do texto.** · **Seção:** Evaluation › 6.2 STRIDE e 6.3 Operational Cost · **Onde:** `section_evaluation.tex` (STRIDE e comparativa agora vivem lá; `results_tables.tex` virou stub; `\input` removido do `ladc.tex`) · **Verificar:** STRIDE aparece perto da 6.2 e a comparativa perto da 6.3 — **não mais no fim da seção 6**.
- [ ] **Floats `table*` → `table[htbp]`** (4 tabelas). · **Seção:** Evaluation · **Onde:** `section_evaluation.tex`, `section_results_ab.tex` · **Verificar:** nenhuma tabela de largura-dupla sendo adiada.
- [ ] **Pseudo-código do ciclo de execução** (`fig:exec-lifecycle`). · **Seção:** Implementation › Execution Plane · **Onde:** `section_implementation.tex` · **Verificar:** fiel ao `executor.py`/`run-vm.sh`; mostra sem-rede, descoberta de disco por marker, handshake serial, cleanup efêmero.

---

## Pendências conhecidas (a fazer, não são mudanças ainda)

- [ ] **Coluna SGX da matriz** — citar números do DNAT original (Eduardo). · **Seção:** Evaluation › Operational Cost (Tab. `tab:comparison`, coluna SGX).
- [x] **C6 (superfície de código por plano)** — resolvido: backado por frase única na evaluation (Rodada 4).
- [ ] **(Opcional) Boot breakdown por fase** (B7.3) — decompor os ~25 s. · **Seção:** Evaluation › Operational Cost.

### Verificações automáticas já feitas

- [x] **Lint de consistência** (2026-06-26): `\ref`→`\label`, labels únicos, `\cite`→`.bib`, `\input` existentes, ambientes balanceados — **5/5 OK**.
- [ ] **Compilar no Overleaf** para confirmação final (o lint não cobre pacotes/quirks do `llncs`). · **Seção:** documento inteiro.
