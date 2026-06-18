import { Filter, Sparkles } from "lucide-react";
import "./benchmark-filters.css";

const DEFAULT_FILTERS = {
  category: "",
  size: "",
  type: "",
  targetAudience: ""
};

const CATEGORY_OPTIONS = [
  { value: "", label: "Any section" },
  { value: "Finance", label: "Finance" },
  { value: "Healthcare", label: "Healthcare" },
  { value: "Retail", label: "Retail" },
  { value: "Industry", label: "Industry" },
  { value: "Education", label: "Education" },
  { value: "Technology", label: "Technology" }
];

const SIZE_OPTIONS = [
  { value: "", label: "Any size" },
  { value: "1-10", label: "1-10 employees" },
  { value: "11-50", label: "11-50 employees" },
  { value: "51-200", label: "51-200 employees" },
  { value: "201-500", label: "201-500 employees" },
  { value: "501-1000", label: "501-1000 employees" },
  { value: "1000+", label: "1000+ employees" }
];

const TYPE_OPTIONS = [
  { value: "", label: "Any type" },
  { value: "Private", label: "Private" },
  { value: "Public", label: "Public" },
  { value: "Startup", label: "Startup" },
  { value: "Software House", label: "Software House" },
  { value: "IT Organization", label: "IT Organization" },
  { value: "Hybrid", label: "Hybrid" }
];

const TARGET_AUDIENCE_OPTIONS = [
  { value: "", label: "Any audience" },
  { value: "B2B", label: "B2B" },
  { value: "B2C", label: "B2C" },
  { value: "B2G", label: "B2G" },
  { value: "Internal", label: "Internal" },
  { value: "Mixed", label: "Mixed" }
];

function selectOptionsForField(fieldName) {
  switch (fieldName) {
    case "category":
      return CATEGORY_OPTIONS;
    case "size":
      return SIZE_OPTIONS;
    case "type":
      return TYPE_OPTIONS;
    case "targetAudience":
      return TARGET_AUDIENCE_OPTIONS;
    default:
      return [];
  }
}

function normalizeDraftFilters(filters = {}) {
  return {
    ...DEFAULT_FILTERS,
    ...filters
  };
}

function FilterSelect({ id, label, value, onChange, options, disabled = false }) {
  return (
    <label className="benchmark-filters__field" htmlFor={id}>
      <span>{label}</span>
      <select id={id} value={value} onChange={onChange} disabled={disabled} className="benchmark-filters__select">
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

/**
 * BenchmarkFilters: refined cohort filter panel for the benchmark page.
 * It keeps the current organization context hidden and filters the peer cohort by Organization fields.
 */
export function BenchmarkFilters({
  filters = {},
  onApplyFilters = () => {},
  loading = false
}) {
  const draft = normalizeDraftFilters(filters);

  function updateField(fieldName, nextValue) {
    onApplyFilters({
      ...draft,
      [fieldName]: nextValue
    });
  }

  function handleReset() {
    onApplyFilters({
      ...DEFAULT_FILTERS
    });
  }

  return (
    <section className="benchmark-filters">
      <div className="benchmark-filters__hero">
        <div className="benchmark-filters__eyebrow">
          <Sparkles size={14} strokeWidth={2.2} />
          <span>Benchmark cohort filters</span>
        </div>
        <h2>Refine the peer cohort</h2>
        <p>
          The comparison is calculated as an AND combination of the selected organization criteria.
          Leave a field empty to keep it broad.
        </p>
      </div>

      <div className="benchmark-filters__panel">
        <div className="benchmark-filters__panel-head">
          <div>
            <p className="benchmark-filters__panel-kicker">
              <Filter size={14} strokeWidth={2.2} /> Cohort filters
            </p>
            <h3>Organization profile</h3>
          </div>
          <button type="button" className="benchmark-filters__ghost-btn" onClick={handleReset} disabled={loading}>
            Reset
          </button>
        </div>

        <div className="benchmark-filters__grid">
          <FilterSelect
            id="benchmark-category-select"
            label="Section"
            value={draft.category}
            onChange={(event) => updateField("category", event.target.value)}
            options={selectOptionsForField("category")}
            disabled={loading}
          />
          <FilterSelect
            id="benchmark-size-select"
            label="Size"
            value={draft.size}
            onChange={(event) => updateField("size", event.target.value)}
            options={selectOptionsForField("size")}
            disabled={loading}
          />
          <FilterSelect
            id="benchmark-type-select"
            label="Type"
            value={draft.type}
            onChange={(event) => updateField("type", event.target.value)}
            options={selectOptionsForField("type")}
            disabled={loading}
          />
          <FilterSelect
            id="benchmark-target-audience-select"
            label="Target audience"
            value={draft.targetAudience}
            onChange={(event) => updateField("targetAudience", event.target.value)}
            options={selectOptionsForField("targetAudience")}
            disabled={loading}
          />
        </div>

        <div className="benchmark-filters__actions">
          <p className="benchmark-filters__hint">
            Filters are applied as a cohort intersection across the selected organization profile.
          </p>
          <button type="button" className="benchmark-filters__apply-btn" onClick={() => onApplyFilters(draft)} disabled={loading}>
            {loading ? "Applying..." : "Apply filters"}
          </button>
        </div>
      </div>
    </section>
  );
}
