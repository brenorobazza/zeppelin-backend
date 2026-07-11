import "./platform-layout.css";
import { Settings as SettingsIcon } from "lucide-react";

function NavIcon({ children, className = "", viewBox = "0 0 24 24" }) {
  return (
    <span className={`nav-item-icon ${className}`.trim()} aria-hidden="true">
      <svg viewBox={viewBox} fill="none" stroke="currentColor" strokeWidth="1.9">
        {children}
      </svg>
    </span>
  );
}

// Itens fixos da navegacao principal.
const navItems = [
  {
    key: "dashboard",
    label: "Dashboard",
    icon: (
      <NavIcon>
        <path d="M3.5 10.5 12 4l8.5 6.5" />
        <path d="M5.5 9.5V20h13V9.5" />
        <path d="M9.5 20v-5.5h5V20" />
      </NavIcon>
    ),
  },
  {
    key: "assessment",
    label: "Assessment",
    icon: (
      <NavIcon>
        <rect x="6" y="3.5" width="12" height="17" rx="2.5" />
        <path d="M9 8h6" />
        <path d="M9 12h6" />
        <path d="M9 16h4" />
      </NavIcon>
    ),
  },
  {
    key: "results",
    label: "Results",
    icon: (
      <NavIcon>
        <path d="M5 19.5V10" />
        <path d="M12 19.5V5.5" />
        <path d="M19 19.5V13" />
        <path d="M3.5 19.5h17" />
      </NavIcon>
    ),
  },
  {
    key: "recommendations",
    label: "Recommendations",
    icon: (
      <NavIcon>
        <path d="M12 3.5a5.5 5.5 0 0 0-3.7 9.6c.9.8 1.5 1.8 1.7 2.9h4c.2-1.1.8-2.1 1.7-2.9A5.5 5.5 0 0 0 12 3.5Z" />
        <path d="M9.7 18h4.6" />
        <path d="M10.4 20.5h3.2" />
      </NavIcon>
    ),
  },
  {
    key: "evolution",
    label: "Evolution",
    icon: (
      <NavIcon>
        <path d="M4 12a8 8 0 1 0 2.3-5.7" />
        <path d="M4 5.5v4.5h4.5" />
        <path d="M12 8v4.2l2.8 1.8" />
      </NavIcon>
    ),
  },
  {
    key: "benchmark",
    label: "Benchmark",
    icon: (
      <NavIcon>
        <path d="M3 5.5v13c0 .8.7 1.5 1.5 1.5h15c.8 0 1.5-.7 1.5-1.5v-13" />
        <path d="M5.5 10l4-4 3 3 3.5-3.5" />
        <path d="M3 19.5h18" />
      </NavIcon>
    ),
  },
  {
    key: "settings",
    label: "Settings",
    icon: (
      <span className="nav-item-icon" aria-hidden="true">
        <SettingsIcon strokeWidth={2.15} />
      </span>
    ),
  },
];

export function PlatformLayout({
  activePage,
  title,
  subtitle,
  organization,
  userName,
  onNavigate,
  onLogout,
  organizationOptions = [],
  selectedOrganizationId = "",
  onOrganizationChange,
  cycleOptions = [],
  selectedCycleId = "",
  onCycleChange,
  usingMockData = false,
  analyticsError = "",
  analyticsLoading = false,
  disableGlobalSelectors = false,
  hideCycleSelector = false,
  children
}) {
  return (
    <div className="platform-shell">
      {/* Sidebar com identidade visual e acesso rápido às páginas centrais. */}
      <aside className="platform-sidebar">
        <div className="platform-logo">
          <img src="/branding/logo-zeppelin.png" alt="Zeppelin" />
          <p>CI/CD Maturity</p>
        </div>

        <nav>
          {navItems.map((item) => (
            <button
              key={item.key}
              type="button"
              className={item.key === activePage ? "active" : ""}
              onClick={() => onNavigate(item.key)}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <button className="logout-btn" type="button" onClick={onLogout}>
          Sign out
        </button>
      </aside>

      <section className="platform-main">
        {/* Topo com contexto da análise atual: empresa, página e ciclo selecionado. */}
        <header className="platform-topbar">
          <div>
            {organizationOptions.length > 1 && onOrganizationChange ? (
              <label className="topbar-control-inline">
                {disableGlobalSelectors ? (
                  <span className="org-label-fixed">{organization}</span>
                ) : (
                  <select 
                    value={selectedOrganizationId} 
                    onChange={(event) => onOrganizationChange(event.target.value)}
                    className="org-select"
                  >
                    {organizationOptions.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                )}
              </label>
            ) : (
              <p>{organization}</p>
            )}
            <h1>{title}</h1>
            <small>{subtitle}</small>
          </div>
          <div className="topbar-actions">
            {!hideCycleSelector && cycleOptions.length > 0 && onCycleChange ? (
              <label className="topbar-control">
                <span>Assessment cycle</span>
                {disableGlobalSelectors ? (
                  <span className="cycle-label-fixed">
                    {cycleOptions.find(c => c.id === selectedCycleId)?.label || "Latest cycle"}
                  </span>
                ) : (
                  <select value={selectedCycleId} onChange={(event) => onCycleChange(event.target.value)}>
                    <option value="">Latest cycle</option>
                    {cycleOptions.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.shortLabel} - {item.label}
                      </option>
                    ))}
                  </select>
                )}
              </label>
            ) : null}

            <div className="topbar-status">
              <div className="user-box">
                <span>{userName}</span>
              </div>
            </div>
          </div>
        </header>

        {analyticsError && usingMockData && !analyticsLoading && activePage !== "benchmark" ? (
          // Se a API falhar, deixamos claro para o usuario o motivo da troca para dados demo.
          <div className="platform-banner">
            Using fallback analytics bundle; some widgets may still load live data. Error: {analyticsError}
          </div>
        ) : null}

        {/* Cada pagina do TCC e renderizada dentro desta area principal. */}
        <div className="platform-content">{children}</div>
      </section>
    </div>
  );
}
