export default function TrendChart({ label, points }: { label: string; points: { date: string; value: number }[] }) {
  if (points.length < 2) return <p className="rounded border border-line bg-paper p-4 text-sm text-quiet">Not enough data for a trend.</p>;
  const max = Math.max(...points.map((point) => point.value), 1);
  const path = points.map((point, index) => {
    const x = (index / (points.length - 1)) * 100;
    const y = 100 - (point.value / max) * 90;
    return `${index ? "L" : "M"} ${x} ${y}`;
  }).join(" ");
  return <figure className="rounded border border-line bg-paper p-4 shadow-soft"><figcaption className="mb-3 text-sm font-medium text-ink">{label}</figcaption><svg viewBox="0 0 100 100" className="h-56 w-full" preserveAspectRatio="none" role="img" aria-label={`${label} trend`}><path d={path} fill="none" stroke="#58789A" strokeWidth="1.5" vectorEffect="non-scaling-stroke" /></svg><div className="flex justify-between text-xs text-quiet"><span>{points[0].date}</span><span>{points[points.length - 1].date}</span></div></figure>;
}
