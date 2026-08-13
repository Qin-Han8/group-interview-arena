import createClient from "openapi-fetch";

import type { paths } from "./generated/schema";

export function createApiClient(baseUrl: string) {
  return createClient<paths>({ baseUrl });
}

export async function checkApiHealth(baseUrl: string): Promise<boolean> {
  const { data, error } = await createApiClient(baseUrl).GET("/health");

  return error === undefined && data?.status === "ok";
}
