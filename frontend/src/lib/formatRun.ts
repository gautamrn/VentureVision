export function formatUsd(amount: number): string {
  if (amount === 0) return "$0";
  if (amount >= 0.01) return `$${amount.toFixed(2)}`;
  return `$${amount.toPrecision(2)}`;
}

export function formatDuration(ms: number): string {
  return ms >= 10_000 ? `${Math.round(ms / 1000)}s` : `${(ms / 1000).toFixed(1)}s`;
}

export const AI_DISCLAIMER = "AI-generated analysis — verify before use";

export function formatRunDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const day = date.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" });
  const time = date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "UTC" });
  return `${day}, ${time} UTC`;
}

export function formatTokens(count: number): string {
  return count >= 1000 ? `${(count / 1000).toFixed(1)}k` : String(count);
}

export const NODE_LABELS: Record<string, string> = {
  planner: "Planner",
  scout: "Scout",
  critic: "Critic",
  writer: "Writer",
  citation_audit: "Citation audit",
};
