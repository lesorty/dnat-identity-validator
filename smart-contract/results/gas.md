# Gás por função do DnatMarketplace (T-709)

gasUsed na rede hardhat em processo (determinístico para as mesmas entradas); o número citado no artigo sai da execução na nuvem (T-709, fase de testes).

Hardhat 2.27.0 · solc 0.8.20

| Função | gasUsed |
|---|---|
| registerAsset (dataset, bloom vazio) | 388,980 |
| registerAsset (dataset, bloom 256 B) | 573,487 |
| registerAsset (aplicação) | 326,835 |
| purchaseAccess | 96,703 |
| registerAsset (modelo base) | 351,619 |
| registerDerivative (recibo, aprovado) | 493,962 |
| registerDerivative (recibo, reprovado) | 474,074 |
| revokeDerivative | 56,222 |
