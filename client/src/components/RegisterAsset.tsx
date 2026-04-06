"use client";

import { useState } from "react";
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Divider,
  Chip,
} from "@mui/material";
import { CloudUpload } from "@mui/icons-material";
import { useContractWrite, useWaitForTransaction } from "@/hooks/useContract";
import { getErrorMessage } from "@/utils/errors";
import { calculateFileHash } from "@/utils/fileUtils";
import { objectToYAML } from "@/utils/yamlUtils";
import { generateEncryptionKey, encryptFile } from "@/utils/encryption";
import { uploadFileToIPFS, uploadToIPFS, checkIPFSConnection } from "@/utils/ipfsClient";
import { uploadKeyToCAS, generateSessionName, storeKeyLocally } from "@/services/cas";

interface ManifestData {
  title: string;
  name: string;
  description: string;
  version: string;
  author: string;
  // Application-specific fields
  framework?: string;
  dependencies?: string;
}

export default function RegisterAsset() {
  const [assetType, setAssetType] = useState<0 | 1>(0);
  const [assetFile, setAssetFile] = useState<File | null>(null);
  const [price, setPrice] = useState("");
  const [bloomFilter, setBloomFilter] = useState("");
  const [contentHash, setContentHash] = useState("");
  const [isCalculatingHash, setIsCalculatingHash] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState("");

  // Manifest fields
  const [manifest, setManifest] = useState<ManifestData>({
    title: "",
    name: "",
    description: "",
    version: "1.0.0",
    author: "",
    framework: "",
    dependencies: "",
  });

  const { write, hash, isPending, error } = useContractWrite();
  const { isLoading: isConfirming, isSuccess } = useWaitForTransaction(hash);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type based on asset type
    const fileName = file.name.toLowerCase();
    const fileExtension = fileName.split('.').pop();

    if (assetType === 0) {
      // Dataset must be CSV
      if (fileExtension !== 'csv') {
        alert("Datasets must be in CSV format. Please upload a .csv file.");
        e.target.value = ''; // Reset file input
        return;
      }
    } else {
      // Application must be Python (.py or .zip for Python projects)
      if (fileExtension !== 'py' && fileExtension !== 'zip') {
        alert("Applications must be Python files (.py) or Python project archives (.zip). Please upload a .py or .zip file.");
        e.target.value = ''; // Reset file input
        return;
      }
    }

    setAssetFile(file);
    setIsCalculatingHash(true);

    try {
      const hash = await calculateFileHash(file);
      setContentHash(hash);
    } catch (err) {
      console.error("Error calculating hash:", err);
      alert("Failed to calculate file hash");
    } finally {
      setIsCalculatingHash(false);
    }
  };

  const handleManifestChange = (field: keyof ManifestData, value: string) => {
    setManifest((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate file
    if (!assetFile) {
      alert("Please select an asset file");
      return;
    }

    // Validate required manifest fields
    if (!manifest.title || !manifest.description || !manifest.author) {
      alert("Please fill in all required manifest fields (title, description, author)");
      return;
    }

    // Validate content hash
    if (!contentHash || contentHash.length !== 66 || !contentHash.startsWith("0x")) {
      alert("Content hash is invalid. Please try uploading the file again.");
      return;
    }

    // Validate and convert price from ETH to Wei
    let priceWei: bigint;
    try {
      const priceValue = price || "0";
      const priceNum = parseFloat(priceValue);
      if (isNaN(priceNum) || priceNum < 0) {
        alert("Price must be a valid positive number in ETH");
        return;
      }
      // Convert ETH to Wei (1 ETH = 10^18 Wei)
      priceWei = BigInt(Math.floor(priceNum * 1e18));
    } catch {
      alert("Invalid price format. Please enter a valid number in ETH");
      return;
    }

    // Check IPFS connection
    setIsUploading(true);
    setUploadProgress("Checking IPFS connection...");
    
    const isIPFSConnected = await checkIPFSConnection();
    if (!isIPFSConnected) {
      alert(
        "IPFS node is not available. Please check:\n" +
        "1. IPFS is running: docker-compose ps\n" +
        "2. IPFS API is accessible: curl http://localhost:5001/api/v0/version\n" +
        "3. Check browser console for detailed error messages"
      );
      setIsUploading(false);
      return;
    }

    try {
      // Step 1: Generate encryption key K
      setUploadProgress("Generating encryption key...");
      const encryptionKey = await generateEncryptionKey();
      
      // Export key immediately to verify it's the same throughout
      const keyBytes = new Uint8Array(await crypto.subtle.exportKey("raw", encryptionKey));
      const keyBase64 = btoa(String.fromCharCode(...keyBytes));
      console.log("=== ENCRYPTION KEY GENERATED ===");
      console.log("Key (b64):", keyBase64);
      console.log("Key length:", keyBytes.length, "bytes");

      // Step 2: Encrypt the asset file
      setUploadProgress("Encrypting asset file...");
      const { encryptedBlob } = await encryptFile(assetFile, encryptionKey);
      console.log("Asset encrypted, size:", encryptedBlob.size, "bytes");
      console.log("Original file size:", assetFile.size, "bytes");
      console.log("Expected encrypted size:", 12 + assetFile.size + 16, "bytes (12 IV + data + 16 tag)");

      // Step 3: Upload encrypted asset to IPFS
      setUploadProgress("Uploading encrypted asset to IPFS...");
      const encryptedAssetCID = await uploadFileToIPFS(encryptedBlob);
      console.log("Encrypted asset uploaded to IPFS:", encryptedAssetCID);

      // Extract CID from encrypted asset URI (remove ipfs:// prefix for storage)
      const encryptedAssetHash = encryptedAssetCID.replace(/^ipfs:\/\//, "");

      // Step 4: Upload encryption key to CAS
      setUploadProgress("Uploading encryption key to CAS...");
      const assetTypeName = assetType === 0 ? "dataset" : "application";
      const sessionName = generateSessionName(assetTypeName, encryptedAssetHash);
      
      console.log("=== UPLOADING TO CAS ===");
      console.log("Session name:", sessionName);
      console.log("Key being uploaded (b64):", keyBase64);
      
      const casResult = await uploadKeyToCAS({
        sessionName,
        encryptionKey: keyBase64,
        assetType: assetTypeName,
        ipfsHash: encryptedAssetHash,
      });

      if (!casResult.success) {
        throw new Error(`CAS upload failed: ${casResult.error}`);
      }
      
      console.log("=== CAS UPLOAD SUCCESS ===");
      console.log("Session:", casResult.sessionName);
      // Store locally for reference
      storeKeyLocally(encryptedAssetHash, keyBase64, sessionName);

      // Step 5: Convert manifest to YAML and upload to IPFS
      setUploadProgress("Uploading manifest to IPFS...");
      const manifestYAML = objectToYAML(manifest);
      const manifestCID = await uploadToIPFS(manifestYAML);
      const manifestUri = `ipfs://${manifestCID}`;
      console.log("Manifest uploaded to IPFS:", manifestUri);

      // Use the hashes (CIDs) for blockchain storage
      const encryptedUri = `ipfs://${encryptedAssetHash}`;
      
      setUploadProgress("Registering on blockchain...");

    // Convert bloom filter to bytes (if provided)
    let bloomFilterBytes: `0x${string}` = "0x" as `0x${string}`;
    if (bloomFilter) {
      const cleanHex = bloomFilter.startsWith("0x") ? bloomFilter.slice(2) : bloomFilter;
      if (!/^[0-9a-fA-F]*$/.test(cleanHex)) {
        alert("Bloom filter must be valid hex");
        return;
      }
      bloomFilterBytes = `0x${cleanHex}` as `0x${string}`;
    }

      // Step 5: Register on blockchain with IPFS hashes
      setUploadProgress("Registering on blockchain...");
      await write("registerAsset", [
        assetType,
        encryptedUri,
        manifestUri,
        contentHash as `0x${string}`,
        priceWei,
        bloomFilterBytes,
      ]);
      
      setIsUploading(false);
      setUploadProgress("");
    } catch (err) {
      console.error("Error in registration process:", err);
      setIsUploading(false);
      setUploadProgress("");
      alert(`Registration failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  const isProcessing = isPending || isConfirming;

  return (
    <Paper sx={{ p: 4 }}>
      <Typography variant="h4" gutterBottom>
        Register Asset
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Register a new dataset or application in the marketplace
      </Typography>

      <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
        {/* Asset Type */}
        <FormControl fullWidth sx={{ mb: 3 }}>
          <InputLabel>Asset Type</InputLabel>
          <Select
            value={assetType}
            onChange={(e) => {
              const newType = e.target.value as 0 | 1;
              setAssetType(newType);
              // Reset file when type changes
              setAssetFile(null);
              setContentHash("");
            }}
            label="Asset Type"
          >
            <MenuItem value={0}>Dataset (CSV format)</MenuItem>
            <MenuItem value={1}>Application (Python)</MenuItem>
          </Select>
        </FormControl>

        <Divider sx={{ my: 3 }} />

        {/* File Upload */}
        <Typography variant="h6" gutterBottom>
          Asset File
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {assetType === 0
            ? "Upload a CSV file for your dataset"
            : "Upload a Python file (.py) or Python project archive (.zip) for your application"}
        </Typography>
        <Box sx={{ mb: 3 }}>
          <input
            accept={assetType === 0 ? ".csv" : ".py,.zip"}
            style={{ display: "none" }}
            id="asset-file-upload"
            type="file"
            onChange={handleFileChange}
            key={assetType} // Reset file input when asset type changes
          />
          <label htmlFor="asset-file-upload">
            <Button
              variant="outlined"
              component="span"
              startIcon={<CloudUpload />}
              sx={{ mb: 2 }}
            >
              Upload {assetType === 0 ? "CSV File" : "Python File/Project"}
            </Button>
          </label>
          {assetFile && (
            <Box sx={{ mt: 1 }}>
              <Chip label={assetFile.name} sx={{ mr: 1 }} />
              <Typography variant="body2" color="text.secondary" component="span">
                ({(assetFile.size / 1024).toFixed(2)} KB)
              </Typography>
            </Box>
          )}
          {isCalculatingHash && (
            <Box sx={{ mt: 1, display: "flex", alignItems: "center", gap: 1 }}>
              <CircularProgress size={16} />
              <Typography variant="body2" color="text.secondary">
                Calculating hash...
              </Typography>
            </Box>
          )}
          {contentHash && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Content Hash: <code>{contentHash}</code>
              </Typography>
            </Box>
          )}
        </Box>

        <Divider sx={{ my: 3 }} />

        {/* Manifest Form */}
        <Typography variant="h6" gutterBottom>
          Manifest Information
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Provide metadata about your asset
        </Typography>

        <TextField
          fullWidth
          label={assetType === 0 ? "Dataset Title *" : "Application Title *"}
          value={manifest.title}
          onChange={(e) => {
            const value = e.target.value;
            handleManifestChange("title", value);
            // Keep `name` for backward compatibility with existing manifest readers.
            handleManifestChange("name", value);
          }}
          required
          sx={{ mb: 2 }}
          placeholder={assetType === 0 ? "Customer Churn Dataset" : "Fraud Detection Model"}
        />

        <TextField
          fullWidth
          label="Description *"
          value={manifest.description}
          onChange={(e) => handleManifestChange("description", e.target.value)}
          required
          multiline
          rows={3}
          sx={{ mb: 2 }}
          placeholder="Describe your asset..."
        />

        <Box sx={{ display: "flex", gap: 2, mb: 2 }}>
          <TextField
            fullWidth
            label="Version"
            value={manifest.version}
            onChange={(e) => handleManifestChange("version", e.target.value)}
            sx={{ mb: 2 }}
            placeholder="1.0.0"
          />
          <TextField
            fullWidth
            label="Author *"
            value={manifest.author}
            onChange={(e) => handleManifestChange("author", e.target.value)}
            required
            sx={{ mb: 2 }}
            placeholder="Your name or organization"
          />
        </Box>

        {assetType === 1 && (
          // Application-specific fields (only for applications)
          <>
            <TextField
              fullWidth
              label="Framework"
              value={manifest.framework}
              onChange={(e) => handleManifestChange("framework", e.target.value)}
              sx={{ mb: 2 }}
              placeholder="TensorFlow, PyTorch, Scikit-learn, etc."
              helperText="Machine learning or data processing framework used"
            />
            <TextField
              fullWidth
              label="Dependencies"
              value={manifest.dependencies}
              onChange={(e) => handleManifestChange("dependencies", e.target.value)}
              sx={{ mb: 2 }}
              placeholder="Comma-separated list of dependencies (e.g., numpy, pandas, tensorflow)"
              helperText="Python packages required to run the application"
            />
          </>
        )}

        <Divider sx={{ my: 3 }} />

        {/* Pricing */}
        <Typography variant="h6" gutterBottom>
          Pricing
        </Typography>
        <TextField
          fullWidth
          label="Price (ETH) *"
          type="number"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          required
          sx={{ mb: 2 }}
          inputProps={{ min: "0", step: "0.001" }}
          helperText="Enter price in ETH (e.g., 0.01 for 0.01 ETH)"
        />

        {assetType === 0 && (
          <TextField
            fullWidth
            label="Bloom Filter (hex, optional)"
            value={bloomFilter}
            onChange={(e) => setBloomFilter(e.target.value)}
            sx={{ mb: 2 }}
            placeholder="0x..."
            helperText="Hex-encoded Bloom filter for whitelisted apps (datasets only)"
          />
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {getErrorMessage(error)}
          </Alert>
        )}

        {isSuccess && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Asset registered successfully! Transaction: {hash}
          </Alert>
        )}

        {uploadProgress && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <CircularProgress size={16} />
              <Typography variant="body2">{uploadProgress}</Typography>
            </Box>
          </Alert>
        )}

        <Button
          type="submit"
          variant="contained"
          fullWidth
          disabled={isProcessing || !assetFile || isCalculatingHash || isUploading}
          sx={{ mt: 2 }}
        >
          {isProcessing || isUploading ? (
            <>
              <CircularProgress size={20} sx={{ mr: 1 }} />
              {isUploading ? uploadProgress || "Uploading..." : isPending ? "Confirming..." : "Processing..."}
            </>
          ) : (
            "Register Asset"
          )}
        </Button>
      </Box>
    </Paper>
  );
}
