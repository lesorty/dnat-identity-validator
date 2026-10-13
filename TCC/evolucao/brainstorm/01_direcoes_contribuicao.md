# Brainstorm 01 — Direções para fortalecer a contribuição

**Origem:** conversa de 2026-10-12, após o feedback do LADC 2026 (submissão #33941).
**Status:** direções 1, 2 e 3 **aceitas como candidatas** (D-002); a escolha da tese fica para a E4.
**Relacionados:** [E1 — auditoria do código](../resultados/E1_auditoria_codigo.md) ·
[plano de ressubmissão](../../PLANO_RESSUBMISSAO.md)

## Diagnóstico de partida

- Os revisores leram o trabalho como **isolamento bem engenheirado**: separar planos e usar
  microVM são decisões de projeto, não resultados.
- A confiança no operador de infraestrutura continua total (R1, R2, R3). A E1 confirma e amplia
  isso: a CVM1 tem a chave global, a carteira única e vê dataset, aplicação e resultado em claro.
- Ledger e IPFS ocupam espaço sem ser a tese ("colcha de retalhos", R2).
- **O que é realmente diferente:** o build tratado como superfície de ataque de supply chain
  dentro de um pipeline confidencial, e o reuso de dependências sem recompilar (contra o SGX).
  Falta transformar isso em uma **garantia verificável**.

---

## Direção 1 — Cadeia verificável build → execução, com recibo ⭐

**Ideia.** A promessa deixa de ser "executou isolado" e passa a ser: *o comprador e o provedor
recebem uma prova de qual código, com quais dependências, sobre qual dataset, em qual ambiente
medido, produziu esta saída.*

**Mecanismo (esboço).**
1. Registro: o desenvolvedor publica o hash do **código-fonte + lockfile com hashes**, não do artefato.
2. Build: o build plane, atestado, produz `application.ext4` e uma **proveniência assinada**
   (in-toto/SLSA) ligando fonte + lockfile → artefato, com sua medição de atestação.
3. Liberação de chave: a chave **por ativo** só é entregue a um executor cuja atestação bata com a
   medição registrada (o papel do MRENCLAVE no DNAT/SGX).
4. Execução: o executor verifica a proveniência e o hash do dataset, roda e **assina um recibo**
   `(H(dataset), H(fonte), H(artefato), medição, H(saída), id da compra)`. A saída é cifrada
   para a chave pública do comprador.
5. Ledger: ancora o recibo (ou o hash dele) e conta as execuções da compra.

**Responde a:** R1 (contribuição explícita), R2 (por que um ledger; colcha de retalhos), R3 e T4
(confiança no operador), E7 (o que a CVM prova).

**Pré-requisitos no código (E1):** A1, A2, A4, A5, A6, A7, A8.

**Riscos.** Depende de uma resposta boa para o isolamento confidencial por job (E2): sem ela, a
medição atestada é a da CVM inteira, não a do job. A proveniência só tem valor se o build for
determinístico o bastante para ser checado (liga à direção 3).

**Custo / alvo.** Texto e desenho: **S**. Implementação e medição: **D**.

---

## Direção 2 — Distribuição de confiança entre operadores

**Ideia.** Hoje as três CVMs têm, na prática, o mesmo operador, e a compartimentação só limita o
raio de dano. Proposta: **cada plano sob o domínio de um stakeholder diferente**. Exemplo: o
provedor de dados custodia a chave do dataset (ou opera o plano de controle), o build roda sob
outro domínio, e o executor é atestado por todos. Assim a compartimentação vira **resultado de
segurança multi-stakeholder**: comprometer um operador não entrega os ativos dos outros.

**Responde a:** T4 (confiança total no operador), P4 (o que a separação ganha de fato), P6 (por
que um ledger: não há um operador confiável por todos).

**Pré-requisitos no código (E1):** A2 e A3 primeiro (sem eles, distribuir não muda nada),
depois A9 (autenticação mútua entre planos).

**Riscos.** É uma mudança de modelo de ameaça: barata de implementar e cara de argumentar.
Precisa de um cenário concreto (P5) que justifique quem opera o quê. Ponto de encontro com a
discussão sobre descentralização (E3).

**Custo / alvo.** Modelo de ameaça e texto: **S**. Separação real de chaves e carteiras: **D**.

---

## Direção 3 — Build reproduzido por construtores independentes

**Ideia.** Dois ou mais builders independentes reconstroem o artefato a partir do mesmo
`(fonte, lockfile)`. O executor, ou a liberação de chave, só aceita se os hashes coincidirem.
Os resultados vão para um log de transparência (estilo Sigstore/Rekor, ou o próprio ledger).

**Responde a:** T6 (cache envenenado, sdist malicioso), fortalece a tese do build, e torna
verificável o `contentHash` da aplicação (A6).

**Pré-requisitos no código (E1):** A6, A10, A11, A12.
- Build determinístico: `--require-hashes`, preferência por wheels, `SOURCE_DATE_EPOCH`, ext4 com
  UUID e timestamps fixos (ou trocar ext4 por um formato reproduzível, como erofs ou squashfs
  com opções fixas) **(a verificar)**.
- Build em duas fases: download com rede **sem** o código, instalação **sem** rede com o código
  (fecha A10).

**Riscos.** sdists raramente são determinísticos; pode ser preciso restringir a wheels ou aceitar
"reproduzível módulo whitelist". Diversidade real exige builders em domínios diferentes, o que
liga à direção 2.

**Custo / alvo.** Duas fases de build e hashes fixados: **S** (barato). Quórum de builders: **D**.

---

## Direção 4 — Política de saída (canal legítimo) · ESTACIONADA

**Ideia.** *Release gate* com política do provedor (limite de bytes, schema, orçamento de execuções).
**Por que estacionada:** escopo grande e atrai comparação com privacidade diferencial. Fica como
trabalho futuro; no máximo uma versão mínima (tamanho + schema) se sobrar tempo.

## Reforços transversais

- **Formalização (ProVerif/Tamarin):** sigilo do dataset e correspondência compra → execução →
  recibo. É o que mais pesa no DSN. Fica mais natural com a direção 1, que já define um protocolo.
- **Suíte de ataques reprodutível (T1–T5 e os novos)** publicada como benchmark: transforma
  evidência em contribuição de artefato.

## Como as direções se combinam

- **1 + 3** formam uma tese estreita e forte: *build verificável, reproduzido e atestado, com
  recibo de execução*.
- **2** é a extensão natural se a E3 mostrar que distribuir operadores compensa.
- As três dependem da resposta da **E2** (onde fica a fronteira atestada de cada job).

## Tópicos novos levantados em 2026-10-12 (aprofundar nas etapas)

- **Sistema distribuído para tirar a confiança de um operador ou provedor único** → E3.
  Hipótese inicial a testar: com computação confidencial, distribuir tudo não aumenta muito o
  sigilo, mas pode aumentar muito a **verificabilidade** (execuções corretas, sem rollback nem
  escolha seletiva) e a **tolerância a falhas do TEE** de um único fabricante.
- **Firecracker fora da computação confidencial** → E2. A E1 confirma que, na CVM, o sistema
  roda em modo direto, sem isolamento entre jobs (A14). Esse é hoje o maior buraco arquitetural.
