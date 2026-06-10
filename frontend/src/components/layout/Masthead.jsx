export default function Masthead({ onSettings }) {
  return (
    <header className="border-b border-ink">
      <div className="max-w-page mx-auto px-8 lg:px-12 pt-7 pb-5
                      flex items-end justify-between">
        <div>
          <h1 className="font-display text-[34px] leading-none font-medium tracking-tight">
            <span className="text-accent mr-3">✦</span>
            Sining<span className="italic text-accent">AI</span>
          </h1>
          <p className="smallcaps mt-3">
            The Continuity Engine for Creative Work
          </p>
        </div>

        <div className="flex items-center gap-5">
          <p className="smallcaps hidden md:block">Vol. 01 / Studio Edition</p>
          <button
            onClick={onSettings}
            className="text-ink-soft hover:text-ink text-lg leading-none"
            title="Settings"
          >
            ⚙
          </button>
        </div>
      </div>
    </header>
  );
}
