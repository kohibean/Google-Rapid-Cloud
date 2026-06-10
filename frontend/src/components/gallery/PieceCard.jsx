import VersionTimeline from "./VersionTimeline";
import StageChip from "./StageChip";

export default function PieceCard({ piece, onClick }) {
  return (
    <article
      onClick={onClick}
      className="editorial-card cursor-pointer group"
    >
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <h3 className="font-display text-[22px] leading-tight font-medium
                         group-hover:text-accent transition-colors">
            {piece.title}
          </h3>
          <p className="font-mono text-[10px] text-ink-soft tracking-wide mt-1.5">
            {piece.versions} version{piece.versions !== 1 ? "s" : ""}
          </p>
        </div>
        <StageChip stage={piece.stage} />
      </div>
      <div className="hairline pt-3">
        <VersionTimeline count={piece.versions} />
      </div>
    </article>
  );
}
