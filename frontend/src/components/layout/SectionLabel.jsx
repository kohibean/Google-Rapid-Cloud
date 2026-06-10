export default function SectionLabel({ children, no }) {
  return (
    <div className="flex items-center gap-4 mb-6">
      {no && <span className="font-mono text-[10px] text-ink-soft">{no}</span>}
      <span className="smallcaps">{children}</span>
      <span className="flex-1 hairline" />
    </div>
  );
}
