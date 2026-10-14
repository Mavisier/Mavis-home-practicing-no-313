import { fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const root = fileURLToPath(new URL("..", import.meta.url));
  const env = { ...loadEnv(mode, root, ""), ...process.env };
  const proxy = {
    target: env.API_PROXY_TARGET || "http://127.0.0.1:8000",
    changeOrigin: true,
    headers: { "X-Demo-Token": env.DEMO_REQUESTER_TOKEN || "" },
  };
  return {
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        "/api/actions": {
          ...proxy,
          headers: {
            ...proxy.headers,
            "X-Demo-Approver-Token": env.DEMO_APPROVER_TOKEN || "",
          },
        },
        "/api": proxy,
        "/health": proxy,
      },
    },
  };
});
