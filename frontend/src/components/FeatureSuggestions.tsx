import { Lightbulb } from "lucide-react";

interface Props {
  suggestions: string[];
}

export default function FeatureSuggestions({ suggestions }: Props) {
  if (suggestions.length === 0) return null;

  return (
    <section className="mb-12">
      <h2 className="font-sans text-xs uppercase tracking-widest text-muted mb-4">
        Features to Consider Building
      </h2>
      <p className="font-sans text-sm text-muted mb-4">
        Based on market evidence and competitor offerings, consider these additions.
      </p>
      <ul className="space-y-3">
        {suggestions.map((suggestion, i) => (
          <li key={i} className="flex items-start gap-3">
            <Lightbulb size={14} className="text-amber-500 mt-1 shrink-0" />
            <span className="text-base leading-relaxed font-serif">
              {suggestion}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
