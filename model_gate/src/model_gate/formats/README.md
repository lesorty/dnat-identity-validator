# Formatos liberados (D5, E14 §8)

Precisão cheia, LLM.int8, NF4 e FP4. O Juiz e o serviço arredondam os pesos para o formato e
fazem a conta em CPU, com o mesmo código dos dois lados.

## O bitsandbytes roda em CPU? (T-503)

**Sim.** Medido em 12/11/2026 com o Qwen2.5-0.5B-Instruct (revisão `7ae5576`), num notebook
Intel Core 7 150U, sem GPU:

| Pacote | Versão |
|---|---|
| bitsandbytes | 0.50.2 |
| torch | 2.15.0+cpu (o do `uv.lock`) |
| transformers | 5.22.1 |

| Formato | Configuração | Camadas | Carga | 12 tokens gulosos | Resposta |
|---|---|---|---|---|---|
| LLM.int8 | `load_in_8bit=True` | `Linear8bitLt` | 2,3 s | 3,5 s | "The capital of France is Paris." |
| NF4 | `load_in_4bit`, `bnb_4bit_quant_type="nf4"`, cômputo em float32 | `Linear4bit` | 3,8 s | 2,0 s | igual |
| FP4 | `load_in_4bit`, `bnb_4bit_quant_type="fp4"`, cômputo em float32 | `Linear4bit` | 5,0 s | 2,1 s | igual |

`device_map="cpu"`, `torch_dtype=float32`. Nenhum erro nos três; os tempos são de uma execução
só, com o modelo minúsculo, e não servem de medida de custo.

O que isso muda e o que fica em aberto:
- O bitsandbytes serve de **referência** para a T-502 (quantizar por conta própria) e pode
  substituí-la; a escolha é da T-502.
- **LLM.int8 em CPU faz a multiplicação em float16:** o bitsandbytes avisa
  `MatMul8bitLt: inputs will be cast from torch.float32 to float16`. Como o serviço usaria o mesmo
  código, a conta é igual nos dois lados, mas não é a mesma do LLM.int8 em GPU; a segunda bancada
  em GPU confidencial (E14 §8) tem de comparar.
- O pacote **não entrou no `uv.lock`**: adicioná-lo é decisão da T-502. Para repetir sem mexer no
  lock, siga o cabeçalho de `experiments/probe_bitsandbytes.py`. O `uv run --with bitsandbytes`
  troca o torch CPU pelo do PyPI, com CUDA (`2.15.0+cu132`); a prova feita assim também passou,
  mas não é o ambiente travado.
