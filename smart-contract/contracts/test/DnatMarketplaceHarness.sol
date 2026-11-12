// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../DnatMarketplace.sol";

/**
 * Só para os testes do hardhat: grava um derivado sem a regra de quem pode gravar, que é da
 * T-703 (registerDerivative restrito ao executor). Não é implantado por deploy.js.
 */
contract DnatMarketplaceHarness is DnatMarketplace {
    function harnessRegisterDerivative(DerivativeInfo calldata info) external returns (uint256 id) {
        id = ++nextAssetId;
        Asset storage d = assets[id];
        d.id = id;
        d.assetType = AssetType.Derivative;
        d.owner = payable(msg.sender);
        d.title = "derivado";
        d.contentHash = info.derivativeHash;
        derivatives[id] = info;
        emit DerivativeRegistered(id, info.parentId, info);
    }
}
