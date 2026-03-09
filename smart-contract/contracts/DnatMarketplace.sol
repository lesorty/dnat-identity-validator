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

    enum AssetType {
        Dataset,
        Application
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

    // Accept stray ETH if needed (e.g., manual top-ups, though not required)
    receive() external payable {}
    fallback() external payable {}
}
