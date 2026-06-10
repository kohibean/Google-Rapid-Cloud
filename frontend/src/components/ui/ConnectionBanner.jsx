import { useEffect, useState } from "react";

export default function ConnectionBanner({ conn }) {
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    if (conn.state === "ok") {
      const t = setTimeout(() => setHidden(true), 2200);
      return () => clearTimeout(t);
    } else {
      setHidden(false);
    }
  }, [conn.state]);

  if (hidden) return null;

  const styles = {
    connecting: "bg-rule text-ink-soft",
    ok: "bg-stage-final/15 text-stage-final",
    bad: "bg-accent/12 text-accent-deep",
  };
  const icons = { connecting: "·", ok: "●", bad: "⚠" };
  const labels = {
    connecting: "connecting to studio companion…",
    ok: `${icons.ok} connected to studio companion`,
    bad: `${icons.bad} ${conn.message}`,
  };
  return (
    <div className={`font-mono text-[11px] tracking-wide text-center py-2 ${styles[conn.state]}`}>
      {labels[conn.state]}
    </div>
  );
}
