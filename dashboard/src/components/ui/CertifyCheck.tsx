// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

interface CertifyCheckProps {
  checked: boolean | null | undefined;
  onChange: (value: boolean) => void;
  disabled?: boolean;
  label?: string;
}

export function CertifyCheck({ checked, onChange, disabled, label = "Certified" }: CertifyCheckProps) {
  return (
    <label className="check">
      <input type="checkbox" checked={!!checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
      {label}
    </label>
  );
}
