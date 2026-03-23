import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Link from "@mui/material/Link";

export default function Footer() {
  return (
    <Box
      component="footer"
      sx={{
        mt: 8,
        py: 3,
        borderTop: 1,
        borderColor: "divider",
        textAlign: "center",
      }}
    >
      <Typography variant="body2" color="text.secondary">
        Built by{" "}
        <Link href="https://www.linkedin.com/in/connor-hehn/" target="_blank" rel="noopener" underline="hover" color="inherit">
          Connor Hehn
        </Link>
        {" · "}
        <Link href="https://github.com/connorhehn" target="_blank" rel="noopener" underline="hover" color="inherit">
          GitHub
        </Link>
      </Typography>
    </Box>
  );
}
