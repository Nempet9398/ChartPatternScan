// Next.js 15: params is a Promise
import ResultClient from "./ResultClient";

export default function ResultPage({
  params,
}: {
  params: Promise<{ symbol: string }>;
}) {
  return <ResultClient params={params} />;
}
