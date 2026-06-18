import { getAuthHeaders } from "./authHelper";
import {
  fallbackAnalyticsMeta,
  fallbackDashboardData,
  fallbackHistoryData,
  fallbackRecommendationsData,
  fallbackResultsData
} from "../mock/analyticsFallback";

// A base da API vem do ambiente para permitir troca de servidor sem editar o código.
const API_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "";

// Padroniza a leitura das respostas do backend e transforma falhas em mensagens legíveis.
async function parseResponse(response, fallbackMessage) {
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message =
      data.error || data.detail || data.message || `${fallbackMessage} (status ${response.status})`;
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return data;
}

function normalizeQuestionnaireStatus(status) {
  return status === "Complete" ? "Complete" : "Under Assessment";
}

function isQuestionnaireComplete(status) {
  return status === "Complete";
}

function buildCoverageHeadline(representedStages, totalStages) {
  return `${representedStages || 0}/${totalStages || 0} stages`;
}

function buildCoverageDetail(missingStages = []) {
  return missingStages.length
    ? `Missing: ${missingStages.join(", ")}`
    : "All stages represented.";
}

// Converte os filtros da interface para query string.
function buildQuery(filters = {}) {
  const params = new URLSearchParams();

  if (filters.organizationId) params.set("organization_id", filters.organizationId);
  if (filters.questionnaireId) params.set("questionnaire_id", filters.questionnaireId);
  if (filters.stageScope) params.set("stage_scope", filters.stageScope);

  const query = params.toString();
  return query ? `?${query}` : "";
}

function buildComparisonQuery(filters = {}) {
  const params = new URLSearchParams();

  if (filters.organizationId) params.set("organization_id", filters.organizationId);
  if (filters.questionnaireId) params.set("questionnaire_id", filters.questionnaireId);
  if (filters.category) params.set("organization_category", filters.category);
  if (filters.size) params.set("organization_size", filters.size);
  if (filters.type) params.set("organization_type", filters.type);
  if (filters.targetAudience) params.set("target_audience", filters.targetAudience);
  if (filters.referenceMode) params.set("reference_mode", filters.referenceMode);
  if (filters.referenceQuestionnaireId) {
    params.set("reference_questionnaire_id", filters.referenceQuestionnaireId);
  }

  const query = params.toString();
  return query ? `?${query}` : "";
}

// Busca uma seção específica da camada analítica.
async function fetchAnalyticsSection(section, filters) {
  const query = buildQuery(filters);
  const response = await fetch(`${API_BASE}/api/questionnaire/analytics/${section}/${query}`, {
    credentials: "include"
  });

  return parseResponse(response, `Failed to load ${section} analytics.`);
}

async function fetchComparisonAnalytics(filters) {
  const query = buildComparisonQuery(filters);
  const response = await fetch(`${API_BASE}/api/questionnaire/analytics/comparison/${query}`, {
    credentials: "include"
  });

  return parseResponse(response, "Failed to load comparison analytics.");
}

async function fetchBenchmarkAnalytics(filters) {
  const query = buildComparisonQuery(filters);
  const response = await fetch(`${API_BASE}/api/questionnaire/analytics/benchmark/${query}`, {
    credentials: "include"
  });

  return parseResponse(response, "Failed to load benchmark analytics.");
}

// Busca o score de um estágio específico pelo nome curto.
function findStageScore(stageScores, shortName) {
  return stageScores.find((item) => item.short_name === shortName)?.score || 0;
}

// Converte um insight bruto do backend para um formato mais simples para os componentes.
function mapInsight(item) {
  return {
    id: item.id,
    questionId: item.question_id,
    stage: item.stage_short_name || item.stage_name || "",
    title: item.title,
    evidence: item.evidence,
    currentLevel: item.current_level,
    score: item.score
  };
}

