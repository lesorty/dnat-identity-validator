"use client";

import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  Typography,
  Chip,
  Box,
  Button,
  CardActionArea,
  Skeleton,
} from "@mui/material";
import { formatEth, formatAddress, formatAssetType, formatHash } from "@/utils/formatting";
import Link from "next/link";
import { Asset } from "@/hooks/useAssets";
import AssetDetailModal from "./AssetDetailModal";
import { fetchFromIPFS, parseYAML } from "@/utils/ipfsUtils";

interface AssetCardProps {
  asset: Asset;
}

export default function AssetCard({ asset }: AssetCardProps) {
  const [detailOpen, setDetailOpen] = useState(false);
  const [manifestData, setManifestData] = useState<{ title?: string; description?: string }>({});
  const [isLoadingManifest, setIsLoadingManifest] = useState(true);

  useEffect(() => {
    let active = true;

    const loadManifest = async () => {
      try {
        const yamlContent = await fetchFromIPFS(asset.manifestUri);
        const parsed = parseYAML(yamlContent);
        if (!active) return;
        setManifestData({
          title: parsed.title || parsed.name,
          description: parsed.description,
        });
      } catch {
        if (!active) return;
        setManifestData({});
      } finally {
        if (active) {
          setIsLoadingManifest(false);
        }
      }
    };

    setIsLoadingManifest(true);
    loadManifest();

    return () => {
      active = false;
    };
  }, [asset.manifestUri]);

  return (
    <>
      <Card
        sx={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          borderRadius: 3,
          border: "1px solid",
          borderColor: "divider",
          boxShadow: "0 10px 30px rgba(5, 16, 31, 0.08)",
          background:
            "linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(248,251,255,0.96) 100%)",
        }}
      >
        <CardActionArea
          onClick={() => setDetailOpen(true)}
          sx={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "stretch" }}
        >
          <CardContent sx={{ flex: 1, width: "100%" }}>
            <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2, gap: 1 }}>
              <Typography variant="h6" component="div" sx={{ fontWeight: 700 }}>
                {manifestData.title || `Asset #${asset.id}`}
              </Typography>
              <Chip
                label={formatAssetType(asset.assetType)}
                color={asset.assetType === 0 ? "primary" : "secondary"}
                size="small"
              />
            </Box>

            {isLoadingManifest ? (
              <Box sx={{ mb: 2 }}>
                <Skeleton variant="text" width="80%" height={22} />
                <Skeleton variant="text" width="95%" />
              </Box>
            ) : manifestData.description ? (
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  mb: 2,
                  display: "-webkit-box",
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: "vertical",
                  overflow: "hidden",
                }}
              >
                {manifestData.description}
              </Typography>
            ) : null}

            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
              ID #{asset.id}
            </Typography>

            <Typography variant="body2" color="text.secondary" gutterBottom>
              Owner: {formatAddress(asset.owner)}
            </Typography>

            <Typography variant="body2" color="text.secondary" gutterBottom>
              Price: {formatEth(asset.price)} ETH
            </Typography>

            <Typography variant="body2" color="text.secondary" gutterBottom>
              Content Hash: {formatHash(asset.contentHash)}
            </Typography>

            <Typography variant="body2" color="text.secondary" gutterBottom>
              Encrypted URI: {asset.encryptedUri.substring(0, 30)}...
            </Typography>

            <Box sx={{ display: "flex", gap: 1, mt: 2 }}>
              <Chip
                label={asset.active ? "Active" : "Inactive"}
                color={asset.active ? "success" : "default"}
                size="small"
              />
              {asset.bloomFilter && asset.bloomFilter !== "0x" && (
                <Chip label="Has Bloom Filter" size="small" />
              )}
            </Box>

            <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: "block" }}>
              Click to view details
            </Typography>
          </CardContent>
        </CardActionArea>
        <Box sx={{ p: 2, pt: 0 }}>
          <Button
            variant="outlined"
            size="small"
            fullWidth
            component={Link}
            href={`/purchase?datasetId=${asset.assetType === 0 ? asset.id : ""}&applicationId=${asset.assetType === 1 ? asset.id : ""}`}
            onClick={(e) => e.stopPropagation()}
          >
            Use in Purchase
          </Button>
        </Box>
      </Card>
      <AssetDetailModal
        asset={asset}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
      />
    </>
  );
}
