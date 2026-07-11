import { useEffect, useMemo, useState } from "react";
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer
} from "recharts";
import { AlertTriangle, Lock, SearchX } from "lucide-react";
import { loadBenchmarkAnalytics, loadComparisonAnalytics } from "../services/analytics";
import { BenchmarkStatePanel } from "./BenchmarkStatePanel";
import "./benchmark-comparison-card.css";

const LENS_OPTIONS = [
  {
    key: "eye",
    label: "Eye of CSE",
    description: "7 dimensions"
  },
  {
    key: "sth",
    label: "StH",
    description: "4 stages"
  }
];

const MIN_LOADING_MS = 400;

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function splitLabel(label, maxChars = 16) {
  if (!label) return [""];

  const words = label.split(" ");
  const lines = [];
  let currentLine = "";

  words.forEach((word) => {
    const nextLine = currentLine ? `${currentLine} ${word}` : word;
    if (nextLine.length <= maxChars) {
      currentLine = nextLine;
      return;
    }

    if (currentLine) {
      lines.push(currentLine);
    }
    currentLine = word;
  });

  if (currentLine) {
    lines.push(currentLine);
  }

  return lines;
}

function renderRadarAxisTick({ x, y, payload, textAnchor }) {
  const lines = splitLabel(payload.value);

  return (
    <text
      x={x}
      y={y}
      textAnchor={textAnchor}
      className="benchmark-comparison-card__label"
      style={{ fill: "#0f172a" }}
    >
      {lines.map((line, index) => (
        <tspan
          key={`${payload.value}-line-${index}`}
          x={x}
          dy={index === 0 ? 0 : 13}
          style={{ fill: "#0f172a" }}
        >
          {line}
        </tspan>
      ))}
    </text>
  );
}

function RadarPlot({
  title,
  axes,
  currentValues,
  referenceValues,
  currentLabel,
  referenceLabel,
  legendReferenceLabel = "Reference"
}) {
  const chartData = useMemo(
    () =>
      axes.map((axis, index) => ({
        axis,
        current: currentValues[index] ?? 0,
        reference: referenceValues[index] ?? 0
      })),
    [axes, currentValues, referenceValues]
  );

  return (
    <div className="benchmark-comparison-card__plot-card">
      <div className="benchmark-comparison-card__plot-header">
        <div>
          <span>Comparison radar</span>
          <h4>{title}</h4>
        </div>
      </div>

      <div className="benchmark-comparison-card__svg-wrap">
        <ResponsiveContainer width="100%" height={380}>
          <RadarChart
            data={chartData}
            aria-label={`${title} comparison radar`}
            margin={{ top: 20, right: 28, bottom: 20, left: 28 }}
          >
            <PolarGrid stroke="rgba(0, 0, 0, 0.2)" />
            <PolarAngleAxis dataKey="axis" tick={renderRadarAxisTick} />
            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} tickLine={false} />

            <Radar
              name={referenceLabel}
              dataKey="reference"
              stroke="rgba(37, 99, 235, 0.72)"
              strokeDasharray="6 4"
              fill="rgba(37, 99, 235, 0.08)"
              fillOpacity={1}
              dot={{ r: 2.8, fill: "rgba(37, 99, 235, 0.9)" }}
            />
            <Radar
              name={currentLabel}
              dataKey="current"
              stroke="rgba(34, 197, 94, 0.94)"
              fill="rgba(34, 197, 94, 0.1)"
              fillOpacity={0.45}
              dot={{ r: 3.2, fill: "rgba(34, 197, 94, 1)" }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="benchmark-comparison-card__legend">
        <span className="benchmark-comparison-card__legend-item">
          <i className="benchmark-comparison-card__legend-dot benchmark-comparison-card__legend-dot--current" />
          Current
        </span>
        <span className="benchmark-comparison-card__legend-item">
          <i className="benchmark-comparison-card__legend-dot benchmark-comparison-card__legend-dot--reference" />
          {legendReferenceLabel}
        </span>
      </div>
    </div>
  );
}

