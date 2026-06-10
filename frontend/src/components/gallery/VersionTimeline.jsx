export default function VersionTimeline({ count }) {
  const n = Math.max(count, 1);
  const nodes = [];
  for (let i = 0; i < n; i++) {
    nodes.push(
      <span
        key={`node-${i}`}
        className={`w-2.5 h-2.5 rounded-full flex-shrink-0 border-2 ${
          i < count ? "bg-accent border-accent" : "bg-paper border-ink-soft"
        }`}
      />
    );
    if (i < n - 1) {
      nodes.push(
        <span key={`line-${i}`} className="flex-1 h-px bg-rule" />
      );
    }
  }
  return (
    <div className="flex items-center gap-1.5">
      {nodes}
      <span className="font-mono text-[10px] text-ink-soft ml-3 whitespace-nowrap">
        v{count}
      </span>
    </div>
  );
}
