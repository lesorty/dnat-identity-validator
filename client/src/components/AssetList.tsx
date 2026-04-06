"use client";

import { useMemo } from "react";
import {
  Box,
  Typography,
  CircularProgress,
  Alert,
  Paper,
  Stack,
} from "@mui/material";
import { useAssetIds } from "@/hooks/useAssets";
import { useAsset } from "@/hooks/useContract";
import { assetFromContractData } from "@/hooks/useAssets";
import AssetCard from "./AssetCard";

// Component to fetch and display a single asset
function AssetItem({ assetId }: { assetId: number }) {
  const { data, isLoading } = useAsset(assetId);
  
  if (isLoading) return null;
  if (!data) return null;
  
  const asset = assetFromContractData(assetId, data);

  const isDataset = asset.assetType === 0;

  return (
    <Box sx={{ gridColumn: { xs: "1 / -1", md: isDataset ? "1 / 2" : "2 / 3" } }}>
      <AssetCard asset={asset} />
    </Box>
  );
}

export default function AssetList() {
  const { assetIds, isLoading, error } = useAssetIds();

  // Limit to first 20 assets to avoid too many requests
  const displayedIds = useMemo(() => assetIds.slice(0, 20), [assetIds]);

  return (
    <Box>
      <Box
        sx={{
          mb: 3,
          p: 3,
          borderRadius: 4,
          border: "1px solid",
          borderColor: "divider",
          background:
            "radial-gradient(circle at top left, rgba(21, 101, 192, 0.12) 0%, rgba(255,255,255,0.95) 58%)",
        }}
      >
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          Asset Marketplace
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
          Datasets are listed on the left, and applications are listed on the right.
        </Typography>
      </Box>

      {isLoading && (
        <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Error loading assets: {error?.message || "Unknown error"}
        </Alert>
      )}

      {!isLoading && !error && displayedIds.length === 0 && (
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <Typography variant="h6" color="text.secondary">
            No assets found
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Be the first to register an asset!
          </Typography>
        </Paper>
      )}

      {!isLoading && displayedIds.length > 0 && (
        <Stack spacing={2}>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
              gap: 2,
              mb: 1,
            }}
          >
            <Paper
              elevation={0}
              sx={{
                p: 2,
                borderRadius: 3,
                border: "1px solid",
                borderColor: "primary.light",
                backgroundColor: "rgba(25, 118, 210, 0.06)",
              }}
            >
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Datasets
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Structured data assets
              </Typography>
            </Paper>
            <Paper
              elevation={0}
              sx={{
                p: 2,
                borderRadius: 3,
                border: "1px solid",
                borderColor: "secondary.light",
                backgroundColor: "rgba(156, 39, 176, 0.06)",
              }}
            >
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Applications
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Executable models and scripts
              </Typography>
            </Paper>
          </Box>

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
              gap: 3,
              alignItems: "start",
            }}
          >
            {displayedIds.map((id) => (
              <AssetItem key={id} assetId={id} />
            ))}
          </Box>
        </Stack>
      )}
    </Box>
  );
}
