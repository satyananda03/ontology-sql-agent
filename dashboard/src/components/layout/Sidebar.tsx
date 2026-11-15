// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useId, useState } from "react";
import { matchPath, NavLink, useLocation } from "react-router-dom";
import {
  BookA,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  Database,
  FlaskConical,
  Library,
  Lightbulb,
  type LucideIcon,
  Network,
  Plug,
  Search,
  Server,
  Settings,
  Workflow,
} from "lucide-react";

interface NavItem {
  to: string;
  label: string;
  /** One line under the label saying what the page is for. */
  hint: string;
  icon: LucideIcon;
}

interface NavGroupDef {
  title: string;
  icon: LucideIcon;
  items: NavItem[];
}

const NAV_GROUPS: NavGroupDef[] = [
  {
    title: "Review",
    icon: ClipboardCheck,
    items: [
      { to: "/terms", label: "Business Terms", hint: "Konsep bisnis hasil kompilasi", icon: BookOpen },
      { to: "/catalog", label: "Katalog", hint: "Tabel dan kolom sumber", icon: Database },
      { to: "/search", label: "Pencarian", hint: "Cari term dan katalog", icon: Search },
    ],
  },
  {
    title: "Pengetahuan",
    icon: Library,
    items: [
      { to: "/glossary", label: "Glossary", hint: "Istilah dan singkatan bisnis", icon: BookA },
      { to: "/analyses", label: "Few-shot examples", hint: "Contoh pertanyaan dan SQL", icon: Lightbulb },
      { to: "/knowledge-graph", label: "Knowledge Graph", hint: "Peta relasi ontologi", icon: Network },
    ],
  },
  {
    title: "Sistem",
    icon: Server,
    items: [
      { to: "/connections", label: "Koneksi", hint: "Database sumber", icon: Plug },
      { to: "/settings", label: "Pengaturan", hint: "Operasi dan konfigurasi", icon: Settings },
      { to: "/playground", label: "Playground", hint: "Uji agent", icon: FlaskConical },
    ],
  },
];

const COLLAPSED_KEY = "sidebar-collapsed";
const NAV_ID = "sidebar-nav";

/** Remembered per browser; storage can be unavailable (private mode, blocked site data). */
function readCollapsed(): boolean {
  try {
    return localStorage.getItem(COLLAPSED_KEY) === "true";
  } catch {
    return false;
  }
}

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(readCollapsed);

  useEffect(() => {
    try {
      localStorage.setItem(COLLAPSED_KEY, String(collapsed));
    } catch {
      // Not remembered: the sidebar still works for this visit.
    }
  }, [collapsed]);

  return (
    <aside className={collapsed ? "sidebar collapsed" : "sidebar"}>
      <div className="brand">
        <span className="brand-logo" aria-hidden="true">
          <Workflow size={22} />
        </span>
        <span className="brand-text">
          <strong>Database Ontology</strong>
          <span>Semantic Layer for SQL Agent</span>
        </span>
      </div>
      <nav id={NAV_ID} className="nav" aria-label="Navigasi utama">
        {NAV_GROUPS.map((group) => (
          <NavGroup key={group.title} group={group} collapsed={collapsed} />
        ))}
      </nav>
      <button
        className="sidebar-toggle"
        onClick={() => setCollapsed((c) => !c)}
        aria-controls={NAV_ID}
        aria-expanded={!collapsed}
        aria-label={collapsed ? "Buka sidebar" : "Tutup sidebar"}
      >
        {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
      </button>
    </aside>
  );
}

/**
 * A group card that expands to its pages. It opens on its own when it holds the
 * current page, and names that page under its title. Collapsed, only the page icons show.
 */
function NavGroup({ group: { title, icon: Icon, items }, collapsed }: { group: NavGroupDef; collapsed: boolean }) {
  const { pathname } = useLocation();
  const current = items.find((item) => matchPath({ path: item.to, end: false }, pathname));
  const [open, setOpen] = useState(!!current);
  const listId = useId();

  useEffect(() => {
    if (current) setOpen(true);
  }, [current]);

  if (collapsed)
    return (
      <div className="nav-group">
        {items.map((item) => (
          <PageLink key={item.to} item={item} iconOnly />
        ))}
      </div>
    );

  return (
    <div className="nav-group">
      <button
        className={current ? "nav-group-card active" : "nav-group-card"}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls={listId}
      >
        <Icon className="nav-icon" size={22} aria-hidden="true" />
        <span className="nav-text">
          <span className="nav-label">{title}</span>
          {current && <span className="nav-hint">{current.label}</span>}
        </span>
        <ChevronRight className={open ? "nav-chevron open" : "nav-chevron"} size={18} aria-hidden="true" />
      </button>
      {open && (
        <ul id={listId} className="nav-pages">
          {items.map((item) => (
            <li key={item.to}>
              <PageLink item={item} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** A page link: icon, label and hint, or the icon alone (named by tooltip and aria-label) in the collapsed rail. */
function PageLink({ item: { to, label, hint, icon: Icon }, iconOnly = false }: { item: NavItem; iconOnly?: boolean }) {
  return (
    <NavLink
      to={to}
      className={iconOnly ? "nav-rail-link" : "nav-page"}
      title={iconOnly ? label : undefined}
      aria-label={iconOnly ? label : undefined}
    >
      <Icon size={iconOnly ? 22 : 18} aria-hidden="true" />
      {!iconOnly && (
        <span className="nav-text">
          {label}
          <span className="nav-hint">{hint}</span>
        </span>
      )}
    </NavLink>
  );
}
