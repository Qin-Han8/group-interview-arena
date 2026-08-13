export type PublicApiConfig =
  | { status: "configured"; baseUrl: string }
  | { status: "missing" }
  | { status: "invalid" };

export function getPublicApiConfig(
  rawValue = process.env.NEXT_PUBLIC_API_BASE_URL,
): PublicApiConfig {
  const value = rawValue?.trim();

  if (!value) {
    return { status: "missing" };
  }

  try {
    const url = new URL(value);
    if (
      !["http:", "https:"].includes(url.protocol) ||
      url.username ||
      url.password ||
      url.search ||
      url.hash
    ) {
      return { status: "invalid" };
    }

    return { status: "configured", baseUrl: url.href.replace(/\/$/, "") };
  } catch {
    return { status: "invalid" };
  }
}
