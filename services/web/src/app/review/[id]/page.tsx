import { notFound } from "next/navigation";

import ReviewPage from "@/components/ReviewPage";
import { getAnalyzeResponseFor, getTranscript } from "@/lib/fixtures";

interface PageProps {
  params: { id: string };
}

export default function ReviewRoute({ params }: PageProps) {
  const transcript = getTranscript(params.id);
  const response = getAnalyzeResponseFor(params.id);
  if (!transcript || !response) {
    notFound();
  }

  return (
    <ReviewPage
      title={transcript.title}
      rawText={transcript.rawText}
      response={response}
    />
  );
}
