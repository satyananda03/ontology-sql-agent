// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Loading } from "@/components/ui";
import AnalysesPage from "@/pages/AnalysesPage";
import AppLayout from "@/pages/AppLayout";
import CatalogPage from "@/pages/CatalogPage";
import ConnectionsPage from "@/pages/ConnectionsPage";
import GlossaryPage from "@/pages/GlossaryPage";
import PlaygroundPage from "@/pages/PlaygroundPage";
import SearchPage from "@/pages/SearchPage";
import SettingsPage from "@/pages/SettingsPage";
import TermDetailPage from "@/pages/TermDetailPage";
import TermListPage from "@/pages/TermListPage";

// Lazy: sigma and graphology are heavy, and only this page needs them.
const KnowledgeGraphPage = lazy(() => import("@/pages/KnowledgeGraphPage"));

export function AppRouter() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/terms" replace />} />
          <Route path="/terms" element={<TermListPage />} />
          <Route path="/terms/:id" element={<TermDetailPage />} />
          <Route path="/catalog" element={<CatalogPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/glossary" element={<GlossaryPage />} />
          <Route path="/analyses" element={<AnalysesPage />} />
          <Route
            path="/knowledge-graph"
            element={
              <Suspense fallback={<Loading />}>
                <KnowledgeGraphPage />
              </Suspense>
            }
          />
          <Route path="/connections" element={<ConnectionsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/playground" element={<PlaygroundPage />} />
          <Route path="*" element={<Navigate to="/terms" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
