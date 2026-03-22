import { createTheme } from "@mui/material/styles";

const AWS_ORANGE = "#FF9900";
const AWS_DARK = "#232F3E";
const AWS_DARK_LIGHT = "#37475A";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: AWS_DARK,
      light: AWS_DARK_LIGHT,
      contrastText: "#ffffff",
    },
    secondary: {
      main: AWS_ORANGE,
      contrastText: "#000000",
    },
    background: {
      default: "#f4f6f8",
      paper: "#ffffff",
    },
  },
  typography: {
    fontFamily:
      '"Amazon Ember", "Inter", "Helvetica Neue", Arial, sans-serif',
    h4: {
      fontWeight: 700,
    },
    h6: {
      fontWeight: 600,
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow:
            "0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)",
          "&:hover": {
            boxShadow:
              "0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1)",
          },
          transition: "box-shadow 0.2s ease-in-out",
        },
      },
    },
  },
});

export default theme;
