import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: "dist",
    sourcemap: false,
  },
  server: {
    // Proxy /data/* to a local mock file during development
    proxy: {
      "/data": {
        target: "http://localhost:5173",
        rewrite: () => "/mock-data.json",
      },
    },
  },
});
