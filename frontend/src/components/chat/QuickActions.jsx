const ACTIONS = [
  { label: "▶  start session", prefix: "I am starting work on " },
  { label: "■  end session", prefix: "Wrapping up. I worked on " },
  { label: "↻  where was I?", prefix: "Where was I on " },
];

export default function QuickActions({ onPick }) {
  return (
    <div className="flex flex-wrap gap-2 pt-5 pb-3">
      {ACTIONS.map((a) => (
        <button
          key={a.label}
          onClick={() => onPick(a.prefix)}
          className="btn-ghost"
        >
          {a.label}
        </button>
      ))}
    </div>
  );
}
