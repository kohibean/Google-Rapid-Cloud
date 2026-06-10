import SectionLabel from "../layout/SectionLabel";
import PieceCard from "./PieceCard";

export default function Gallery({ pieces, onAskAbout }) {
  return (
    <div>
      <SectionLabel no="I.">Your Pieces</SectionLabel>

      {pieces.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {pieces.map((p) => (
            <PieceCard
              key={p.title}
              piece={p}
              onClick={() => onAskAbout(p.title)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="py-16 text-center">
      <div className="text-accent text-3xl mb-5">✦</div>
      <p className="font-serif italic text-lg text-ink-soft max-w-prose mx-auto">
        Nothing in the studio yet. Tell your companion you're starting a piece,
        and the work will begin to accumulate here.
      </p>
      <p className="smallcaps mt-6">
        Try — <span className="italic font-serif normal-case tracking-normal text-ink">
          "I'm starting work on a dragon painting"
        </span>
      </p>
    </div>
  );
}
