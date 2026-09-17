import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const API_TARGET = process.env.SENTINEL_API || "http://127.0.0.1:8100";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": { target: API_TARGET, changeOrigin: false, ws: false },
      "/ws": { target: API_TARGET.replace(/^http/, "ws"), ws: true },
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 5173,
  },
});