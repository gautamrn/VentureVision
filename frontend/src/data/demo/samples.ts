export interface DemoSample {
  id: string;
  category: string;
  title: string;
  tagline: string;
}

export const DEMO_SAMPLES: DemoSample[] = [
  {
    id: "flakeguard",
    category: "Dev-tools SaaS",
    title: "Flakeguard",
    tagline: "Detects and quarantines flaky tests before they block a merge.",
  },
  {
    id: "pantry",
    category: "Consumer app",
    title: "Pantry",
    tagline: "Turns grocery receipts into a weekly meal plan that uses what you already bought.",
  },
  {
    id: "thermalith",
    category: "Climate hardware",
    title: "Thermalith",
    tagline: "Sand-based thermal batteries that replace gas boilers for industrial process heat.",
  },
];
