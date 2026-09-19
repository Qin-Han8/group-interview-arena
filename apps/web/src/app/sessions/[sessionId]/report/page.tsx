import { getPublicApiConfig } from "@/lib/config/public-env";
import ReportPageClient from "@/features/reports/report-page-client";

export default async function ReportPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  const config = getPublicApiConfig();
  return (
    <ReportPageClient
      baseUrl={config.status === "configured" ? config.baseUrl : null}
      sessionId={sessionId}
    />
  );
}
