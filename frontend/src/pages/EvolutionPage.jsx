import { BenchmarkComparisonCard } from "../components/BenchmarkComparisonCard";
import { BenchmarkStatePanel } from "../components/BenchmarkStatePanel";
import { Lock } from "lucide-react";
import { fallbackHistoryData } from "../mock/analyticsFallback";

const EVOLUTION_STAGE_METRICS = [
  {
    key: "agile",
    title: "Agile R&D evolution",
    label: "Agile R&D Organization"
  },
  {
    key: "ci",
    title: "CI evolution",
    label: "Continuous Integration"
  },
  {
    key: "cd",
    title: "CD evolution",
    label: "Continuous Deployment"
  },
  {
    key: "experimentation",
    title: "Experiment System evolution",
    label: "R&D as an Experiment System"
  }
];

function getCycleStageScore(cycle, stageKey) {
  if (!cycle) return null;
  if (cycle[stageKey] != null) return cycle[stageKey];
  return cycle.stages?.find((stage) => stage.key === stageKey)?.score ?? null;
}

function formatScore(value) {
  return value == null ? "-" : value;
}

export function EvolutionPage({ data, loading, filters }) {
  const view = data || fallbackHistoryData;
  const historySeries = view.historySeries || [];
  const completeHistorySeries = historySeries.filter((item) => item.complete);
  const hasHistory = Array.isArray(view.historySeries) && view.historySeries.length > 0;
  const hasCompleteHistory = completeHistorySeries.length > 0;
  const hasEnoughCompleteCycles = completeHistorySeries.length >= 2;
  const displayHistorySeries = completeHistorySeries;

  if (loading && !data) {
    return <section className="panel">Loading evolution...</section>;
  }

  if (view.selectedCycleEmpty) {
    return (
      <section className="panel">
        <p className="eyebrow">Evolution</p>
        <h3>No submitted answers for this cycle</h3>
        <p>No answers submitted yet.</p>
      </section>
    );
  }

  if (!hasHistory) {
    return (
      <section className="panel">
        <p className="eyebrow">Evolution</p>
        <h3>No evolution data available</h3>
        <p>No evolution data.</p>
      </section>
    );
  }

  if (!hasCompleteHistory) {
    return (
      <section className="panel">
        <p className="eyebrow">Evolution</p>
        <h3>No complete cycles available</h3>
        <p>No complete cycles yet.</p>
      </section>
    );
  }

  return (
    <>
      {hasEnoughCompleteCycles ? (
        <BenchmarkComparisonCard filters={filters} />
      ) : (
        <BenchmarkStatePanel
          tone="warning"
          badge="Insufficient Data"
          icon={<Lock size={24} strokeWidth={2.2} />}
          title="Two complete cycles required"
          message="Comparison needs two complete cycles."
          details="Minimum required: 2 complete cycles"
        />
      )}

      <section className="panel">
        <div className="section-head">
          <div>
            <h3>Scores for each cycle</h3>
          </div>
        </div>

        <div className="history-cycles history-cycles--three">
          {displayHistorySeries.map((item, index) => (
            <article key={`${item.cycle}-${index}`} className="history-cycle-card">
              <div className="history-cycle-card__head">
                <div>
                  <h4>{item.cycle}</h4>
                  <p>{item.period}</p>
                </div>
              </div>

              <div className="history-cycle-card__score">
                <span>Overall score</span>
                <strong>{item.overall}</strong>
              </div>

              <div className="progress">
                <span style={{ width: `${item.overall}%` }} />
              </div>

              <ul className="trend-list">
                {EVOLUTION_STAGE_METRICS.map((stage) => (
                  <li key={`${item.cycle}-${stage.key}`}>
                    <span>{stage.label}</span>
                    <strong>{formatScore(getCycleStageScore(item, stage.key))}</strong>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="section-head">
          <div>
            <h3>Adoption levels across cycles</h3>
            <p>Adoption levels by cycle.</p>
          </div>
        </div>

        <table className="table">
          <thead>
            <tr>
              <th>Cycle</th>
              <th>Not adopted</th>
              <th>Abandoned</th>
              <th>Project/Product</th>
              <th>Process</th>
              <th>Institutionalized</th>
            </tr>
          </thead>
          <tbody>
            {displayHistorySeries.map((item) => (
              <tr key={item.cycle}>
                <td>
                  <strong>{item.cycle}</strong>
                  <div>{item.period}</div>
                </td>
                <td>{item.adoptionLevels.notAdopted}</td>
                <td>{item.adoptionLevels.abandoned}</td>
                <td>{item.adoptionLevels.project}</td>
                <td>{item.adoptionLevels.process}</td>
                <td>{item.adoptionLevels.institutionalized}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
