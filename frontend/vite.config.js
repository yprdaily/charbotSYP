import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
  plugins: [react()],
  base: "./",
  server: { host: "127.0.0.1", strictPort: true, port: 5173 },
  preview: { host: "127.0.0.1", strictPort: true },
  build: {
    outDir: path.resolve(__dirname, "../extension/widget"),
    emptyOutDir: true,
  },
});
