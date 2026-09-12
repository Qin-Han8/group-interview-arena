import { getPublicApiConfig } from "@/lib/config/public-env";
import ReportPageClient from "@/features/reports/report-page-client";

export default async function ReportPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  const config = getPublicApiConfig();
  if (config.status !== "configured")
    return (
      <main className="grid min-h-dvh place-items-center">
        <p>报告服务暂未配置。</p>
      </main>
    );
  return <ReportPageClient baseUrl={config.baseUrl} sessionId={sessionId} />;
}
