import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// If SAFECOMMENT_API_KEY is set, the dashboard sends it with every API call.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        headers: { "X-API-Key": process.env.SAFECOMMENT_API_KEY || "" },
      },
    },
  },
});
