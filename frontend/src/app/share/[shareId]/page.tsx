import type { Metadata } from "next";
import Link from "next/link";
import { headers } from "next/headers";
import { notFound } from "next/navigation";
import CompareMemos from "@/components/CompareMemos";
import MemoDocument from "@/components/MemoDocument";
import PitchScore from "@/components/PitchScore";
import PrintHeader from "@/components/PrintHeader";
import ShareActions from "@/components/ShareActions";
import { fetchShare } from "@/lib/api";
import { AI_DISCLAIMER, formatRunDate } from "@/lib/formatRun";
import type { SharedMemo } from "@/lib/types";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Shared analysis · VentureVision",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

function excerpt(text: string, length: number): string {
  return text.length > length ? `${text.slice(0, length)}…` : text;
}

async function shareUrlFor(shareId: string): Promise<string> {
  const h = await headers();
  const host = h.get("x-forwarded-host") ?? h.get("host") ?? "";
  const protocol = h.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  return `${protocol}://${host}/share/${shareId}`;
}

function Disclaimer({ memos }: { memos: SharedMemo[] }) {
  const dates = memos.map((m) => formatRunDate(m.generated_at));
  return (
    <div className="mb-10 border border-foreground px-4 py-3 font-sans text-xs rounded-sm print:hidden">
      <p className="uppercase tracking-widest text-foreground">{AI_DISCLAIMER}</p>
      <p className="text-muted mt-1.5">
        {memos.length === 1 ? `Run ${dates[0]}` : `Runs ${dates.join(" and ")}`}. Read-only copy produced by
        VentureVision&apos;s research agents from public web sources; check the cited sources before relying on any
        figure.
      </p>
    </div>
  );
}

export default async function SharedAnalysisPage({ params }: { params: Promise<{ shareId: string }> }) {
  const { shareId } = await params;
  const result = await fetchShare(shareId);

  if (result.status === "not_found") notFound();
  if (result.status === "error") {
    return (
      <main className="min-h-screen bg-background px-6 py-16">
        <div className="w-full max-w-2xl mx-auto font-sans text-sm">
          <p className="uppercase tracking-widest text-xs text-[#9B2C2C] mb-2">Couldn&apos;t load this shared analysis</p>
          <p className="text-foreground">{result.message}</p>
          <p className="text-muted mt-2">The link itself may be fine. Try again in a minute.</p>
        </div>
      </main>
    );
  }

  const { share } = result;
  const shareUrl = await shareUrlFor(shareId);
  const [first, second] = share.memos;
  const isCompare = share.kind === "compare" && second !== undefined;

  return (
    <main className="min-h-screen bg-background px-6 py-16 print:p-0 print:min-h-0">
      <div className={`w-full mx-auto ${isCompare ? "max-w-6xl" : "max-w-2xl"}`}>
        <PrintHeader
          label={isCompare ? "Shared comparison" : "Shared investment memo"}
          title={isCompare ? `${excerpt(first.pitch, 50)} vs ${excerpt(second.pitch, 50)}` : excerpt(first.pitch, 160)}
          runDates={share.memos.map((m) => m.generated_at)}
          shareUrl={shareUrl}
        />

        <div className="mb-8 print:hidden">
          <Link href="/" className="text-xs font-sans text-muted tracking-widest uppercase mb-8 block">
            &larr; VentureVision
          </Link>
          <p className="font-sans text-xs uppercase tracking-widest text-muted mb-2">
            {isCompare ? "Shared comparison" : "Shared investment memo"}
          </p>
          <p className="font-serif text-xl text-foreground leading-snug">
            {isCompare ? `${excerpt(first.pitch, 60)} vs ${excerpt(second.pitch, 60)}` : excerpt(first.pitch, 160)}
          </p>
        </div>

        <Disclaimer memos={share.memos} />
        <ShareActions kind={share.kind} memos={share.memos} printOnly />

        {isCompare ? (
          <CompareMemos
            left={{ pitch: first.pitch, memo: first.memo, source: { kind: "shared", generatedAt: first.generated_at }, runDate: first.generated_at }}
            right={{ pitch: second.pitch, memo: second.memo, source: { kind: "shared", generatedAt: second.generated_at }, runDate: second.generated_at }}
          />
        ) : (
          <>
            <PitchScore pitchScore={first.memo.pitch_score} subscores={first.memo.subscores} />
            <MemoDocument memo={first.memo} pitch={first.pitch} source={{ kind: "shared", generatedAt: first.generated_at }} />
          </>
        )}

        <div className="border-t border-border pt-6 mt-10 print:hidden">
          <Link href="/" className="font-sans text-sm text-foreground hover:underline">
            Analyze your own pitch &rarr;
          </Link>
        </div>
      </div>
    </main>
  );
}
