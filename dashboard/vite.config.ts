// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, "..", "");
  const backend = env.UI_BACKEND_URL || "http://127.0.0.1:3001";
  const proxy = { "/api": { target: backend } };
  return {
    // Tailwind serves the knowledge graph only; see styles/globals.css.
    plugins: [react(), tailwindcss()],
    resolve: { alias: { "@": "/src" } },
    server: { host: "127.0.0.1", port: 5173, strictPort: true, proxy },
    preview: { host: "127.0.0.1", port: 4173, strictPort: true, proxy },
  };
});
