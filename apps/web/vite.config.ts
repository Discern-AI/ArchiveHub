/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const API = process.env.ARCHIVEHUB_API_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // Same-origin in development: cookies and CSRF work without CORS.
    proxy: {
      "/api": { target: API, changeOrigin: false },
      "/_allauth": { target: API, changeOrigin: false },
      "/admin": { target: API, changeOrigin: false },
      "/static": { target: API, changeOrigin: false },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