// Faz a mesma padronização para as recomendações do roadmap.
function mapRecommendation(item) {
  return {
    id: item.id,
    questionId: item.question_id,
    questionDescription: item.question_description || "",
    stage: item.stage_short_name || item.stage_name || "",
    track: item.track,
    currentLevel: item.current_level,
    title: item.title,
    recommendation: item.recommendation,
    catalogRecommendation: item.catalog_recommendation || "",
    expectedImpact: item.expected_impact,
    priority: item.priority,
    nextStep: item.next_step,
    triggerRule: item.trigger_rule || "",
    referenceSource: item.reference_source || "",
    status: item.status,
    contextNote: item.context_note || "",
    dimensionName: item.dimension_name || "",
    elementName: item.element_name || ""
  };
}

// Normaliza os cards de score por estágio.
function mapStageScore(item) {
  return {
    key: item.key,
    name: item.name,
    shortName: item.short_name,
    score: item.score,
    currentLevel: item.current_level,
    answeredPractices: item.answered_practices,
    totalPractices: item.total_practices ?? item.answered_practices,
    strengthCount: item.strength_count,
    bottleneckCount: item.bottleneck_count
  };
}

// Prepara o payload bruto do dashboard para o formato que a tela entende.
function normalizeDashboard(payload) {
  const stageScores = payload.stage_scores.map(mapStageScore);

  return {
    selectedCycleEmpty: payload.selected_cycle_empty || false,
    maturitySnapshot: {
      organization: payload.organization.name,
      organizationType: payload.organization.type || "",
      cycleLabel: payload.cycle.label,
      answeredPractices: payload.snapshot.answered_practices,
      questionnaireStatus: normalizeQuestionnaireStatus(
        payload.snapshot.questionnaire_status
      ),
      isQuestionnaireComplete: isQuestionnaireComplete(
        payload.snapshot.questionnaire_status
      ),
      overallScore: payload.snapshot.overall_score,
      overallLevel: payload.snapshot.overall_level,
      ciScore: findStageScore(stageScores, "CI"),
      cdScore: findStageScore(stageScores, "CD"),
      recommendationCount: payload.snapshot.recommendation_count,
      executiveSummary: payload.snapshot.executive_summary,
      overallInterpretation: payload.snapshot.executive_summary
    },
    stageScores,
    adoptionLevels: payload.adoption_levels.map((item) => ({
      id: item.id,
      key: item.key,
      label: item.label,
      count: item.count,
      percentage: item.percentage,
      score: item.score
    })),
    strengths: payload.strengths.map(mapInsight),
    bottlenecks: payload.bottlenecks.map(mapInsight),
    recommendationsPreview: payload.recommendations_preview.map(mapRecommendation),
    overallDelta: payload.snapshot.overall_delta
  };
}

