import { useState, useEffect, useMemo } from "react";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Grid";

import { LayersData, Layer } from "./types";
import Header from "./components/Header";
import SearchBar from "./components/SearchBar";
import LayerCard from "./components/LayerCard";

function matchesSearch(layer: Layer, query: string): boolean {
  if (!query) return true;
  const q = query.toLowerCase();
  if (layer.name.toLowerCase().includes(q)) return true;
  if (layer.publisher.toLowerCase().includes(q)) return true;
  if (layer.description.toLowerCase().includes(q)) return true;
  return layer.packages.some(
    (p) =>
      p.name.toLowerCase().includes(q) ||
      p.summary.toLowerCase().includes(q)
  );
}

export default function App() {
  const [data, setData] = useState<LayersData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetch("/data/layers.json")
      .then((res) => {
        if (!res.ok) {
          if (res.status === 403 || res.status === 404) {
            throw new Error("NO_DATA");
          }
          throw new Error(`HTTP ${res.status}`);
        }
        return res.json();
      })
      .then((json: LayersData) => {
        setData(json);
        setLoading(false);
      })
      .catch((err: Error) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const filteredLayers = useMemo(() => {
    if (!data) return [];
    return data.layers.filter((l) => matchesSearch(l, search));
  }, [data, search]);

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <Header updatedAt={data?.updated_at ?? null} layerCount={data?.layer_count ?? null} />

      <Container maxWidth="xl" sx={{ py: 4 }}>
        {/* Search */}
        {data && (
          <SearchBar
            value={search}
            onChange={setSearch}
            resultCount={filteredLayers.length}
            totalCount={data.layers.length}
          />
        )}

        {/* Loading */}
        {loading && (
          <Box sx={{ display: "flex", justifyContent: "center", mt: 8 }}>
            <CircularProgress size={48} />
          </Box>
        )}

        {/* No data yet (first deploy before Lambda has run) */}
        {!loading && error === "NO_DATA" && (
          <Alert severity="info" sx={{ mt: 4 }}>
            Layer data hasn't been collected yet. Invoke the Orchestrator Lambda
            manually, or wait for the weekly scheduled run.
          </Alert>
        )}

        {/* Other errors */}
        {!loading && error && error !== "NO_DATA" && (
          <Alert severity="error" sx={{ mt: 4 }}>
            Failed to load layer data: {error}
          </Alert>
        )}

        {/* Results */}
        {!loading && data && filteredLayers.length === 0 && (
          <Typography color="text.secondary" sx={{ mt: 4, textAlign: "center" }}>
            No layers match your search.
          </Typography>
        )}

        {!loading && data && filteredLayers.length > 0 && (
          <Grid container spacing={3} sx={{ mt: 1 }}>
            {filteredLayers.map((layer) => (
              <Grid item xs={12} md={6} xl={4} key={layer.arn}>
                <LayerCard layer={layer} search={search} />
              </Grid>
            ))}
          </Grid>
        )}
      </Container>
    </Box>
  );
}
