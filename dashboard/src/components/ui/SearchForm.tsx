// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState, type ReactNode } from "react";

interface SearchFormProps {
  /** The query currently applied, usually read from the URL. */
  value: string;
  onSearch: (query: string) => void;
  placeholder: string;
  label: string;
  /** Characters required before Search is enabled. */
  minLength?: number;
  autoFocus?: boolean;
  children?: ReactNode;
}

/** A search box that applies its query only on submit. */
export function SearchForm({ value, onSearch, placeholder, label, minLength = 0, autoFocus, children }: SearchFormProps) {
  const [draft, setDraft] = useState(value);
  return (
    <form
      className="row"
      onSubmit={(e) => {
        e.preventDefault();
        onSearch(draft.trim());
      }}
    >
      <input
        type="search"
        className="narrow"
        placeholder={placeholder}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        aria-label={label}
        autoFocus={autoFocus}
      />
      <button type="submit" className="primary" disabled={draft.trim().length < minLength}>
        Cari
      </button>
      {children}
    </form>
  );
}
