import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Box from "@mui/material/Box";
import LayersIcon from "@mui/icons-material/Layers";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import Tooltip from "@mui/material/Tooltip";

interface Props {
  updatedAt: string | null;
  layerCount: number | null;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

export default function Header({ updatedAt, layerCount }: Props) {
  return (
    <AppBar position="static" elevation={0} sx={{ bgcolor: "primary.main" }}>
      <Toolbar sx={{ gap: 2, flexWrap: "wrap", py: 1 }}>
        <LayersIcon sx={{ color: "secondary.main", fontSize: 32 }} />

        <Box sx={{ flex: 1 }}>
          <Typography variant="h6" component="h1" sx={{ lineHeight: 1.2 }}>
            AWS Lambda Layers Explorer
          </Typography>
          <Typography variant="caption" sx={{ opacity: 0.75 }}>
            Catalogue of packages inside AWS-owned public Lambda layers
          </Typography>
        </Box>

        <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
          {layerCount !== null && (
            <Chip
              label={`${layerCount} layer${layerCount !== 1 ? "s" : ""}`}
              size="small"
              sx={{ bgcolor: "secondary.main", color: "secondary.contrastText" }}
            />
          )}
          {updatedAt && (
            <Tooltip title={`Data collected: ${formatDate(updatedAt)}`}>
              <Chip
                icon={<AccessTimeIcon sx={{ fontSize: "0.9rem !important" }} />}
                label={`Updated ${formatDate(updatedAt)}`}
                size="small"
                variant="outlined"
                sx={{ color: "white", borderColor: "rgba(255,255,255,0.4)" }}
              />
            </Tooltip>
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
}
