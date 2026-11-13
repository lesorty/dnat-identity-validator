// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title Confidential Data & Application Marketplace (DNAT-style)
 *
 * High-level idea:
 * - "Asset" is generic: it can be either a DATASET or an APPLICATION.
 * - Each asset is stored off-chain (e.g., encrypted in IPFS); on-chain we keep:
 *      * owner (dataset or application provider)
 *      * price in wei
 *      * URI for encrypted bytes (IPFS CID, etc.)
 *      * URI or hash for the manifest
 *      * SHA-256 hash of the plaintext (for integrity)
 *      * optional Bloom filter bytes for dataset whitelisting
 * - Users buy the right to run (dataset D, application A).
 *   The contract:
 *      * checks D is a dataset and A is an application
 *      * transfers ETH to both owners
 *      * records that <D, A, user> has rights
 *      * emits an event the Executor can later read
 */
contract DnatMarketplace {
    // ------------------------------------------------------------------------
    // Types and storage
    // ------------------------------------------------------------------------

    // Model e Derivative ficam no fim para não mudar os valores de Dataset (0) e Application (1).
    enum AssetType {
        Dataset,
        Application,
        Model,      // base custodiado; o dono deposita pelo caminho de registerAsset
        Derivative  // derivado julgado pelo Juiz; não entra por registerAsset (só pelo executor, T-703)
    }

    // Veredito do Juiz sobre um derivado (E14 §6.3). O zero é Pending: um derivado retido ainda
    // sem veredito lê Pending, e o valor padrão do Solidity nunca pode ser um aprovado.
    enum Verdict {
        Pending,
        Approved,
        Rejected,
        Inconclusive
    }

    // Campos do derivado no recibo (T-104, E14 §10.1): só hashes, veredito e data. Medidas e
    // motivos ficam no verdict.json, conferido por verdictHash. Ligado ao Asset por assetId,
    // sem mexer no layout de Asset usado por purchaseAccess. O hash do pai é o contentHash do
    // Asset parentId; a raiz é o próprio pai, porque derivado de derivado não entra (um nível só).
    struct DerivativeInfo {
        uint256 parentId;             // Model de que o derivado saiu
        bytes32 parentReferenceHash;  // referência do pai, medida sob custódia
        bytes32 derivativeHash;       // digest do derivado retido (regra de model_gate.io.digest)
        bytes32 judgeHash;            // hash do pacote do Juiz (identifica a versão)
        bytes32 batteryCommitment;    // compromisso da parte secreta da bateria (T-109)
        bytes32 preregHash;           // hash do prereg.yaml (limiares congelados)
        bytes32 datasetHash;          // hash do dataset do job, retido
        bytes32 verdictHash;          // hash do verdict.json
        bytes32 identityId;           // SHA-256 da chave pública de quem pediu o job (E14 §18)
        Verdict verdict;
        uint64 decidedAt;             // data do veredito
    }

    struct Asset {
        uint256 id;               // internal ID
        AssetType assetType;      // dataset or application
        address payable owner;    // dataset provider or application provider
        string title;             // short title for catalog visualization
        string description;       // descriptive text for catalog visualization

        // Off-chain references:
        // - encryptedUri: IPFS CID or any URL for the encrypted asset ϵ(α, κ)
        // - manifestUri: IPFS CID or URL for the manifest μ
        string encryptedUri;
        string manifestUri;

        // Hash of the plaintext asset α (e.g., SHA-256(bytes)), used for integrity checking
        bytes32 contentHash;

        // Price to acquire usage rights, in wei
        uint256 price;

        // For datasets only: Bloom filter that encodes which apps are allowed free access.
        // For applications this is typically empty.
        bytes bloomFilter;

        bool active;              // if false, asset is revoked (no new purchases)
    }

    uint256 public nextAssetId;
    mapping(uint256 => Asset) public assets;

    // Access rights: user is allowed to run `applicationId` over `datasetId`
    // key = keccak256(datasetId, applicationId, user)
    mapping(bytes32 => bool) public accessRights;

    // Campos de cada derivado, por assetId (só para assets do tipo Derivative).
    mapping(uint256 => DerivativeInfo) internal derivatives;

    // Derivados retirados pelo operador (T-705). Fica fora de DerivativeInfo para não mudar o recibo.
    // A marca é definitiva: o dono não reativa um derivado revogado (T-704).
    mapping(uint256 => bool) public derivativeRevoked;

    // Papéis (T-703, T-105): o admin troca o operador; o operador é o executor (CVM1), o único que
    // pode afirmar que um derivado passou pelo Juiz. O dono do derivado é o adversário e não grava.
    address public admin;
    address public operator;

    // Simple reentrancy guard (because we transfer ETH)
    bool private locked;

    // ------------------------------------------------------------------------
    // Events
    // ------------------------------------------------------------------------

    event AssetRegistered(
        uint256 indexed id,
        AssetType assetType,
        address indexed owner,
        uint256 price,
        bool hasBloomFilter
    );

    event AssetUpdated(
        uint256 indexed id,
        uint256 newPrice,
        bool newActive
    );

    event AssetRevoked(
        uint256 indexed id
    );

    // Emitido quando o operador retira um derivado (T-705); judgeHash é o do veredito original.
    event DerivativeRevoked(
        uint256 indexed id,
        string reason,
        bytes32 judgeHash
    );

    event OperatorChanged(address indexed previousOperator, address indexed newOperator);

    // Emitido quando o executor grava um derivado (T-703), com os mesmos campos de DerivativeInfo.
    event DerivativeRegistered(
        uint256 indexed id,
        uint256 indexed parentId,
        DerivativeInfo info
    );

    event AccessPurchased(
        uint256 indexed datasetId,
        uint256 indexed applicationId,
        address indexed user,
        uint256 datasetPrice,
        uint256 applicationPrice
    );

    // ------------------------------------------------------------------------
    // Modifiers
    // ------------------------------------------------------------------------

    modifier nonReentrant() {
        require(!locked, "ReentrancyGuard: reentrant call");
        locked = true;
        _;
        locked = false;
    }

    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin");
        _;
    }

    modifier onlyOperator() {
        require(msg.sender == operator, "Only operator");
        _;
    }

    // ------------------------------------------------------------------------
    // Papéis (T-703)
    // ------------------------------------------------------------------------

    /**
     * @dev Quem implanta vira admin; o operador é fixado aqui (deploy.js) e só o admin o troca.
     */
    constructor(address initialOperator) {
        require(initialOperator != address(0), "Operator required");
        admin = msg.sender;
        operator = initialOperator;
        emit OperatorChanged(address(0), initialOperator);
    }

    function setOperator(address newOperator) external onlyAdmin {
        require(newOperator != address(0), "Operator required");
        emit OperatorChanged(operator, newOperator);
        operator = newOperator;
    }

    // ------------------------------------------------------------------------
    // Asset management (datasets + applications)
    // ------------------------------------------------------------------------

    /**
     * @dev Register a new asset (dataset or application).
     *
     * @param assetType    Dataset or Application
     * @param encryptedUri IPFS CID or URL of encrypted asset ϵ(α, κ)
     * @param manifestUri  IPFS CID or URL of manifest μ
     * @param contentHash  SHA-256 (or similar) hash of plaintext asset α
     * @param price        Price in wei to acquire rights
     * @param bloomFilter  For datasets: Bloom filter bytes; for applications: leave empty
     *
     * @return id          Internal asset ID
     */
    function registerAsset(
        AssetType assetType,
        string calldata title,
        string calldata description,
        string calldata encryptedUri,
        string calldata manifestUri,
        bytes32 contentHash,
        uint256 price,
        bytes calldata bloomFilter
    ) external returns (uint256 id) {
        require(bytes(title).length > 0, "Title required");
        // Por aqui o derivado nasceria ativo e sem veredito; ele só entra pelo executor (T-703).
        require(assetType != AssetType.Derivative, "Derivative only via executor");
        id = ++nextAssetId;

        bytes memory bf;
        if (assetType == AssetType.Dataset) {
            // For datasets we keep the Bloom filter on-chain (Executor can read it off-chain).
            bf = bloomFilter;
        }

        Asset storage newAsset = assets[id];
        newAsset.id = id;
        newAsset.assetType = assetType;
        newAsset.owner = payable(msg.sender);
        newAsset.title = title;
        newAsset.description = description;
        newAsset.encryptedUri = encryptedUri;
        newAsset.manifestUri = manifestUri;
        newAsset.contentHash = contentHash;
        newAsset.price = price;
        newAsset.bloomFilter = bf;
        newAsset.active = true;

        emit AssetRegistered(id, assetType, msg.sender, price, bf.length > 0);
    }

    /**
     * @dev Update price and active flag for an asset you own.
     */
    function updateAsset(
        uint256 assetId,
        uint256 newPrice,
        bool newActive
    ) external {
        Asset storage a = assets[assetId];
        require(a.id != 0, "Asset does not exist");
        require(a.owner == msg.sender, "Only owner");

        // O dono do derivado é o adversário (T-105): reprovado, inconclusivo, pendente ou revogado
        // pelo operador nunca volta a ficar ativo por aqui (C1, T-704).
        if (a.assetType == AssetType.Derivative && newActive) {
            require(!derivativeRevoked[assetId], "Derivative revoked");
            require(derivatives[assetId].verdict == Verdict.Approved, "Derivative not approved");
            // T-707: com o pai fora, o derivado não volta.
            require(assets[derivatives[assetId].parentId].active, "Parent inactive");
        }

        a.price = newPrice;
        a.active = newActive;

        emit AssetUpdated(assetId, newPrice, newActive);
    }

    /**
     * @dev Permanently revoke an asset (no new access can be purchased).
     *      Existing access rights are not revoked (they are immutable logs).
     */
    function revokeAsset(uint256 assetId) external {
        Asset storage a = assets[assetId];
        require(a.id != 0, "Asset does not exist");
        require(a.owner == msg.sender, "Only owner");
        require(a.active, "Already revoked");

        a.active = false;
        emit AssetRevoked(assetId);
    }

    /**
     * @dev Grava um derivado julgado (T-703; recibo da E14 §10.1). Só o operador: pelo R10 e pela
     *      fronteira do T-105, só o executor, que roda o Juiz por hash na CVM, afirma o veredito.
     *
     * O pai tem de ser um Model existente e ativo (derivado de derivado não entra: um nível só).
     * O derivado só nasce ativo com veredito Approved; qualquer outro veredito, inclusive Pending,
     * nasce inativo (C1). O contentHash do Asset é o derivativeHash; o preço é zero.
     *
     * @param info          Campos do recibo; info.parentId é o Model de que o derivado saiu
     * @param owner         Endereço de quem pediu o job (dono do derivado, não grava nada aqui)
     * @param title         Título para o catálogo
     * @param encryptedUri  CID do derivado cifrado e retido no IPFS (T-803)
     * @return id           Id do novo asset Derivative
     */
    function registerDerivative(
        DerivativeInfo calldata info,
        address owner,
        string calldata title,
        string calldata encryptedUri
    ) external onlyOperator returns (uint256 id) {
        Asset storage parent = assets[info.parentId];
        require(parent.id != 0, "Parent not found");
        require(parent.assetType == AssetType.Model, "Parent is not a model");
        require(parent.active, "Parent inactive");
        require(owner != address(0), "Owner required");
        require(bytes(title).length > 0, "Title required");
        require(info.derivativeHash != bytes32(0), "Derivative hash required");

        id = ++nextAssetId;
        bool approved = info.verdict == Verdict.Approved;

        Asset storage d = assets[id];
        d.id = id;
        d.assetType = AssetType.Derivative;
        d.owner = payable(owner);
        d.title = title;
        d.encryptedUri = encryptedUri;
        d.contentHash = info.derivativeHash;
        d.active = approved;
        derivatives[id] = info;

        emit AssetRegistered(id, AssetType.Derivative, owner, 0, false);
        emit DerivativeRegistered(id, info.parentId, info);
    }

    /**
     * @dev Retira um derivado (T-705, ciclo de vida do T-110): só o operador, porque o dono é o
     *      adversário e revokeAsset exige o dono. Zera active e marca a revogação como definitiva.
     *      Vale também para um derivado já inativo (o dono o desativou ou nasceu reprovado), para
     *      que a marca impeça a reativação.
     *
     * @param assetId  Asset do tipo Derivative
     * @param reason   Motivo registrado no evento (por exemplo, "judge-version-changed")
     */
    function revokeDerivative(uint256 assetId, string calldata reason) external onlyOperator {
        Asset storage a = assets[assetId];
        require(a.id != 0, "Asset does not exist");
        require(a.assetType == AssetType.Derivative, "Not a derivative");
        require(!derivativeRevoked[assetId], "Already revoked");

        derivativeRevoked[assetId] = true;
        a.active = false;
        emit DerivativeRevoked(assetId, reason, derivatives[assetId].judgeHash);
    }

    // ------------------------------------------------------------------------
    // Access acquisition (user pays dataset + app providers)
    // ------------------------------------------------------------------------

    /**
     * @dev Purchase execution rights to run `applicationId` over `datasetId`.
     *
     * The caller must send enough ETH to cover:
     *      assets[datasetId].price + assets[applicationId].price
     *
     * The contract:
     * - checks both assets exist and are active
     * - checks types (dataset vs application)
     * - marks <encryptedDatasetHash, encryptedApplicationHash, msg.sender> as having access
     * - pays both owners
     * - emits AccessPurchased event
     *
     * NOTE: Access rights are stored using encrypted hashes (IPFS CIDs), not asset IDs.
     * NOTE: This version does NOT implement "free via Bloom filter" logic on-chain.
     *       You can extend it later to use `bloomFilter` if you want exact DNAT semantics.
     */
    function purchaseAccess(
        uint256 datasetId,
        uint256 applicationId
    ) external payable nonReentrant {
        Asset storage d = assets[datasetId];
        Asset storage a = assets[applicationId];

        require(d.id != 0 && a.id != 0, "Asset not found");
        require(d.assetType == AssetType.Dataset, "datasetId is not dataset");
        require(a.assetType == AssetType.Application, "applicationId is not application");
        require(d.active && a.active, "Inactive asset");

        uint256 datasetPrice = d.price;
        uint256 appPrice = a.price;
        uint256 totalPrice = datasetPrice + appPrice;

        require(msg.value >= totalPrice, "Insufficient payment");

        // Mark access right using encrypted hashes (IPFS CIDs), not asset IDs
        // Access rights key: keccak256(encryptedDatasetHash, encryptedApplicationHash, user)
        bytes32 key = keccak256(
            abi.encodePacked(d.encryptedUri, a.encryptedUri, msg.sender)
        );
        accessRights[key] = true;

        emit AccessPurchased(
            datasetId,
            applicationId,
            msg.sender,
            datasetPrice,
            appPrice
        );

        // Pay dataset owner
        if (datasetPrice > 0) {
            (bool ok1, ) = d.owner.call{value: datasetPrice}("");
            require(ok1, "Dataset payment failed");
        }

        // Pay application owner
        if (appPrice > 0) {
            (bool ok2, ) = a.owner.call{value: appPrice}("");
            require(ok2, "Application payment failed");
        }

        // Refund any extra ETH sent by the user
        uint256 change = msg.value - totalPrice;
        if (change > 0) {
            (bool ok3, ) = payable(msg.sender).call{value: change}("");
            require(ok3, "Refund failed");
        }
    }

    // ------------------------------------------------------------------------
    // View helpers (Executor / off-chain indexers will use these)
    // ------------------------------------------------------------------------

    /**
     * @dev Check if a user has purchased the right to run an application over a dataset.
     *      Uses encrypted hashes (IPFS CIDs) to check access rights.
     *      The Executor can call this directly, or it can reconstruct the same information
     *      by scanning AccessPurchased events.
     *
     * @param user The user address to check
     * @param encryptedDatasetHash The IPFS CID of the encrypted dataset (e.g., "ipfs://Qm...")
     * @param encryptedApplicationHash The IPFS CID of the encrypted application (e.g., "ipfs://Qm...")
     */
    function hasAccess(
        address user,
        string calldata encryptedDatasetHash,
        string calldata encryptedApplicationHash
    ) external view returns (bool) {
        bytes32 key = keccak256(
            abi.encodePacked(encryptedDatasetHash, encryptedApplicationHash, user)
        );
        return accessRights[key];
    }

    /**
     * @dev Legacy function: Check access using asset IDs (for backward compatibility).
     *      This looks up the encrypted hashes from asset IDs and then checks access.
     */
    function hasAccessByIds(
        address user,
        uint256 datasetId,
        uint256 applicationId
    ) external view returns (bool) {
        Asset storage d = assets[datasetId];
        Asset storage a = assets[applicationId];
        
        require(d.id != 0 && a.id != 0, "Asset not found");
        
        bytes32 key = keccak256(
            abi.encodePacked(d.encryptedUri, a.encryptedUri, user)
        );
        return accessRights[key];
    }

    /**
     * @dev Convenience getter for asset details
     *      (Solidity can't return structs with dynamic types easily to all callers).
     */
    function getAsset(uint256 assetId)
        external
        view
        returns (
            AssetType assetType,
            address owner,
            string memory title,
            string memory description,
            string memory encryptedUri,
            string memory manifestUri,
            bytes32 contentHash,
            uint256 price,
            bytes memory bloomFilter,
            bool active
        )
    {
        Asset storage a = assets[assetId];
        require(a.id != 0, "Asset not found");

        return (
            a.assetType,
            a.owner,
            a.title,
            a.description,
            a.encryptedUri,
            a.manifestUri,
            a.contentHash,
            a.price,
            a.bloomFilter,
            a.active
        );
    }

    /**
     * @dev O derivado pode ser usado agora? (T-707, cascata preguiçosa, E14 §11). Ativo, aprovado,
     *      não revogado pelo operador e com o pai ativo. Revogar o pai derruba todos os filhos de uma
     *      vez sem laço sobre eles (gás constante): o estado efetivo de cada filho é lido aqui, e
     *      quem serve ou vende o derivado (API, executor) tem de consultar esta função, não só
     *      getAsset().active, que guarda o estado próprio do derivado.
     */
    function isDerivativeUsable(uint256 assetId) external view returns (bool) {
        Asset storage a = assets[assetId];
        require(a.id != 0, "Asset not found");
        require(a.assetType == AssetType.Derivative, "Not a derivative");
        DerivativeInfo storage info = derivatives[assetId];
        return a.active
            && info.verdict == Verdict.Approved
            && !derivativeRevoked[assetId]
            && assets[info.parentId].active;
    }

    /**
     * @dev Campos do derivado (T-104). Reverte se o asset não existe ou não é Derivative.
     */
    function getDerivative(uint256 assetId) external view returns (DerivativeInfo memory) {
        Asset storage a = assets[assetId];
        require(a.id != 0, "Asset not found");
        require(a.assetType == AssetType.Derivative, "Not a derivative");
        return derivatives[assetId];
    }

    // Accept stray ETH if needed (e.g., manual top-ups, though not required)
    receive() external payable {}
    fallback() external payable {}
}
