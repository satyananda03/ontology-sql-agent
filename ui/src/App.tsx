// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import Analyses from "./pages/Analyses";
import Catalog from "./pages/Catalog";
import Connections from "./pages/Connections";
import Glossary from "./pages/Glossary";
import Playground from "./pages/Playground";
import Search from "./pages/Search";
import Settings from "./pages/Settings";
import { TermDetail, TermList } from "./pages/Terms";
import { Toaster } from "./ui";

const NAV = [
  ["Review", [["/terms", "Terms"], ["/catalog", "Katalog"], ["/search", "Pencarian"]]],
  ["Pengetahuan", [["/glossary", "Glossary"], ["/analyses", "Custom analyses"]]],
  ["Sistem", [["/connections", "Koneksi"], ["/settings", "Pengaturan"], ["/playground", "Playground"]]],
] as const;

export default function App() {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          Ontology <span>SQL</span> Agent
        </div>
        <nav className="nav" aria-label="Navigasi utama">
          {NAV.map(([group, links]) => (
            <div key={group} style={{ display: "contents" }}>
              <div className="group">{group}</div>
              {links.map(([to, label]) => (
                <NavLink key={to} to={to}>
                  {label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/terms" replace />} />
          <Route path="/terms" element={<TermList />} />
          <Route path="/terms/:id" element={<TermDetail />} />
          <Route path="/catalog" element={<Catalog />} />
          <Route path="/search" element={<Search />} />
          <Route path="/glossary" element={<Glossary />} />
          <Route path="/analyses" element={<Analyses />} />
          <Route path="/connections" element={<Connections />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/playground" element={<Playground />} />
          <Route path="*" element={<Navigate to="/terms" replace />} />
        </Routes>
      </main>
      <Toaster />
    </div>
  );
}
