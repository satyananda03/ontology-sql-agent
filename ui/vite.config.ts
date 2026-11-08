// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// The SQL agent route needs `x-api-key`. The proxy adds it from the repo's
// `.env` on the dev server, so the key never reaches the browser bundle.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, "..", "");
  const backend = env.UI_BACKEND_URL || "http://127.0.0.1:3001";
  const proxy = {
    "/api/sql-agent": {
      target: backend,
      headers: { "x-api-key": env.SQL_AGENT_API_KEY ?? "" },
    },
    "/api": { target: backend },
  };
  return {
    plugins: [react()],
    server: { host: "127.0.0.1", port: 5173, strictPort: true, proxy },
    preview: { host: "127.0.0.1", port: 4173, strictPort: true, proxy },
  };
});
