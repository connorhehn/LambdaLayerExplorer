import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import SearchIcon from "@mui/icons-material/Search";
import IconButton from "@mui/material/IconButton";
import ClearIcon from "@mui/icons-material/Clear";

interface Props {
  value: string;
  onChange: (v: string) => void;
  resultCount: number;
  totalCount: number;
}

export default function SearchBar({ value, onChange, resultCount, totalCount }: Props) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 3 }}>
      <TextField
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search layers or packages…"
        size="small"
        fullWidth
        sx={{ maxWidth: 480, bgcolor: "background.paper", borderRadius: 1 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon color="action" />
            </InputAdornment>
          ),
          endAdornment: value ? (
            <InputAdornment position="end">
              <IconButton size="small" onClick={() => onChange("")} edge="end">
                <ClearIcon fontSize="small" />
              </IconButton>
            </InputAdornment>
          ) : null,
        }}
      />
      {value && (
        <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: "nowrap" }}>
          {resultCount} of {totalCount}
        </Typography>
      )}
    </Box>
  );
}