function LevelBars({ axes, currentValues, referenceValues, lensKey }) {
  const maxScore = 100;

  return (
    <div className="benchmark-comparison-card__levels">
      <div className="benchmark-comparison-card__levels-head">
        <span>Dimensions breakdown</span>
        <small>Current vs reference</small>
      </div>

      <div className="benchmark-comparison-card__levels-list">
        {axes.map((axis, index) => {
          const current = axis.current ?? currentValues[index] ?? 0;
          const reference = axis.reference ?? referenceValues[index] ?? 0;
          const currentWidth = `${clamp((current / maxScore) * 100, 0, 100)}%`;
          const referenceWidth = `${clamp((reference / maxScore) * 100, 0, 100)}%`;
          const gap = current - reference;

          return (
            <article key={axis.key} className="benchmark-comparison-card__level-row">
              <div className="benchmark-comparison-card__level-copy">
                <strong>{axis.label}</strong>
                <span className={gap < 0 ? "is-negative" : "is-positive"}>
                  {gap >= 0 ? `+${gap}` : gap}% vs ref
                </span>
              </div>

              <div className="benchmark-comparison-card__level-track">
                <span
                  className="benchmark-comparison-card__level-bar benchmark-comparison-card__level-bar--reference"
                  style={{ width: referenceWidth }}
                />
                <span
                  className="benchmark-comparison-card__level-bar benchmark-comparison-card__level-bar--current"
                  style={{ width: currentWidth }}
                />
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function createEmptyComparisonData() {
  return {
    benchmarkState: {
      code: "ready",
      title: "",
      message: "",
      errorCode: "",
      minCompanyThreshold: 5,
      companyCount: 0,
      snapshotCount: 0
    },
    selection: {
      currentCycle: { id: "", label: "", answeredPractices: 0 },
      referenceCycle: { id: "", label: "", answeredPractices: 0 },
      availableCycles: []
    },
    summary: {
      currentScore: 0,
      referenceScore: 0,
      delta: 0,
      currentAnsweredPractices: 0,
      referenceAnsweredPractices: 0
    },
    lenses: {
      eye: {
        key: "eye",
        title: "Benchmark comparison",
        subtitle: "Select two cycles to compare them.",
        currentScore: 0,
        referenceScore: 0,
        delta: 0,
        axes: []
      },
      sth: {
        key: "sth",
        title: "Benchmark comparison",
        subtitle: "Select two cycles to compare them.",
        currentScore: 0,
        referenceScore: 0,
        delta: 0,
        axes: []
      }
    }
  };
}

function normalizeAxisValues(axes = []) {
  return axes.map((axis, index) => ({
    ...axis,
    index
  }));
}

function getCycleLabel(comparisonData, cycleId) {
  return (
    comparisonData?.selection?.availableCycles?.find((cycle) => String(cycle.id) === String(cycleId))
      ?.displayLabel ||
    comparisonData?.selection?.availableCycles?.find((cycle) => String(cycle.id) === String(cycleId))
      ?.label ||
    ""
  );
}

function getDifferentCycleId(cycles = [], excludedId = "") {
  const candidate = cycles.find((cycle) => String(cycle.id) !== String(excludedId));
  return candidate ? String(candidate.id) : "";
}

/**
 * BenchmarkComparisonCard
 * 
 * Wrapper that adds mock data support on top of TimeEvolutionCard logic.
 * Used by BenchmarkPage to support both backend and mock analytics.
 * 
 * Props:
 * - filters: Object with organizationId, questionnaireId, stageScope
 * - mockLoader: Optional function(filters) that returns mock comparison data
 * - className: CSS class names to apply
 */
export function BenchmarkComparisonCard({
  className = "",
  filters = {},
  mockLoader = null,
  comparisonVariant = "history",
  onClearFilters,
  onAdjustFilters
}) {
  const isBenchmarkComparison = comparisonVariant === "benchmark";
  const [lensKey, setLensKey] = useState("eye");
  const [currentQuestionnaireId, setCurrentQuestionnaireId] = useState(filters.questionnaireId || "");
  const [referenceQuestionnaireId, setReferenceQuestionnaireId] = useState("");
  const [comparisonData, setComparisonData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setCurrentQuestionnaireId(filters.questionnaireId || "");
    setReferenceQuestionnaireId("");
  }, [
    filters.organizationId,
    filters.questionnaireId,
    filters.category,
    filters.size,
    filters.type,
    filters.targetAudience
  ]);

  useEffect(() => {
    let ignore = false;

    async function syncComparison() {
      const startedAt = Date.now();

      if (!filters.organizationId) {
        setComparisonData(createEmptyComparisonData());
        setLoading(false);
        return;
      }

      setLoading(true);
      setError("");

      try {
        const useSpecificCycles = Boolean(currentQuestionnaireId && referenceQuestionnaireId);
        const requestFilters = {
          organizationId: filters.organizationId,
          questionnaireId: currentQuestionnaireId || filters.questionnaireId || "",
          category: filters.category,
          size: filters.size,
          type: filters.type,
          targetAudience: filters.targetAudience,
          referenceMode: isBenchmarkComparison
            ? "peer-aggregate"
            : useSpecificCycles
              ? "specific-cycles"
              : "first-submission",
          referenceQuestionnaireId: useSpecificCycles ? referenceQuestionnaireId : ""
        };

        // Use mockLoader if provided; otherwise fetch from backend
        const loadAnalytics = isBenchmarkComparison
          ? loadBenchmarkAnalytics
          : loadComparisonAnalytics;
        const bundle = mockLoader ? mockLoader(requestFilters) : await loadAnalytics(requestFilters);
        if (ignore) return;

        setComparisonData(bundle);

        const availableCycles = bundle.selection?.availableCycles || [];
        const resolvedCurrentId = currentQuestionnaireId || String(bundle.selection?.currentCycle?.id || "");
        const resolvedReferenceId = referenceQuestionnaireId || String(bundle.selection?.referenceCycle?.id || "");

        if (!currentQuestionnaireId && resolvedCurrentId) {
          setCurrentQuestionnaireId(resolvedCurrentId);
        }

        if (!isBenchmarkComparison && (!resolvedReferenceId || resolvedReferenceId === resolvedCurrentId)) {
          const nextReferenceId = getDifferentCycleId(availableCycles, resolvedCurrentId);
          if (nextReferenceId) {
            setReferenceQuestionnaireId(nextReferenceId);
          }
        } else if (!isBenchmarkComparison && !referenceQuestionnaireId) {
          setReferenceQuestionnaireId(resolvedReferenceId);
        }
      } catch (fetchError) {
        if (ignore) return;
        setComparisonData({
          ...createEmptyComparisonData(),
          benchmarkState: {
            code: "error",
            title: "Unable to load benchmark data",
            message: fetchError.message || "Failed to load comparison analytics.",
            errorCode: "ERR_DATA_FETCH_FAILED_500",
            minCompanyThreshold: 5,
            companyCount: 0,
            snapshotCount: 0
          }
        });
        setError(fetchError.message || "Failed to load comparison analytics.");
      } finally {
        const elapsed = Date.now() - startedAt;
        const remaining = Math.max(0, MIN_LOADING_MS - elapsed);
        if (remaining > 0) {
          await new Promise((resolve) => setTimeout(resolve, remaining));
        }

        if (!ignore) {
          setLoading(false);
        }
      }
    }

    syncComparison();

    return () => {
      ignore = true;
    };
  }, [
    filters.organizationId,
    filters.questionnaireId,
    filters.category,
    filters.size,
    filters.type,
    filters.targetAudience,
    currentQuestionnaireId,
    referenceQuestionnaireId,
    isBenchmarkComparison,
    mockLoader
  ]);

  const selectedCurrentCycleId = currentQuestionnaireId || String(comparisonData?.selection?.currentCycle?.id || "");
  const selectedReferenceCycleId = referenceQuestionnaireId || String(comparisonData?.selection?.referenceCycle?.id || "");
  const availableCycles = comparisonData?.selection?.availableCycles || [];
  const currentCycleLabel = getCycleLabel(comparisonData, selectedCurrentCycleId) || comparisonData?.selection?.currentCycle?.label || "Current cycle";
  const referenceCycleLabel = getCycleLabel(comparisonData, selectedReferenceCycleId) || comparisonData?.selection?.referenceCycle?.label || "Reference cycle";
  const referenceContext = comparisonData?.selection?.referenceContext || null;
  const benchmarkReferenceLabel = referenceContext?.label || referenceCycleLabel || "Peer average";
  const benchmarkState = comparisonData?.benchmarkState || { code: "ready" };
  const benchmarkStateCode = String(benchmarkState.code || "ready").toLowerCase();
  const isInsufficientState = isBenchmarkComparison && benchmarkStateCode === "insufficient_data";
  const isEmptyState = isBenchmarkComparison && benchmarkStateCode === "empty_results";
  const isErrorState = isBenchmarkComparison && benchmarkStateCode === "error";
  const isRefreshing = loading && Boolean(comparisonData);
  const referenceCycleOptions = availableCycles.filter(
    (cycle) => String(cycle.id) !== String(selectedCurrentCycleId)
  );

  const currentScoreLabel = "Current score";
  const referenceScoreLabel = isBenchmarkComparison ? "Peer average" : "Reference score";

  const activeLens = comparisonData?.lenses?.[lensKey] || comparisonData?.lenses?.eye;
  const selectedAxes = normalizeAxisValues(activeLens?.axes || []);
  const radarTitle = isBenchmarkComparison
    ? activeLens?.title || "Benchmark comparison"
    : `${currentCycleLabel} vs ${referenceCycleLabel}`;

  function handleCurrentCycleChange(nextCurrentQuestionnaireId) {
    setCurrentQuestionnaireId(nextCurrentQuestionnaireId);

    if (!isBenchmarkComparison && String(nextCurrentQuestionnaireId) === String(referenceQuestionnaireId)) {
      const nextReferenceId = getDifferentCycleId(availableCycles, nextCurrentQuestionnaireId);
      setReferenceQuestionnaireId(nextReferenceId);
    }
  }

  function handleReferenceCycleChange(nextReferenceQuestionnaireId) {
    if (!isBenchmarkComparison) {
      setReferenceQuestionnaireId(nextReferenceQuestionnaireId);
    }
  }

  if (loading && !comparisonData) {
    return (
      <section className={["benchmark-comparison-card", "benchmark-comparison-card--loading", className].filter(Boolean).join(" ")}>
        <div className="benchmark-comparison-card__skeleton-header" />
        <div className="benchmark-comparison-card__skeleton-body" />
        <div className="benchmark-comparison-card__skeleton-body benchmark-comparison-card__skeleton-body--short" />
      </section>
    );
  }

  if (!comparisonData) {
    return (
      <section className={["benchmark-comparison-card", "benchmark-comparison-card--loading", className].filter(Boolean).join(" ")}>
        <div className="benchmark-comparison-card__skeleton-header" />
        <div className="benchmark-comparison-card__skeleton-body" />
        <div className="benchmark-comparison-card__skeleton-body benchmark-comparison-card__skeleton-body--short" />
      </section>
    );
  }

  if (isInsufficientState) {
    return (
      <BenchmarkStatePanel
        tone="warning"
        badge="Insufficient Data"
        icon={<Lock size={24} strokeWidth={2.2} />}
        title={benchmarkState.title || "Insufficient data for comparison"}
        message={benchmarkState.message || "Not enough peer companies for comparison."}
        actionLabel="Clear filters"
        onAction={onClearFilters}
      />
    );
  }

  if (isEmptyState) {
    return (
      <BenchmarkStatePanel
        tone="neutral"
        badge="Empty State"
        icon={<SearchX size={24} strokeWidth={2.2} />}
        title={benchmarkState.title || "No data found"}
        message={benchmarkState.message || "No benchmark snapshots match the selected filters."}
      />
    );
  }

  if (isErrorState) {
    return (
      <BenchmarkStatePanel
        tone="error"
        badge="Error"
        icon={<AlertTriangle size={24} strokeWidth={2.2} />}
        title={benchmarkState.title || "Unable to load benchmark data"}
        message={benchmarkState.message || "A server-side error occurred while computing benchmark data."}
        details={benchmarkState.errorCode ? `Error code: ${benchmarkState.errorCode}` : "Please adjust filters or try again later."}
      />
    );
  }

  return (
    <section
      className={[
        "benchmark-comparison-card",
        isRefreshing && "benchmark-comparison-card--refreshing",
        className
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {isRefreshing ? (
        <div className="benchmark-comparison-card__refresh-overlay" role="status" aria-live="polite">
          <div className="benchmark-comparison-card__refresh-badge">Loading benchmark data...</div>
        </div>
      ) : null}

      <div className="benchmark-comparison-card__toolbar">
        <div className="benchmark-comparison-card__toolbar-center">
          <h3>{activeLens?.title || "Benchmark comparison"}</h3>
          <p>{activeLens?.subtitle || "Comparison data loaded from backend analytics."}</p>
          {error ? <small className="benchmark-comparison-card__error">{error}</small> : null}
        </div>

        <div className="benchmark-comparison-card__group">
          <span>Lens</span>
          <div className="benchmark-comparison-card__segmented">
            {LENS_OPTIONS.map((option) => (
              <button
                key={option.key}
                type="button"
                className={[
                  "benchmark-comparison-card__segment",
                  lensKey === option.key && "is-active"
                ]
                  .filter(Boolean)
                  .join(" ")}
                onClick={() => setLensKey(option.key)}
                aria-pressed={lensKey === option.key}
                title={option.description}
              >
                <strong>{option.label}</strong>
                <small>{option.description}</small>
              </button>
            ))}
          </div>
        </div>

        <div className="benchmark-comparison-card__group">
          <div className="benchmark-comparison-card__cycles-picker">
            {!isBenchmarkComparison ? (
              <div className="benchmark-comparison-card__cycle-group">
                <label htmlFor={`current-cycle-${lensKey}`}>Current cycle</label>
                <select
                  id={`current-cycle-${lensKey}`}
                  value={selectedCurrentCycleId}
                  onChange={(event) => handleCurrentCycleChange(event.target.value)}
                  className="benchmark-comparison-card__cycle-select"
                >
                  {availableCycles.map((cycle) => (
                    <option key={cycle.id} value={cycle.id}>
                      {cycle.displayLabel || cycle.label}
                    </option>
                  ))}
                </select>
              </div>
            ) : null}

            {isBenchmarkComparison ? (
              <div className="benchmark-comparison-card__reference-summary">
                <span>Peer group</span>
                <small>
                  {referenceContext
                    ? `${referenceContext.company_count} companies · ${referenceContext.snapshot_count} snapshots`
                    : "Aggregated peer snapshots matched by the active filters"}
                </small>
              </div>
            ) : (
              <div className="benchmark-comparison-card__cycle-group">
                <label htmlFor={`reference-cycle-${lensKey}`}>Reference cycle</label>
                <select
                  id={`reference-cycle-${lensKey}`}
                  value={selectedReferenceCycleId}
                  onChange={(event) => handleReferenceCycleChange(event.target.value)}
                  className="benchmark-comparison-card__cycle-select"
                >
                  {referenceCycleOptions.map((cycle) => (
                    <option key={cycle.id} value={cycle.id}>
                      {cycle.displayLabel || cycle.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="benchmark-comparison-card__body">
        <div className="benchmark-comparison-card__canvas">
          <RadarPlot
            key={`${lensKey}-${selectedCurrentCycleId}-${selectedReferenceCycleId}`}
            title={radarTitle}
            axes={selectedAxes.map((axis) => axis.label)}
            currentValues={selectedAxes.map((axis) => axis.current ?? 0)}
            referenceValues={selectedAxes.map((axis) => axis.reference ?? 0)}
            currentLabel={currentCycleLabel}
            referenceLabel={isBenchmarkComparison ? benchmarkReferenceLabel : referenceCycleLabel}
            legendReferenceLabel={isBenchmarkComparison ? "Peers" : "Reference"}
          />
        </div>

        <aside className="benchmark-comparison-card__summary">
          <article className="benchmark-comparison-card__score-card">
            <span className="benchmark-comparison-card__score-heading">
              <i className="benchmark-comparison-card__score-indicator benchmark-comparison-card__score-indicator--current" />
              {currentScoreLabel}
            </span>
            <strong>{comparisonData.summary.currentScore}/100</strong>
          </article>

          <article className="benchmark-comparison-card__reference-score-card benchmark-comparison-card__score-card--soft">
            <span className="benchmark-comparison-card__score-heading">
              <i className="benchmark-comparison-card__score-indicator benchmark-comparison-card__score-indicator--reference" />
              {referenceScoreLabel}
            </span>
            <strong>{comparisonData.summary.referenceScore}/100</strong>
            {!isBenchmarkComparison ? (
              <small>{referenceCycleLabel}</small>
            ) : null}
          </article>

          <LevelBars
            axes={selectedAxes}
            currentValues={selectedAxes.map((axis) => axis.current ?? 0)}
            referenceValues={selectedAxes.map((axis) => axis.reference ?? 0)}
            lensKey={lensKey}
          />
        </aside>
      </div>
    </section>
  );
}