// Prepara os dados usados pela tela de resultados.
function normalizeResults(payload) {
  return {
    selectedCycleEmpty: payload.selected_cycle_empty || false,
    selectedCycleLabel: payload.cycle?.label || "",
    summary: {
      answeredPractices: payload.summary.answered_practices,
      questionnaireStatus: normalizeQuestionnaireStatus(
        payload.summary.questionnaire_status
      ),
      stageGap: payload.summary.stage_gap,
      calibratedProfile: payload.organization.type || "Current organization profile",
      overallScore: payload.summary.overall_score,
      overallLevel: payload.summary.overall_level
    },
    adoptionLevelStageOverview: {
      stages: (payload.adoption_level_stage_overview?.stages || []).map((item) => ({
        key: item.key,
        title: item.title
      })),
      levels: (payload.adoption_level_stage_overview?.levels || []).map((item) => ({
        key: item.key,
        label: item.label,
        weight: item.weight,
        agileCount: item.agile_count,
        ciCount: item.ci_count,
        cdCount: item.cd_count,
        experimentationCount: item.experimentation_count,
        organizationCount: item.organization_count
      })),
      totals: {
        agileCount: payload.adoption_level_stage_overview?.totals?.agile_count ?? 0,
        ciCount: payload.adoption_level_stage_overview?.totals?.ci_count ?? 0,
        cdCount: payload.adoption_level_stage_overview?.totals?.cd_count ?? 0,
        experimentationCount:
          payload.adoption_level_stage_overview?.totals?.experimentation_count ?? 0,
        organizationCount:
          payload.adoption_level_stage_overview?.totals?.organization_count ?? 0
      },
      degreeOfAdoption: {
        agileScore:
          payload.adoption_level_stage_overview?.degree_of_adoption?.agile_score ?? null,
        ciScore: payload.adoption_level_stage_overview?.degree_of_adoption?.ci_score ?? null,
        cdScore: payload.adoption_level_stage_overview?.degree_of_adoption?.cd_score ?? null,
        experimentationScore:
          payload.adoption_level_stage_overview?.degree_of_adoption?.experimentation_score ??
          null,
        organizationScore:
          payload.adoption_level_stage_overview?.degree_of_adoption?.organization_score ?? null
      }
    },
    stageScores: payload.stage_scores.map(mapStageScore),
    dimensionScoreOverview: {
      dimensions: (payload.dimension_score_overview?.dimensions || []).map((item) => ({
        key: item.key,
        name: item.name,
        agileScore: item.agile_score ?? null,
        ciScore: item.ci_score ?? null,
        cdScore: item.cd_score ?? null,
        experimentationScore: item.experimentation_score ?? null,
        organizationScore: item.organization_score ?? 0,
        agilePracticeCount: item.agile_practice_count ?? 0,
        ciPracticeCount: item.ci_practice_count ?? 0,
        cdPracticeCount: item.cd_practice_count ?? 0,
        experimentationPracticeCount: item.experimentation_practice_count ?? 0,
        practiceCount: item.practice_count ?? 0
      })),
      summary: {
        agileScore: payload.dimension_score_overview?.summary?.agile_score ?? null,
        ciScore: payload.dimension_score_overview?.summary?.ci_score ?? null,
        cdScore: payload.dimension_score_overview?.summary?.cd_score ?? null,
        experimentationScore:
          payload.dimension_score_overview?.summary?.experimentation_score ?? null,
        organizationScore:
          payload.dimension_score_overview?.summary?.organization_score ?? null
      }
    },
    dimensionOverview: {
      dimensions: (payload.dimension_overview?.dimensions || []).map((item) => ({
        key: item.key,
        name: item.name,
        agileCount: item.agile_count ?? 0,
        ciCount: item.ci_count ?? 0,
        cdCount: item.cd_count ?? 0,
        experimentationCount: item.experimentation_count ?? 0,
        agilePracticeCount: item.agile_practice_count,
        ciPracticeCount: item.ci_practice_count,
        cdPracticeCount: item.cd_practice_count,
        experimentationPracticeCount: item.experimentation_practice_count,
        practiceCount: item.practice_count
      })),
      summary: {
        agileCount: payload.dimension_overview?.summary?.agile_count ?? 0,
        ciCount: payload.dimension_overview?.summary?.ci_count ?? 0,
        cdCount: payload.dimension_overview?.summary?.cd_count ?? 0,
        experimentationCount: payload.dimension_overview?.summary?.experimentation_count ?? 0,
        statementCount: payload.dimension_overview?.summary?.statement_count ?? 0
      }
    },
    elementOverview: {
      rows: (payload.element_overview?.rows || []).map((item) => ({
        key: item.key,
        dimensionName: item.dimension_name,
        elementName: item.element_name,
        agileCount: item.agile_count ?? 0,
        ciCount: item.ci_count ?? 0,
        cdCount: item.cd_count ?? 0,
        experimentationCount: item.experimentation_count ?? 0,
        practiceCount: item.practice_count ?? 0,
        agileScore: item.agile_score ?? null,
        ciScore: item.ci_score ?? null,
        cdScore: item.cd_score ?? null,
        experimentationScore: item.experimentation_score ?? null,
        organizationScore: item.organization_score ?? null,
        agileScoreCount: item.agile_score_count ?? 0,
        ciScoreCount: item.ci_score_count ?? 0,
        cdScoreCount: item.cd_score_count ?? 0,
        experimentationScoreCount: item.experimentation_score_count ?? 0,
        scoreCount: item.score_count ?? 0
      })),
      summary: {
        agileCount: payload.element_overview?.summary?.agile_count ?? 0,
        ciCount: payload.element_overview?.summary?.ci_count ?? 0,
        cdCount: payload.element_overview?.summary?.cd_count ?? 0,
        experimentationCount:
          payload.element_overview?.summary?.experimentation_count ?? 0,
        statementCount: payload.element_overview?.summary?.statement_count ?? 0,
        agileScore: payload.element_overview?.summary?.agile_score ?? null,
        ciScore: payload.element_overview?.summary?.ci_score ?? null,
        cdScore: payload.element_overview?.summary?.cd_score ?? null,
        experimentationScore:
          payload.element_overview?.summary?.experimentation_score ?? null,
        organizationScore: payload.element_overview?.summary?.organization_score ?? null
      }
    },
    processOverview: {
      rows: (payload.process_overview?.rows || []).map((item) => ({
        key: item.key,
        name: item.name,
        agileScore: item.agile_score ?? null,
        ciScore: item.ci_score ?? null,
        cdScore: item.cd_score ?? null,
        experimentationScore: item.experimentation_score ?? null,
        organizationScore: item.organization_score ?? null,
        practiceCount: item.practice_count ?? 0
      })),
      summary: {
        processCount: payload.process_overview?.summary?.process_count ?? 0,
        agileScore: payload.process_overview?.summary?.agile_score ?? null,
        ciScore: payload.process_overview?.summary?.ci_score ?? null,
        cdScore: payload.process_overview?.summary?.cd_score ?? null,
        experimentationScore:
          payload.process_overview?.summary?.experimentation_score ?? null,
        organizationScore: payload.process_overview?.summary?.organization_score ?? null
      }
    },
    practiceThemes: payload.dimensions.map((item) => ({
      key: item.key,
      name: item.name,
      focus: item.focus,
      score: item.score,
      currentLevel: item.current_level,
      strength: item.strength,
      bottleneck: item.bottleneck,
      answeredPractices: item.answered_practices,
      strengthItem: item.strength_item ? mapInsight(item.strength_item) : null,
      bottleneckItem: item.bottleneck_item ? mapInsight(item.bottleneck_item) : null
    })),
    strengths: payload.strengths.map(mapInsight),
    bottlenecks: payload.bottlenecks.map(mapInsight),
    opportunities: payload.opportunities.map(mapRecommendation)
  };
}

