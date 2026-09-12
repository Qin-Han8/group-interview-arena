"use client";

import { useMemo } from "react";

import { createApiClient } from "@/lib/api/client";

import ReportView from "./report-view";

export default function ReportPageClient({
  baseUrl,
  sessionId,
}: {
  baseUrl: string;
  sessionId: string;
}) {
  const apiClient = useMemo(() => createApiClient(baseUrl), [baseUrl]);
  return <ReportView apiClient={apiClient} sessionId={sessionId} />;
}
