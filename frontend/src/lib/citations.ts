import type { Citation, PitchAnnotation } from "./types";

export function numberCitations(citations: (Citation | null | undefined)[]): (number | null)[] {
  const numbers = new Map<string, number>();
  return citations.map((citation) => {
    if (!citation) return null;
    const key = `${citation.source_url}\u0000${citation.quote}`;
    if (!numbers.has(key)) numbers.set(key, numbers.size + 1);
    return numbers.get(key) ?? null;
  });
}

export function annotationsInPitch(pitch: string, annotations: PitchAnnotation[]): PitchAnnotation[] {
  const lowerPitch = pitch.toLowerCase();
  return annotations.filter((a) => lowerPitch.includes(a.excerpt.toLowerCase()));
}

export function retrievalDate(citation: Citation): string {
  return citation.retrieved_at.slice(0, 10);
}

export function sourceHost(citation: Citation): string {
  try {
    return new URL(citation.source_url).hostname.replace(/^www\./, "");
  } catch {
    return citation.source_url;
  }
}
