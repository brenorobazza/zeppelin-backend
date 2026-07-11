import { SlidersHorizontal } from "lucide-react";
import "./benchmark-state-panel.css";

export function BenchmarkStatePanel({
  tone = "neutral",
  title,
  message,
  badge,
  actionLabel,
  onAction,
  icon = null
}) {
  return (
    <section className={["benchmark-state", `benchmark-state--${tone}`].join(" ")}>
      <header className="benchmark-state__head">
        {badge ? <span className="benchmark-state__badge">{badge}</span> : null}
      </header>

      <div className="benchmark-state__icon" aria-hidden="true">
        {icon}
      </div>

      <h3>{title}</h3>
      <p>{message}</p>

      {actionLabel && typeof onAction === "function" ? (
        <button type="button" className="benchmark-state__action" onClick={onAction}>
          <SlidersHorizontal size={14} strokeWidth={2.2} />
          {actionLabel}
        </button>
      ) : null}
    </section>
  );
}
