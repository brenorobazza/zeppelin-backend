/**
 * Payload mock para a comparação de benchmark.
 * Estrutura baseada no contrato esperado por normalizeComparison() em services/analytics.js.
 * O reference payload representa um agregado de snapshots de organizações diferentes.
 */

const benchmarkProfiles = {
  all: {
    referenceLabel: "Peer average",
    referenceAnsweredPractices: 184,
    companyCount: 18,
    snapshotCount: 84,
    summary: {
      current_score: 78,
      reference_score: 67,
      delta: 11,
      current_answered_practices: 42,
      reference_answered_practices: 184
    },
    lenses: {
      eye: {
        current_score: 76,
        reference_score: 66,
        delta: 10,
        axes: [
          { key: "development", label: "Development", current: 85, reference: 79, delta: 6 },
          { key: "quality", label: "Quality", current: 78, reference: 70, delta: 8 },
          { key: "software_mgt", label: "Software Mgt", current: 76, reference: 68, delta: 8 },
          { key: "technical_solution", label: "Technical Solution", current: 88, reference: 79, delta: 9 },
          { key: "knowledge", label: "Knowledge", current: 74, reference: 66, delta: 8 },
          { key: "business", label: "Business", current: 70, reference: 62, delta: 8 },
          { key: "user_customer", label: "User/Customer", current: 72, reference: 64, delta: 8 }
        ]
      },
      sth: {
        current_score: 79,
        reference_score: 66,
        delta: 13,
        axes: [
          { key: "ci", label: "CI", current: 76, reference: 69, delta: 7 },
          { key: "cd", label: "CD", current: 69, reference: 63, delta: 6 },
          { key: "exp", label: "EXP", current: 72, reference: 64, delta: 8 },
          { key: "aro", label: "ARO", current: 67, reference: 60, delta: 7 }
        ]
      }
    }
  },
  CI: {
    referenceLabel: "CI-focused peers",
    referenceAnsweredPractices: 122,
    companyCount: 13,
    snapshotCount: 47,
    summary: {
      current_score: 81,
      reference_score: 70,
      delta: 11,
      current_answered_practices: 42,
      reference_answered_practices: 122
    },
    lenses: {
      eye: {
        current_score: 80,
        reference_score: 71,
        delta: 9,
        axes: [
          { key: "development", label: "Development", current: 88, reference: 83, delta: 5 },
          { key: "quality", label: "Quality", current: 80, reference: 73, delta: 7 },
          { key: "software_mgt", label: "Software Mgt", current: 79, reference: 72, delta: 7 },
          { key: "technical_solution", label: "Technical Solution", current: 89, reference: 81, delta: 8 },
          { key: "knowledge", label: "Knowledge", current: 77, reference: 70, delta: 7 },
          { key: "business", label: "Business", current: 72, reference: 65, delta: 7 },
          { key: "user_customer", label: "User/Customer", current: 74, reference: 67, delta: 7 }
        ]
      },
      sth: {
        current_score: 78,
        reference_score: 69,
        delta: 9,
        axes: [
          { key: "ci", label: "CI", current: 77, reference: 72, delta: 5 },
          { key: "cd", label: "CD", current: 70, reference: 64, delta: 6 },
          { key: "exp", label: "EXP", current: 73, reference: 68, delta: 5 },
          { key: "aro", label: "ARO", current: 68, reference: 63, delta: 5 }
        ]
      }
    }
  },
  CD: {
    referenceLabel: "Delivery-focused peers",
    referenceAnsweredPractices: 136,
    companyCount: 11,
    snapshotCount: 39,
    summary: {
      current_score: 76,
      reference_score: 64,
      delta: 12,
      current_answered_practices: 42,
      reference_answered_practices: 136
    },
    lenses: {
      eye: {
        current_score: 74,
        reference_score: 63,
        delta: 11,
        axes: [
          { key: "development", label: "Development", current: 84, reference: 74, delta: 10 },
          { key: "quality", label: "Quality", current: 76, reference: 67, delta: 9 },
          { key: "software_mgt", label: "Software Mgt", current: 75, reference: 66, delta: 9 },
          { key: "technical_solution", label: "Technical Solution", current: 87, reference: 74, delta: 13 },
          { key: "knowledge", label: "Knowledge", current: 72, reference: 64, delta: 8 },
          { key: "business", label: "Business", current: 68, reference: 60, delta: 8 },
          { key: "user_customer", label: "User/Customer", current: 70, reference: 62, delta: 8 }
        ]
      },
      sth: {
        current_score: 77,
        reference_score: 65,
        delta: 12,
        axes: [
          { key: "ci", label: "CI", current: 75, reference: 66, delta: 9 },
          { key: "cd", label: "CD", current: 68, reference: 60, delta: 8 },
          { key: "exp", label: "EXP", current: 71, reference: 63, delta: 8 },
          { key: "aro", label: "ARO", current: 66, reference: 59, delta: 7 }
        ]
      }
    }
  }
};

