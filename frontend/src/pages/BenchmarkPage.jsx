import { useEffect, useState } from "react";
import { BenchmarkFilters } from "../components/BenchmarkFilters";
import { BenchmarkComparisonCard } from "../components/BenchmarkComparisonCard";
import "./benchmark-page.css";

/**
 * BenchmarkPage: Displays benchmark comparison against cohorts.
 * Uses the backend benchmark endpoint for cohort comparisons.
 */
export function BenchmarkPage({ filters = {} }) {
  const baseFilters = {
    organizationId: filters.organizationId || "",
    category: "",
    size: "",
    type: "",
    targetAudience: ""
  };

  const [appliedFilters, setAppliedFilters] = useState({
    ...baseFilters
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setAppliedFilters((current) => ({
      ...baseFilters,
      organizationId: filters.organizationId || current.organizationId || ""
    }));
  }, [filters.organizationId]);

  function handleFiltersApply(nextFilters) {
    setLoading(true);
    // Simulate async operation; in real usage, this would trigger a backend fetch.
    setTimeout(() => {
      setAppliedFilters((current) => ({
        ...current,
        ...nextFilters,
        organizationId: current.organizationId || filters.organizationId || ""
      }));
      setLoading(false);
    }, 300);
  }

  function handleClearBenchmarkFilters() {
    setAppliedFilters((current) => ({
      ...baseFilters,
      organizationId: current.organizationId || filters.organizationId || ""
    }));
  }

  return (
    <div className="benchmark-page">
      {/* Topbar filter area */}
      <BenchmarkFilters
        filters={appliedFilters}
        onApplyFilters={handleFiltersApply}
        loading={loading}
      />

      {/* Main content area with the comparison card */}
      <section className="benchmark-page__content">
        <BenchmarkComparisonCard
          className="benchmark-page__card"
          comparisonVariant="benchmark"
          onClearFilters={handleClearBenchmarkFilters}
          onAdjustFilters={handleClearBenchmarkFilters}
          filters={{
            organizationId: appliedFilters.organizationId,
            category: appliedFilters.category,
            size: appliedFilters.size,
            type: appliedFilters.type,
            targetAudience: appliedFilters.targetAudience
          }}
        />
      </section>
    </div>
  );
}
