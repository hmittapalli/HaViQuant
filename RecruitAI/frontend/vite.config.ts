import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: { rollupOptions: { input: { workspace: "index.html", world: "world.html", invite: "invite.html" } } },
  server: {
    port: 5173,
    host: "127.0.0.1",
  },
});