// Agrupa recomendações nas trilhas do roadmap para leitura mais estratégica.
function normalizeRecommendations(payload) {
  const recommendationTracks = payload.tracks.map((lane) => ({
    key: lane.key,
    title: lane.title,
    description: lane.description,
    count: lane.count,
    items: lane.items.map(mapRecommendation)
  }));

  return {
    selectedCycleEmpty: payload.selected_cycle_empty || false,
    selectedCycleLabel: payload.cycle?.label || "",
    summary: {
      triggeredRecommendations: payload.summary.triggered_recommendations,
      adoptNowCount: payload.summary.adopt_now_count,
      consolidateCount: payload.summary.consolidate_count,
      answeredPractices: payload.summary.answered_practices ?? 0,
      expectedPractices: payload.summary.expected_practices ?? 0,
      representedStages: payload.summary.represented_stages ?? 0,
      totalStages: payload.summary.total_stages ?? 0,
      missingStages: payload.summary.missing_stages || [],
      coverageHeadline: buildCoverageHeadline(
        payload.summary.represented_stages,
        payload.summary.total_stages
      ),
      coverageDetail: buildCoverageDetail(payload.summary.missing_stages || []),
      questionnaireStatus: normalizeQuestionnaireStatus(
        payload.summary.questionnaire_status
      ),
      isQuestionnaireComplete: isQuestionnaireComplete(
        payload.summary.questionnaire_status
      )
    },
    recommendationTracks,
    recommendations: payload.items.map(mapRecommendation),
    availableStages: payload.filters.available_stages || [],
    availablePracticeGroups: payload.filters.available_practice_groups || [],
    availableTracks: payload.filters.available_tracks || [],
    availablePriorities: payload.filters.available_priorities || []
  };
}

