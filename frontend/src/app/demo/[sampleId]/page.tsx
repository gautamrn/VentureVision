import { notFound } from "next/navigation";
import DemoReplay from "@/components/DemoReplay";
import { loadDemoRun } from "@/data/demo/loadDemoRun";
import { DEMO_SAMPLES } from "@/data/demo/samples";

export const dynamicParams = false;

export function generateStaticParams() {
  return DEMO_SAMPLES.map((sample) => ({ sampleId: sample.id }));
}

export default async function DemoPage({ params }: { params: Promise<{ sampleId: string }> }) {
  const { sampleId } = await params;
  const run = loadDemoRun(sampleId);
  if (!run) notFound();

  return <DemoReplay run={run} />;
}
