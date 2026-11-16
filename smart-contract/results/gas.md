# Gás por função do DnatMarketplace (T-709)

gasUsed na rede hardhat em processo (determinístico para as mesmas entradas); o número citado no artigo sai da execução na nuvem (T-709, fase de testes).

Hardhat 2.27.0 · solc 0.8.20

| Função | gasUsed |
|---|---|
| registerAsset (dataset, bloom vazio) | 411,779 |
| registerAsset (dataset, bloom 256 B) | 596,286 |
| registerAsset (aplicação) | 349,676 |
| purchaseAccess | 83,135 |
| registerAsset (modelo base) | 351,811 |
| registerDerivative (recibo, aprovado) | 494,028 |
| registerDerivative (recibo, reprovado) | 474,140 |
| revokeDerivative | 56,288 |