// Resolve pequenas variações de nome nas chaves de histórico.
function getHistoryCount(cycle, key) {
  const adoptionLevels = cycle?.adoption_levels || {};
  if (adoptionLevels[key] != null) return adoptionLevels[key];

  const aliases = {
    "not-adopted": ["nao-adotada", "not-adopted"],
    abandoned: ["abandonada", "abandoned"],
    project: [
      "realizada-no-nivel-de-projeto-produto",
      "project-product-level",
      "realized-at-project-product-level"
    ],
    process: [
      "realizada-no-nivel-de-processo",
      "process-level",
      "realized-at-process-level"
    ],
    institutionalized: ["institucionalizada", "institutionalized"]
  };

  const candidates = aliases[key] || [key];
  const matchedKey = Object.keys(adoptionLevels).find((itemKey) =>
    candidates.includes(itemKey)
  );
  return matchedKey ? adoptionLevels[matchedKey] : 0;
}

const HISTORY_STAGE_DEFINITIONS = [
  {
    key: "agile",
    name: "Agile R&D Organization",
    shortName: "Agile",
    aliases: ["agile", "aro", "agile-rd-organization"]
  },
  {
    key: "ci",
    name: "Continuous Integration",
    shortName: "CI",
    aliases: ["ci", "continuous-integration"]
  },
  {
    key: "cd",
    name: "Continuous Deployment",
    shortName: "CD",
    aliases: ["cd", "continuous-deployment"]
  },
  {
    key: "experimentation",
    name: "R&D as an Experiment System",
    shortName: "Experimentation",
    aliases: ["experimentation", "exp", "experiment-system"]
  }
];

