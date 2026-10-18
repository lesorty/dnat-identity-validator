# Brainstorm 05 — Imagem OCI pronta enviada pelo desenvolvedor

**Origem:** conversa de 2026-10-14, durante a E3.
**Status:** ESTACIONADA (D-029). O build continua sendo feito pela rede; esta ideia fica para
avaliar em outro momento.
**Relacionados:** [04 — descentralização](04_descentralizacao.md) §12 · [E2b](../resultados/E2b_build_oci.md)

## Pergunta

Se o próprio desenvolvedor envia a aplicação, por que ele não envia a imagem OCI já construída?

## Análise

**Sigilo:** não muda nada. O desenvolvedor já tem o código; cifrar uma imagem pronta não expõe
nada a mais. O build pela rede não serve ao sigilo, e sim à **integridade e à proveniência**.

**O que se perde com a imagem pronta**
1. **Vínculo fonte → imagem.** No caso de código conhecido (E4), o dono do dataset aprova uma
   fonte; só o build atestado prova que a imagem executada veio dela.
2. **Proteção contra a supply chain do desenvolvedor.** Uma dependência maliciosa na máquina dele
   entra na imagem sem que ele saiba. O build em duas fases, em ambiente limpo e com varredura, é
   o centro da tese original.
3. **Recibo verificável (direção 1).** Passa de "este código, com estas dependências, gerou este
   resultado" para "esta imagem, que o desenvolvedor afirma ser X".

**O que se ganha:** nenhum custo de build na rede; some a questão de como a chave do código chega
aos builders (o desenvolvedor cifra a imagem com `K_app` e divide a chave com o comitê).

## Proposta para quando for retomada: nível de origem na política do dataset

| Nível | Origem da imagem | Garantia | Custo |
|---|---|---|---|
| 0 | Imagem pronta, assinada pelo desenvolvedor | Confia no desenvolvedor | Nenhum build na rede |
| 1 | Build atestado por 1 builder | Imagem vem da fonte declarada | 1 build |
| 2 | N builders concordantes | Detecta builder comprometido | N builds |

O dono do dataset escolhe o nível mínimo, como já faz com o nível de executor; o contrato registra
o nível de cada aplicação.

**Cuidado para o artigo:** se o nível 0 virar o caminho principal, o plano de build, que é a
contribuição mais original, perde peso. Como opção adicional, só amplia o sistema.
