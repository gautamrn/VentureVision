import Link from "next/link";

export default function ShareNotFound() {
  return (
    <main className="min-h-screen bg-background px-6 py-16">
      <div className="w-full max-w-2xl mx-auto font-sans text-sm">
        <p className="uppercase tracking-widest text-xs text-muted mb-2">Shared analysis not found</p>
        <p className="text-foreground">This link doesn&apos;t match any shared memo. Check that it was copied in full.</p>
        <Link href="/" className="inline-block mt-6 text-foreground hover:underline">
          &larr; VentureVision
        </Link>
      </div>
    </main>
  );
}
