# Nota de ética: anotação humana de respostas a pedidos nocivos (T-1606)

**Status:** rascunho de 12/11/2026, para revisão do orientador. **Falta:** perguntar à instituição
se a anotação precisa de aprovação de comitê de ética e, se precisar, submeter (passo humano).
Base: E13 §3.4, T-1005 (amostra de ~60 respostas), PLANO §0 (não publicar pesos nem gerações
nocivas).

## 1. O que será anotado e por quê

Dois anotadores leem uma amostra estratificada de respostas de modelos pequenos (0,5B e 1B) a
pedidos da bateria de referência (HarmBench) e a pedidos seguros do XSTest. Cada um marca, sem ver o
rótulo do outro nem o veredito do Juiz: se o modelo recusou, recusou em parte ou atendeu; e, nos
pedidos nocivos, se a resposta dá ajuda real ao pedido. A anotação confere o juiz automático da
verdade de referência (T-1002), e a concordância entre os dois (κ) vai para o artigo.

## 2. Riscos para os anotadores

- **Conteúdo perturbador:** parte das respostas descreve violência, crimes, drogas, armas, fraude ou
  discurso de ódio, com o detalhe que um modelo pequeno consegue dar.
- **Carga:** a leitura repetida de texto nocivo cansa. A amostra é pequena (~60 respostas por
  anotador) e não tem prazo apertado.
- **Sem risco de identificação:** não há dado pessoal dos anotadores no material nem no artigo; só a
  concordância agregada é publicada.

## 3. Consentimento e direito de desistir

- Antes de começar, cada anotador recebe esta nota, um exemplo do tipo de texto que vai ler e o guia
  de anotação (T-1005), e confirma por escrito que aceita participar.
- A participação é voluntária. O anotador pode **pular** qualquer resposta, **parar** a qualquer
  momento e **retirar** as anotações já feitas, sem precisar justificar e sem consequência
  acadêmica ou profissional.
- Os anotadores são membros do grupo de pesquisa ou colegas convidados. Nenhum anotador é o
  guardião da bateria secreta nem quem ataca o Juiz (T-1605).

## 4. Como o texto é guardado e descartado

- As respostas ficam **fora do git**, na pasta de dados do projeto (`$MODEL_GATE_DATA`, T-211), numa
  máquina de quem conduz o experimento. Os anotadores leem por uma planilha ou arquivo local
  entregue só a eles, sem cópia em serviço de nuvem público.
- Só vão para o repositório e para o artigo: os IDs da amostra, a semente do sorteio e as marcas
  (recusou, atendeu, ajuda real), nunca o texto das respostas.
- Ao fim do projeto (aceite ou rejeição final do artigo), as cópias entregues aos anotadores são
  apagadas, e as gerações ficam só onde a reprodução do artigo exige, cifradas.
- Nenhum peso de derivado nem geração nociva é publicado (PLANO §0). O artefato do artigo traz
  código, configurações, IDs e notas agregadas.

## 5. Para a seção de ética do artigo (T-1512)

> Two annotators, members of the research group who volunteered and could skip items or withdraw at
> any time, labeled about 60 responses of small models to harmful and safe requests. Responses were
> kept outside public repositories and services, only item IDs and labels are released, and no
> fine-tuned weights or harmful generations are published. \todo{aprovação do comitê, se exigida}

## 6. Pendências

- [ ] Perguntar à instituição se é preciso comitê (e qual o prazo, se for).
- [ ] Nomear os anotadores (T-1605) e colher o aceite por escrito.
- [ ] Escrever o guia de anotação junto da amostra (T-1005).
