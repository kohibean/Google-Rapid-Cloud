import { stageMeta } from "../../lib/stages";

export default function StageChip({ stage }) {
  const meta = stageMeta(stage);
  return (
    <span
      className={`${meta.color} text-paper font-sans text-[10px] uppercase tracking-wide
                  px-2 py-1 whitespace-nowrap`}
    >
      {meta.label}
    </span>
  );
}