function buildFilterSummary(filters = {}) {
  const entries = [
    ["category", filters.category],
    ["size", filters.size],
    ["type", filters.type],
    ["target audience", filters.targetAudience]
  ].filter(([, value]) => Boolean(value));

  if (!entries.length) {
    return "No benchmark filters selected";
  }

  return entries.map(([label, value]) => `${label}: ${value}`).join(" · ");
}

function buildSelection(filters = {}) {
  const profileKey = "all";
  const profile = benchmarkProfiles[profileKey];

  return {
    reference_mode: "peer-aggregate",
    reference_context: {
      label: `${profile.referenceLabel} · ${buildFilterSummary(filters)}`,
      company_count: profile.companyCount,
      snapshot_count: profile.snapshotCount,
      stage_scope: profileKey
    },
    current_cycle: {
      id: 3,
      label: "December 2025",
      applied_date: "2025-12-15",
      answered_practices: 42
    },
    reference_cycle: {
      id: `peer-group-${profileKey}`,
      label: profile.referenceLabel,
      applied_date: null,
      answered_practices: profile.referenceAnsweredPractices
    },
    available_cycles: [
      {
        id: 1,
        label: "April 2024",
        applied_date: "2024-04-10",
        answered_practices: 38
      },
      {
        id: 2,
        label: "August 2024",
        applied_date: "2024-08-22",
        answered_practices: 40
      },
      {
        id: 3,
        label: "December 2025",
        applied_date: "2025-12-15",
        answered_practices: 42
      },
      {
        id: 4,
        label: "May 2026",
        applied_date: "2026-05-05",
        answered_practices: 45
      }
    ]
  };
}

function buildBenchmarkState(filters = {}) {
  const minCompanyThreshold = 5;

  if (filters.category === "Education" && filters.size === "1-10") {
    return {
      code: "insufficient_data",
      title: "Insufficient data for comparison",
      message: "The selected peer group has only 3 companies. Benchmark requires at least 5 companies.",
      error_code: "BENCHMARK_LOW_PEER_COUNT",
      min_company_threshold: minCompanyThreshold,
      company_count: 3,
      snapshot_count: 9
    };
  }

  if (filters.category === "Retail" && filters.targetAudience === "B2G") {
    return {
      code: "empty_results",
      title: "No data found",
      message: "No benchmark snapshots match the selected filters.",
      error_code: "BENCHMARK_EMPTY_RESULT",
      min_company_threshold: minCompanyThreshold,
      company_count: 0,
      snapshot_count: 0
    };
  }

  if (filters.type === "Hybrid" && filters.targetAudience === "Internal") {
    return {
      code: "error",
      title: "Unable to load benchmark data",
      message: "A server-side issue occurred while building the peer group.",
      error_code: "ERR_DATA_FETCH_FAILED_500",
      min_company_threshold: minCompanyThreshold,
      company_count: 0,
      snapshot_count: 0
    };
  }

  return {
    code: "ready",
    title: "Benchmark ready",
    message: "Benchmark loaded successfully with enough peer companies.",
    error_code: "",
    min_company_threshold: minCompanyThreshold,
    company_count: benchmarkProfiles.all.companyCount,
    snapshot_count: benchmarkProfiles.all.snapshotCount
  };
}

export function loadComparisonMock(filters = {}) {
  const profileKey = "all";
  const profile = benchmarkProfiles[profileKey];
  const filterSummary = buildFilterSummary(filters);
  const benchmarkState = buildBenchmarkState(filters);

  return {
    organization: {
      id: filters.organizationId || "org-001",
      name: "TechCorp Solutions"
    },
    scope: profileKey,
    benchmark_state: benchmarkState,
    selection: buildSelection(filters),
    summary: profile.summary,
    lenses: {
      eye: {
        key: "eye",
        title: "Eye",
        subtitle: `Compare against peer organizations matched by the active filters. ${filterSummary}.`,
        ...profile.lenses.eye
      },
      sth: {
        key: "sth",
        title: "StH",
        subtitle: `Compare against peer organizations matched by the active filters. ${filterSummary}.`,
        ...profile.lenses.sth
      }
    }
  };
}
