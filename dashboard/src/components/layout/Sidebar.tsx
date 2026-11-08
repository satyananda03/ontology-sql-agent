// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { Fragment } from "react";
import { NavLink } from "react-router-dom";

const NAV_GROUPS = [
  { title: "Review", links: [["/terms", "Terms"], ["/catalog", "Katalog"], ["/search", "Pencarian"]] },
  {
    title: "Pengetahuan",
    links: [["/glossary", "Glossary"], ["/analyses", "Custom analyses"], ["/knowledge-graph", "Knowledge Graph"]],
  },
  { title: "Sistem", links: [["/connections", "Koneksi"], ["/settings", "Pengaturan"], ["/playground", "Playground"]] },
] as const;

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        Ontology <span>SQL</span> Agent
      </div>
      <nav className="nav" aria-label="Navigasi utama">
        {NAV_GROUPS.map(({ title, links }) => (
          <Fragment key={title}>
            <div className="group">{title}</div>
            {links.map(([to, label]) => (
              <NavLink key={to} to={to}>
                {label}
              </NavLink>
            ))}
          </Fragment>
        ))}
      </nav>
    </aside>
  );
}
