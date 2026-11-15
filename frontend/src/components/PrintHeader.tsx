import { AI_DISCLAIMER, formatRunDate } from "@/lib/formatRun";

interface Props {
  label: string;
  title: string;
  runDates?: (string | null | undefined)[];
  shareUrl?: string | null;
}

export default function PrintHeader({ label, title, runDates = [], shareUrl }: Props) {
  const dates = runDates.filter((d): d is string => Boolean(d)).map(formatRunDate);
  return (
    <header className="hidden print:block mb-8 pb-4 border-b-2 border-foreground font-sans">
      <div className="flex items-baseline justify-between gap-6 text-[9pt] uppercase tracking-widest">
        <span className="text-foreground">VentureVision</span>
        <span className="text-muted">{label}</span>
      </div>
      <p className="font-serif text-[17pt] leading-snug text-foreground mt-3">{title}</p>
      <p className="text-[8.5pt] text-muted mt-2">
        {dates.length > 0 ? `${dates.length === 1 ? "Run" : "Runs"} ${dates.join(" and ")} · ` : ""}
        {AI_DISCLAIMER}
      </p>
      {shareUrl && <p className="text-[8pt] text-muted mt-1 break-all">{shareUrl}</p>}
    </header>
  );
}
