"use client";

import { Analytics } from "@vercel/analytics/react";

/** Page views on shared memos are never sent: visitors are not tracked, and share URLs are secrets. */
export default function SiteAnalytics() {
  return <Analytics beforeSend={(event) => (new URL(event.url).pathname.startsWith("/share/") ? null : event)} />;
}
