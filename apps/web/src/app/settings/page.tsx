import SettingsPageClient from "@/features/settings/settings-page-client";
import { getPublicApiConfig } from "@/lib/config/public-env";

export default function SettingsPage() {
  const config = getPublicApiConfig();
  return (
    <SettingsPageClient
      baseUrl={config.status === "configured" ? config.baseUrl : null}
    />
  );
}
