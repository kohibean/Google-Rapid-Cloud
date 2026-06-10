export default function Message({ who, text, briefing }) {
  if (who === "user") {
    return (
      <div className="flex justify-end">
        <p className="bg-ink text-paper font-serif text-[15.5px] leading-relaxed
                      px-4 py-2.5 max-w-[88%] rounded-sm rounded-br-2xl">
          {text}
        </p>
      </div>
    );
  }

  if (briefing) {
    return (
      <article className="border border-accent bg-paper p-5
                          shadow-[3px_4px_0_0_rgba(181,83,42,0.18)]">
        <p className="smallcaps text-accent mb-3">A Briefing</p>
        <p className="font-serif text-[16px] leading-[1.6] whitespace-pre-wrap">
          {text}
        </p>
      </article>
    );
  }

  return (
    <div className="border-l-2 border-accent pl-4">
      <p className="smallcaps text-accent mb-1.5">SiningAI</p>
      <p className="font-serif text-[16px] leading-[1.55] whitespace-pre-wrap">
        {text}
      </p>
    </div>
  );
}