function normalizeHistoryStageValue(value = "") {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function buildHistoryStageValues(stageScores = []) {
  return HISTORY_STAGE_DEFINITIONS.map((definition) => {
    const source = stageScores.find((stage) => {
      const candidates = [stage.key, stage.name, stage.shortName].map(
        normalizeHistoryStageValue
      );

      return candidates.some((candidate) => definition.aliases.includes(candidate));
    });

    return {
      ...definition,
      score: source?.score ?? null,
      currentLevel: source?.currentLevel || ""
    };
  });
}

function findHistoryStageScore(stages, key) {
  return stages.find((stage) => stage.key === key)?.score ?? null;
}

// Converte o histórico bruto em um formato pronto para comparação entre ciclos.
function normalizeHistory(payload) {
  const historyCycles = (payload.cycles || []).filter(
    (item) => item.id != null && item.label !== "Aggregated snapshot"
  );

  const mapCyclesToSeries = (cycles = []) => {
    return cycles.map((item, index) => {
      const stageScores = item.stage_scores.map(mapStageScore);
      const stages = buildHistoryStageValues(stageScores);
      const agile = findHistoryStageScore(stages, "agile");
      const ci = findHistoryStageScore(stages, "ci");
      const cd = findHistoryStageScore(stages, "cd");
      const experimentation = findHistoryStageScore(stages, "experimentation");

      return {
        id: item.id ? String(item.id) : "",
        cycle: `Cycle ${index + 1}`,
        period: item.label,
        overall: item.overall_score,
        overallLevel: item.overall_level,
        complete: Boolean(item.complete),
        agile,
        ci,
        cd,
        experimentation,
        stages,
        recommendationCount: item.recommendation_count,
        delta: index === 0 ? null : item.overall_score - cycles[index - 1].overall_score,
        adoptionLevels: {
          notAdopted: getHistoryCount(item, "not-adopted"),
          abandoned: getHistoryCount(item, "abandoned"),
          project: getHistoryCount(item, "project"),
          process: getHistoryCount(item, "process"),
          institutionalized: getHistoryCount(item, "institutionalized")
        }
      };
    });
  };

  const historySeries = mapCyclesToSeries(historyCycles);

  return {
    insufficientData: historySeries.length < 2,
    historySeries
  };
}

function normalizeComparison(payload) {
  function formatCycleLabel(index, label) {
    const baseLabel = label || "Cycle";
    return `Cycle ${index + 1} - ${baseLabel}`;
  }

  const availableCycles = (payload.selection?.available_cycles || []).map((cycle, index) => ({
    id: cycle.id != null ? String(cycle.id) : "",
    label: cycle.label,
    displayLabel: formatCycleLabel(index, cycle.label),
    appliedDate: cycle.applied_date || null,
    answeredPractices: cycle.answered_practices || 0
  }));

  const currentCycleId = payload.selection?.current_cycle?.id ? String(payload.selection.current_cycle.id) : "";
  const referenceCycleId = payload.selection?.reference_cycle?.id ? String(payload.selection.reference_cycle.id) : "";

  const lensEntries = Object.entries(payload.lenses || {}).map(([key, lens]) => ({
    key,
    title: lens.title,
    subtitle: lens.subtitle,
    currentScore: lens.current_score,
    referenceScore: lens.reference_score,
    delta: lens.delta,
    axes: (lens.axes || []).map((axis) => ({
      key: axis.key,
      label: axis.label,
      current: axis.current,
      reference: axis.reference,
      delta: axis.delta
    }))
  }));

  const normalizedBenchmarkState = {
    code: payload.benchmark_state?.code || payload.selection?.benchmark_state?.code || "ready",
    title: payload.benchmark_state?.title || payload.selection?.benchmark_state?.title || "",
    message: payload.benchmark_state?.message || payload.selection?.benchmark_state?.message || "",
    errorCode:
      payload.benchmark_state?.error_code || payload.selection?.benchmark_state?.error_code || "",
    minCompanyThreshold:
      payload.benchmark_state?.min_company_threshold ||
      payload.selection?.benchmark_state?.min_company_threshold ||
      5,
    companyCount:
      payload.benchmark_state?.company_count ||
      payload.selection?.benchmark_state?.company_count ||
      payload.selection?.reference_context?.company_count ||
      0,
    snapshotCount:
      payload.benchmark_state?.snapshot_count ||
      payload.selection?.benchmark_state?.snapshot_count ||
      payload.selection?.reference_context?.snapshot_count ||
      0
  };

  return {
    organization: payload.organization,
    scope: payload.scope,
    benchmarkState: normalizedBenchmarkState,
    selection: {
      referenceMode: payload.selection?.reference_mode || "first-submission",
      referenceContext: payload.selection?.reference_context || null,
      currentCycle: {
        id: currentCycleId,
        label:
          availableCycles.find((cycle) => cycle.id === currentCycleId)?.displayLabel ||
          payload.selection?.current_cycle?.label ||
          "",
        appliedDate: payload.selection?.current_cycle?.applied_date || null,
        answeredPractices: payload.selection?.current_cycle?.answered_practices || 0
      },
      referenceCycle: {
        id: referenceCycleId,
        label:
          availableCycles.find((cycle) => cycle.id === referenceCycleId)?.displayLabel ||
          payload.selection?.reference_cycle?.label ||
          "",
        appliedDate: payload.selection?.reference_cycle?.applied_date || null,
        answeredPractices: payload.selection?.reference_cycle?.answered_practices || 0
      },
      availableCycles
    },
    summary: {
      currentScore: payload.summary?.current_score ?? 0,
      referenceScore: payload.summary?.reference_score ?? 0,
      delta: payload.summary?.delta ?? 0,
      currentAnsweredPractices: payload.summary?.current_answered_practices ?? 0,
      referenceAnsweredPractices: payload.summary?.reference_answered_practices ?? 0
    },
    lenses: lensEntries.reduce((accumulator, item) => {
      accumulator[item.key] = item;
      return accumulator;
    }, {}),
    lensOptions: lensEntries
  };
}

// O layout principal precisa de metadados globais, como nome da empresa e lista de ciclos.
function normalizeMeta(dashboardPayload, historyPayload) {
  return {
    organizationName: dashboardPayload.organization.name,
    organizationType: dashboardPayload.organization.type || "",
    selectedCycleLabel: dashboardPayload.cycle.label,
    cycleOptions: historyPayload.cycles
      .filter((item) => item.id != null)
      .map((item, index) => ({
        id: String(item.id),
        label: item.label,
        shortLabel: `Cycle ${index + 1}`,
        answeredPractices: item.answered_practices || 0,
        complete: Boolean(item.complete)
      }))
  };
}

// Carrega todas as seções em paralelo para manter consistência entre as páginas.
export async function loadAnalyticsBundle(filters = {}) {
  const [dashboardPayload, resultsPayload, recommendationsPayload, historyPayload] =
    await Promise.all([
      fetchAnalyticsSection("dashboard", filters),
      fetchAnalyticsSection("results", filters),
      fetchAnalyticsSection("recommendations", filters),
      fetchAnalyticsSection("history", filters)
    ]);

  return {
    meta: normalizeMeta(dashboardPayload, historyPayload),
    dashboard: normalizeDashboard(dashboardPayload),
    results: normalizeResults(resultsPayload),
    recommendations: normalizeRecommendations(recommendationsPayload),
    history: normalizeHistory(historyPayload)
  };
}

// Carrega a comparação agregada usada pelo card de benchmark.
export async function loadComparisonAnalytics(filters = {}) {
  const payload = await fetchComparisonAnalytics(filters);
  return normalizeComparison(payload);
}

// Carrega a comparação de benchmark real usada pelo BenchmarkPage.
export async function loadBenchmarkAnalytics(filters = {}) {
  const payload = await fetchBenchmarkAnalytics(filters);
  return normalizeComparison(payload);
}

// Entrega um conjunto de dados de demonstração quando o backend não estiver disponível.
export function getFallbackAnalyticsBundle() {
  return {
    meta: fallbackAnalyticsMeta,
    dashboard: fallbackDashboardData,
    results: fallbackResultsData,
    recommendations: fallbackRecommendationsData,
    history: fallbackHistoryData
  };
}

// Lê da URL o contexto atual da análise.
export function getAnalyticsFiltersFromUrl() {
  const url = new URL(window.location.href);
  return {
    organizationId: url.searchParams.get("organization_id") || "",
    questionnaireId: url.searchParams.get("questionnaire_id") || "",
    stageScope: url.searchParams.get("stage_scope") || "all"
  };
}

// Atualiza a URL sem recarregar a página, preservando o contexto escolhido pelo usuário.
export function updateAnalyticsFiltersInUrl(filters) {
  const url = new URL(window.location.href);
  const values = {
    organization_id: filters.organizationId,
    questionnaire_id: filters.questionnaireId,
    stage_scope: filters.stageScope && filters.stageScope !== "all" ? filters.stageScope : ""
  };

  Object.entries(values).forEach(([key, value]) => {
    if (value) {
      url.searchParams.set(key, value);
    } else {
      url.searchParams.delete(key);
    }
  });

  window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
}
