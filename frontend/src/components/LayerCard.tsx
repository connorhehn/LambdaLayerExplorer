import { useState } from "react";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardActions from "@mui/material/CardActions";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Collapse from "@mui/material/Collapse";
import Divider from "@mui/material/Divider";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Tooltip from "@mui/material/Tooltip";
import IconButton from "@mui/material/IconButton";
import Alert from "@mui/material/Alert";
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";

import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import InventoryIcon from "@mui/icons-material/Inventory";
import SearchIcon from "@mui/icons-material/Search";

import { Layer, Package } from "../types";

interface Props {
  layer: Layer;
  search: string;
}

function highlight(text: string, query: string): React.ReactNode {
  if (!query) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark style={{ background: "#ffe082", borderRadius: 2, padding: "0 1px" }}>
        {text.slice(idx, idx + query.length)}
      </mark>
      {text.slice(idx + query.length)}
    </>
  );
}

function formatBytes(bytes: number): string {
  if (!bytes) return "";
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function matchesPackage(pkg: Package, q: string): boolean {
  if (!q) return true;
  return (
    pkg.name.toLowerCase().includes(q) ||
    pkg.summary.toLowerCase().includes(q)
  );
}

export default function LayerCard({ layer, search }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const [pkgSearch, setPkgSearch] = useState("");

  const handleCopyArn = () => {
    navigator.clipboard.writeText(layer.latest_version_arn);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const filteredPackages = layer.packages.filter((p) =>
    matchesPackage(p, pkgSearch.toLowerCase())
  );

  return (
    <Card sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <CardContent sx={{ flex: 1 }}>
        {/* Layer name + version badge */}
        <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1, mb: 1 }}>
          <Typography
            variant="h6"
            component="h2"
            sx={{ flex: 1, fontSize: "0.95rem", wordBreak: "break-all" }}
          >
            {highlight(layer.name, search)}
          </Typography>
          <Chip
            label={`v${layer.latest_version}`}
            size="small"
            color="secondary"
            sx={{ flexShrink: 0, mt: 0.3 }}
          />
        </Box>

        {/* Publisher */}
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          {highlight(layer.publisher, search)}
        </Typography>

        {/* Description */}
        {layer.description && (
          <Typography variant="body2" sx={{ mb: 1.5, color: "text.primary" }}>
            {highlight(layer.description, search)}
          </Typography>
        )}

        {/* Runtimes */}
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mb: 1.5 }}>
          {layer.compatible_runtimes.map((rt) => (
            <Chip
              key={rt}
              label={rt}
              size="small"
              variant="outlined"
              sx={{ fontSize: "0.7rem", height: 20 }}
            />
          ))}
          {layer.compatible_architectures?.map((arch) => (
            <Chip
              key={arch}
              label={arch}
              size="small"
              variant="outlined"
              color="primary"
              sx={{ fontSize: "0.7rem", height: 20 }}
            />
          ))}
        </Box>

        {/* ARN */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            bgcolor: "grey.50",
            borderRadius: 1,
            px: 1,
            py: 0.5,
            gap: 0.5,
            border: "1px solid",
            borderColor: "grey.200",
          }}
        >
          <Typography
            variant="caption"
            sx={{
              flex: 1,
              fontFamily: "monospace",
              fontSize: "0.65rem",
              wordBreak: "break-all",
              color: "text.secondary",
            }}
          >
            {layer.latest_version_arn}
          </Typography>
          <Tooltip title={copied ? "Copied!" : "Copy ARN"}>
            <IconButton size="small" onClick={handleCopyArn}>
              <ContentCopyIcon sx={{ fontSize: 14 }} />
            </IconButton>
          </Tooltip>
        </Box>

        {/* Size + package count summary */}
        <Box sx={{ display: "flex", gap: 2, mt: 1.5 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <InventoryIcon sx={{ fontSize: 14, color: "text.secondary" }} />
            <Typography variant="caption" color="text.secondary">
              {layer.package_count} package{layer.package_count !== 1 ? "s" : ""}
            </Typography>
          </Box>
          {layer.layer_size_bytes > 0 && (
            <Typography variant="caption" color="text.secondary">
              {formatBytes(layer.layer_size_bytes)} compressed
            </Typography>
          )}
        </Box>

        {layer.error && (
          <Alert severity="warning" sx={{ mt: 1.5, fontSize: "0.75rem" }}>
            Inspection failed: {layer.error}
          </Alert>
        )}
      </CardContent>

      <Divider />

      <CardActions sx={{ justifyContent: "space-between", px: 2 }}>
        <Button
          size="small"
          endIcon={expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          onClick={() => setExpanded((v) => !v)}
          disabled={layer.package_count === 0}
        >
          {expanded ? "Hide" : "Show"} packages
        </Button>
        <Tooltip title="View on AWS docs">
          <IconButton
            size="small"
            href="https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html"
            target="_blank"
            rel="noopener noreferrer"
            component="a"
          >
            <OpenInNewIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </CardActions>

      {/* Expandable package list */}
      <Collapse in={expanded} timeout="auto" unmountOnExit>
        <Divider />
        <Box sx={{ px: 2, pt: 1.5, pb: 1 }}>
          <TextField
            value={pkgSearch}
            onChange={(e) => setPkgSearch(e.target.value)}
            placeholder="Filter packages…"
            size="small"
            fullWidth
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon sx={{ fontSize: 16 }} color="action" />
                </InputAdornment>
              ),
            }}
            sx={{ mb: 1 }}
          />
          <TableContainer sx={{ maxHeight: 340 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600, fontSize: "0.75rem" }}>Package</TableCell>
                  <TableCell sx={{ fontWeight: 600, fontSize: "0.75rem" }}>Version</TableCell>
                  <TableCell sx={{ fontWeight: 600, fontSize: "0.75rem" }}>Summary</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredPackages.map((pkg) => (
                  <TableRow key={pkg.name} hover>
                    <TableCell sx={{ fontSize: "0.75rem" }}>
                      {pkg.home_page ? (
                        <a
                          href={pkg.home_page}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: "inherit" }}
                        >
                          {highlight(pkg.name, search || pkgSearch)}
                        </a>
                      ) : (
                        highlight(pkg.name, search || pkgSearch)
                      )}
                    </TableCell>
                    <TableCell sx={{ fontSize: "0.75rem", whiteSpace: "nowrap" }}>
                      <code>{pkg.version}</code>
                    </TableCell>
                    <TableCell sx={{ fontSize: "0.75rem", color: "text.secondary" }}>
                      {highlight(pkg.summary, search || pkgSearch)}
                    </TableCell>
                  </TableRow>
                ))}
                {filteredPackages.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3} sx={{ color: "text.secondary", fontSize: "0.75rem" }}>
                      No packages match.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      </Collapse>
    </Card>
  );
}
