// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { PageHeader } from "@/components/layout";
import { GeneralSettings } from "@/features/settings/components/GeneralSettings";
import { ModelTransferPanel } from "@/features/settings/components/ModelTransferPanel";
import { OperationsPanel } from "@/features/settings/components/OperationsPanel";

export default function SettingsPage() {
  return (
    <>
      <PageHeader title="Pengaturan">Perubahan berlaku pada proses berikutnya tanpa restart.</PageHeader>
      <OperationsPanel />
      <GeneralSettings />
      <ModelTransferPanel />
    </>
  );
}
