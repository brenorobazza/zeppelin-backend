import { useEffect, useMemo, useState } from "react";
import { Building2, Building, Plus, Trash2, ArrowLeftRight } from "lucide-react";
import { searchOrganizations } from "../services/auth";

export function OrganizationOverviewCard({
  organization,
  organizationOptions = [],
  currentOrganizationId = "",
  selectedOrganizationId = "",
  onSelectOrganization,
  onSetCurrentOrganization,
  currentUser,
  feedback,
  onCreateOrganization,
  onQuitOrganization,
  onJoinOrganization,
  isQuitting = false,
  joiningOrganizationId = null,
  switchingCurrentOrganizationId = null,
  canQuitOrganization = true,
  quitRestrictionReason = "",
}) {
  const mockOrganizations = [
    {
      id: String(organization?.id || "current"),
      name: organization?.name || "Acme Corporation",
      memberCount: organization?.member_count ?? 12,
      isCurrent: true,
    },
    {
      id: "mock-2",
      name: "Tech Solutions Inc.",
      memberCount: 8,
      isCurrent: false,
    },
    {
      id: "mock-3",
      name: "Global Enterprises",
      memberCount: 25,
      isCurrent: false,
    },
  ];

  const organizationItems = useMemo(
    () =>
      organizationOptions.length > 0
        ? organizationOptions.map((item) => ({
            id: String(item.id),
            name: item.name,
            sector: item.organization_sector || item.sector || "",
            isCurrent: Boolean(item.is_current) || String(item.id) === String(organization?.id),
          }))
        : mockOrganizations,
    [organizationOptions, organization?.id, organization?.name, organization?.member_count]
  );

  const normalizedSelectedId = String(selectedOrganizationId || "");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState("");

  const linkedOrganizationIds = useMemo(
    () => new Set(organizationItems.map((item) => String(item.id))),
    [organizationItems]
  );

  const orderedOrganizationItems = useMemo(() => {
    const currentId = String(currentOrganizationId || "");
    return [...organizationItems].sort((a, b) => {
      const aIsCurrent = String(a.id) === currentId;
      const bIsCurrent = String(b.id) === currentId;
      if (aIsCurrent === bIsCurrent) return 0;
      return aIsCurrent ? -1 : 1;
    });
  }, [currentOrganizationId, organizationItems]);

  const normalizedQuery = searchQuery.trim().toLowerCase();

  useEffect(() => {
    let ignore = false;

    async function loadOrganizations() {
      if (normalizedQuery.length < 3) {
        setSearchResults([]);
        setSearchError("");
        return;
      }

      setIsSearching(true);
      setSearchError("");

      try {
        const data = await searchOrganizations(normalizedQuery);
        if (ignore) return;

        const filteredResults = data.filter(
          (item) => !linkedOrganizationIds.has(String(item.id))
        );
        setSearchResults(filteredResults);
      } catch (err) {
        if (ignore) return;
        setSearchError(err.message || "Could not load organizations.");
      } finally {
        if (!ignore) {
          setIsSearching(false);
        }
      }
    }

    loadOrganizations();

    return () => {
      ignore = true;
    };
  }, [normalizedQuery, linkedOrganizationIds]);

  const quitTooltip = !normalizedSelectedId
    ? "Select an organization first."
    : !canQuitOrganization
      ? quitRestrictionReason || "You cannot quit this organization right now."
      : "Quit this organization.";

  return (
    <section className="panel">
      <div className="settings-overview-head">
        <div className="settings-overview-head__icon" aria-hidden="true">
          <Building2 size={20} strokeWidth={2.2} />
        </div>
        <div>
          <h3>Organization Profile</h3>
          <p>Manage your organization settings and preferences</p>
        </div>
      </div>

      {feedback ? <p className="feedback success">{feedback}</p> : null}

      <div className="settings-overview-body">
        <div className="settings-overview-group">
          <p className="settings-overview-label">Current Organizations</p>

          <div className="settings-organization-list" role="list" aria-label="Linked organizations">
            {orderedOrganizationItems.map((item) => {
              const optionId = String(item.id);
              const isCurrent = optionId === String(currentOrganizationId || "");
              const isSelected = optionId === normalizedSelectedId;

              return (
                <article
                  key={item.id}
                  className={`settings-organization-option ${isSelected ? "is-selected" : ""}`.trim()}
                  role="listitem"
                >
                  <button
                    type="button"
                    className="settings-organization-option__select"
                    onClick={() => {
                      if (typeof onSelectOrganization === "function") {
                        onSelectOrganization(optionId);
                      }
                      if (typeof onSetCurrentOrganization === "function") {
                        onSetCurrentOrganization(item);
                      }
                    }}
                  >
                    <div className="settings-organization-option__left">
                      <span
                        className={`settings-organization-option__radio ${isSelected ? "is-selected" : ""}`.trim()}
                        aria-hidden="true"
                      />

                      <span className="settings-organization-option__icon" aria-hidden="true">
                        <Building size={14} strokeWidth={2.2} />
                      </span>

                      <div>
                        <strong>{item.name}</strong>
                        <p>
                          {item.sector || "Sector unavailable"}
                        </p>
                      </div>
                    </div>
                  </button>

                  <div className="settings-organization-option__actions">
                    {isCurrent ? (
                      <span className="settings-organization-option__current">Current</span>
                    ) : (
                      <button
                        type="button"
                        className="btn-secondary-ui settings-organization-option__switch"
                        onClick={() => {
                          if (typeof onSetCurrentOrganization === "function") {
                            onSetCurrentOrganization(item);
                          }
                        }}
                        disabled={String(switchingCurrentOrganizationId) === optionId}
                      >
                        <ArrowLeftRight size={14} strokeWidth={2.3} />
                        {String(switchingCurrentOrganizationId) === optionId
                          ? "Setting..."
                          : "Set as current"}
                      </button>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        </div>

        <div className="settings-overview-group">
          <p className="settings-overview-label">Select Organization</p>

          <div className="settings-org-search-wrap">
            <input
              className="settings-org-search-input"
              type="text"
              value={searchQuery}
              onChange={(event) => {
                setSearchQuery(event.target.value);
              }}
              placeholder="Search organizations to join..."
            />
            <p className="settings-org-search-hint">Type at least 3 characters to see suggestions.</p>
          </div>

          <div className="settings-org-search-results" role="list" aria-label="Organizations available to join">
            {normalizedQuery.length < 3 ? (
              <p className="settings-org-search-empty">Start typing to search organizations.</p>
            ) : isSearching ? (
              <p className="settings-org-search-empty">Searching organizations...</p>
            ) : searchError ? (
              <p className="settings-org-search-error">{searchError}</p>
            ) : searchResults.length > 0 ? (
              searchResults.map((item) => (
                <article key={item.id} className="settings-org-search-card" role="listitem">
                  <div>
                    <strong>{item.name}</strong>
                    <p>{item.organization_sector || item.sector || "Sector unavailable"}</p>
                  </div>

                  <button
                    type="button"
                    className="btn-secondary-ui"
                    onClick={() => {
                      if (typeof onJoinOrganization === "function") {
                        onJoinOrganization(item);
                      }
                    }}
                    disabled={String(joiningOrganizationId) === String(item.id)}
                  >
                    <ArrowLeftRight size={14} strokeWidth={2.3} />
                    {String(joiningOrganizationId) === String(item.id)
                      ? "Joining..."
                      : "Join Organization"}
                  </button>
                </article>
              ))
            ) : (
              <p className="settings-org-search-empty">No organizations found outside your current memberships.</p>
            )}
          </div>
        </div>

        <div className="settings-overview-actions">
          <button
            className="btn-primary-ui"
            type="button"
            onClick={() => {
              if (typeof onCreateOrganization === "function") {
                onCreateOrganization();
              }
            }}
          >
            <Plus size={14} strokeWidth={2.4} />
            Create New Organization
          </button>

          <span className="settings-overview-actions__tooltip" title={quitTooltip}>
            <button
              className="btn-secondary-ui settings-overview-actions__danger"
              type="button"
              onClick={() => {
                if (typeof onQuitOrganization === "function") {
                  onQuitOrganization();
                }
              }}
              disabled={isQuitting || !normalizedSelectedId || !canQuitOrganization}
            >
              <Trash2 size={14} strokeWidth={2.4} />
              {isQuitting ? "Quitting..." : "Quit Organization"}
            </button>
          </span>
        </div>
      </div>

      <p className="settings-rule">
        Access level in this workspace: {currentUser.is_admin ? "Admin" : "Standard member"}.
      </p>
    </section>
  );
}
