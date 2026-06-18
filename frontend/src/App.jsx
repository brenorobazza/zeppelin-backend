import { useEffect, useRef, useState } from "react";
import { PlatformLayout } from "./components/PlatformLayout";
import { CreateAccountPage } from "./pages/CreateAccountPage";
import { AssessmentPage } from "./pages/AssessmentPage";
import { BenchmarkPage } from "./pages/BenchmarkPage";
import { DashboardPage } from "./pages/DashboardPage";
import { HistoryPage } from "./pages/HistoryPage";
import { LoginPage } from "./pages/LoginPage";
import { RecommendationsPage } from "./pages/RecommendationsPage";
import { ResultsPage } from "./pages/ResultsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { JoinOrganizationPage } from "./pages/JoinOrganizationPage";
import { OrganizationRegistrationPage } from "./pages/OrganizationRegistrationPage";
import {
  addOrganization,
  joinOrganization,
  registerAccount,
  submitOrganizationRegistration,
} from "./services/auth";
import { setCurrentOrganization } from "./services/settings";
import {
  getAnalyticsFiltersFromUrl,
  getFallbackAnalyticsBundle,
  loadAnalyticsBundle,
  updateAnalyticsFiltersInUrl
} from "./services/analytics";

// Lê o hash da URL e traduz isso para a "tela atual" da aplicação.
function getScreenFromHash() {
  const hash = window.location.hash.replace("#", "");
  if (hash === "create-account") return "create-account";
  if (hash === "join-organization") return "join-organization";
  if (hash === "organization-registration") return "organization-registration";
  if (hash === "dashboard") return "dashboard";
  if (hash === "assessment") return "assessment";
  if (hash === "results") return "results";
  if (hash === "recommendations") return "recommendations";
  if (hash === "history") return "history";
  if (hash === "benchmark") return "benchmark";
  if (hash === "settings") return "settings";
  return "login";
}

export default function App() {
  // Define qual página está visível neste momento.
  const [screen, setScreen] = useState(getScreenFromHash);

  // Guarda apenas o dado mínimo do usuário para apresentação no layout.
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem("zeppelin_user");
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  // Reúne os filtros que controlam a análise: empresa, ciclo e escopo.
  const [analyticsFilters, setAnalyticsFilters] = useState(getAnalyticsFiltersFromUrl);

  // Centraliza todos os dados usados pelas telas principais.
  // Também informa se a tela está carregando, se está usando mock e se ocorreu erro.
  const [analytics, setAnalytics] = useState(() => ({
    ...getFallbackAnalyticsBundle(),
    loading: false,
    usingMockData: true,
    error: ""
  }));

  const [refreshKey, setRefreshKey] = useState(0);
  const [disableGlobalSelectors, setDisableGlobalSelectors] = useState(false);
  const [registrationUserData, setRegistrationUserData] = useState(null);
  const [organizationRegistrationContext, setOrganizationRegistrationContext] = useState({
    mode: "signup",
    source: "join-organization",
    employeeId: null,
  });
  const lastScreenRef = useRef(screen);

  const allCycleOptions = analytics.meta?.cycleOptions || [];
  const completeCycleOptions = allCycleOptions.filter((cycle) => cycle.complete);
  const selectedCompleteCycleId =
    completeCycleOptions.some((cycle) => cycle.id === analyticsFilters.questionnaireId)
      ? analyticsFilters.questionnaireId
      : completeCycleOptions[completeCycleOptions.length - 1]?.id || "";

  function triggerRefresh() {
    setRefreshKey(k => k + 1);
  }

  useEffect(() => {
    if (lastScreenRef.current === "assessment" && screen !== "assessment") {
      triggerRefresh();
    }
    lastScreenRef.current = screen;
  }, [screen]);

  useEffect(() => {
    // Sincroniza a interface com a URL sempre que o usuário navega manualmente.
    function syncNavigationState() {
      setScreen(getScreenFromHash());
      setAnalyticsFilters(getAnalyticsFiltersFromUrl());
      setDisableGlobalSelectors(false); // Reset on navigation
    }

    window.addEventListener("hashchange", syncNavigationState);
    window.addEventListener("popstate", syncNavigationState);
    return () => {
      window.removeEventListener("hashchange", syncNavigationState);
      window.removeEventListener("popstate", syncNavigationState);
    };
  }, []);

  // Apenas estas telas dependem do backend analítico.
  const isPlatformScreen = [
    "dashboard",
    "assessment",
    "results",
    "recommendations",
    "history",
    "benchmark",
    "settings"
  ].includes(screen);

  useEffect(() => {
    if (!isPlatformScreen || !user) return;

    // Evita atualizar estado quando o usuário troca de tela antes da resposta terminar.
    let ignore = false;

    async function syncAnalytics() {
      setAnalytics((current) => ({
        ...current,
        loading: true,
        error: ""
      }));

      try {
        const bundle = await loadAnalyticsBundle(analyticsFilters);

        if (ignore) return;

        setAnalytics({
          ...bundle,
          loading: false,
          usingMockData: false,
          error: ""
        });
      } catch (error) {
        if (ignore) return;

        if (error.status === 401) {
          setUser(null);
          window.location.hash = "login";
          setScreen("login");
          return;
        }

        console.error("Failed to load analytics bundle:", error, { filters: analyticsFilters });
        setAnalytics({
          ...getFallbackAnalyticsBundle(),
          loading: false,
          usingMockData: true,
          error: error.message || "Failed to load analytics from backend."
        });
      }
    }

    syncAnalytics();

    return () => {
      ignore = true;
    };
  }, [isPlatformScreen, user, analyticsFilters.organizationId, analyticsFilters.questionnaireId, analyticsFilters.stageScope, refreshKey]);

  function goToLogin() {
    window.location.hash = "login";
    setScreen("login");
  }

  function goToCreateAccount() {
    window.location.hash = "create-account";
    setScreen("create-account");
  }

  function goToDashboard() {
    window.location.hash = "dashboard";
    setScreen("dashboard");
  }

  function goToJoinOrganization() {
    window.location.hash = "join-organization";
    setScreen("join-organization");
  }

  function goToOrganizationRegistration(context = {}) {
    setOrganizationRegistrationContext((current) => ({
      ...current,
      ...context,
    }));
    window.location.hash = "organization-registration";
    setScreen("organization-registration");
  }

  function mapOrganizationFormPayload(form) {
    return {
      organization_name: form.name,
      organization_country: form.country,
      years: form.years,
      state: form.state,
      organization_type: form.organizationType,
      organization_sector: form.sector,
      organization_size: form.size,
      target_audience: form.audience,
    };
  }

  async function handleFinalizeJoin({ accountData, organizationId }) {
    const registerPayload = await registerAccount({
      username: accountData.username,
      email: accountData.email,
      password: accountData.password,
      role: accountData.role || "",
    });

    await joinOrganization({
      employee_id: registerPayload.employee_id,
      organization_id: organizationId,
    });
  }

  async function handleOrganizationRegistrationSubmit({ form, mode, accountData }) {
    const organizationPayload = mapOrganizationFormPayload(form);

    if (mode === "signup") {
      const registerPayload = await registerAccount({
        username: accountData.username,
        email: accountData.email,
        password: accountData.password,
        role: accountData.role || "",
      });

      await submitOrganizationRegistration({
        employee_id: registerPayload.employee_id,
        ...organizationPayload,
      });

      return {
        message: "Registration completed successfully. Your account is now linked to an organization.",
      };
    }

    const payload = await addOrganization(organizationPayload);

    setUser((current) => {
      if (!current) return current;

      const alreadyExists = (current.organizations || []).some(
        (item) => String(item.id) === String(payload.organization_id)
      );

      const nextOrganizations = alreadyExists
        ? current.organizations || []
        : [
            ...(current.organizations || []),
            {
              id: payload.organization_id,
              name: payload.organization_name || form.name || "New Organization",
              organization_country:
                payload.organization_country || form.country || "Brazil",
              organization_sector:
                payload.organization_sector || form.sector || "",
            },
          ];

      const nextUser = {
        ...current,
        organizations: nextOrganizations,
      };

      localStorage.setItem("zeppelin_user", JSON.stringify(nextUser));
      return nextUser;
    });

    return {
      message: payload.message || "Organization created and linked to your profile.",
    };
  }

  function goToScreen(nextScreen) {
    window.location.hash = nextScreen;
    setScreen(nextScreen);
  }

  function logout() {
    setUser(null);
    localStorage.removeItem("zeppelin_user");
    const resetFilters = { organizationId: "", questionnaireId: "", stageScope: "all" };
    setAnalyticsFilters(resetFilters);
    updateAnalyticsFiltersInUrl(resetFilters);
    localStorage.removeItem("organization_id");
    goToLogin();
  }

  function updateUserProfile(nextProfile) {
    setUser((current) => {
      if (!current) return current;

      const nextUser = {
        ...current,
        username: nextProfile.username || current.username,
        fullName: nextProfile.fullName || current.fullName,
        email: nextProfile.email || current.email,
        employeeId: current.employeeId,
        accessToken: current.accessToken,
      };
      localStorage.setItem("zeppelin_user", JSON.stringify(nextUser));
      return nextUser;
    });
  }

  function updateAnalyticsFilters(nextFilters) {
    setAnalyticsFilters((current) => {
      const next = { ...current, ...nextFilters };
      // Mantém organização e ciclo no URL para suportar histórico por empresa/ciclo.
      updateAnalyticsFiltersInUrl(next);
      return next;
    });
  }

  function syncCurrentOrganization(nextOrganizationId, { persistCurrentOrganization = false } = {}) {
    const nextId = String(nextOrganizationId || "");
    if (!nextId) {
      return;
    }

    setUser((current) => {
      if (!current) return current;

      const nextUser = {
        ...current,
        currentOrganizationId: nextId,
      };
      localStorage.setItem("zeppelin_user", JSON.stringify(nextUser));
      return nextUser;
    });

    if (persistCurrentOrganization) {
      setCurrentOrganization(nextId).catch((error) => {
        console.error("Failed to persist current organization:", error);
      });
    }

    updateAnalyticsFilters({
      organizationId: nextId,
      questionnaireId: "",
    });
  }

  useEffect(() => {
    if (!user) return;

    const fallbackOrganizationId =
      user.currentOrganizationId ||
      (user.organizations && user.organizations.length > 0
        ? String(user.organizations[0].id)
        : "");

    if (!fallbackOrganizationId) {
      return;
    }

    if (String(analyticsFilters.organizationId || "") !== String(fallbackOrganizationId)) {
      updateAnalyticsFilters({
        organizationId: fallbackOrganizationId,
        questionnaireId: analyticsFilters.questionnaireId || "",
      });
    }
  }, [user, analyticsFilters.organizationId]);

  function handleOrganizationQuit(payload) {
    const removedId = String(payload?.organization_id || "");
    if (!removedId) {
      return;
    }

    let shouldLogout = false;
    let nextOrganizationId = "";

    setUser((current) => {
      if (!current) return current;

      const nextOrganizations = (current.organizations || []).filter(
        (organization) => String(organization.id) !== removedId
      );
      const nextCurrentOrganizationId =
        String(current.currentOrganizationId || "") === removedId
          ? (nextOrganizations[0] ? String(nextOrganizations[0].id) : "")
          : String(current.currentOrganizationId || "");

      const nextUser = {
        ...current,
        organizations: nextOrganizations,
        currentOrganizationId: nextCurrentOrganizationId || null,
      };
      localStorage.setItem("zeppelin_user", JSON.stringify(nextUser));

      if (nextOrganizations.length === 0) {
        shouldLogout = true;
      } else if (analyticsFilters.organizationId === removedId) {
        nextOrganizationId = String(nextOrganizations[0].id);
      }

      return nextUser;
    });

    if (shouldLogout) {
      logout();
      return;
    }

    if (nextOrganizationId) {
      updateAnalyticsFilters({
        organizationId: nextOrganizationId,
        questionnaireId: "",
      });
    }
  }

  function handleOrganizationJoined(payload) {
    const joinedId = String(payload?.organization_id || "");
    if (!joinedId) {
      return;
    }

    setUser((current) => {
      if (!current) return current;

      const alreadyLinked = (current.organizations || []).some(
        (organization) => String(organization.id) === joinedId
      );
      if (alreadyLinked) {
        return current;
      }

      const nextUser = {
        ...current,
        organizations: [
          ...(current.organizations || []),
          {
            id: payload.organization_id,
            name: payload.organization_name || `Organization ${payload.organization_id}`,
            organization_country: payload.organization_country || "Brazil",
            organization_sector: payload.organization_sector || "",
          },
        ],
        currentOrganizationId:
          current.currentOrganizationId || String(payload.organization_id),
      };

      localStorage.setItem("zeppelin_user", JSON.stringify(nextUser));
      return nextUser;
    });
  }

  function handleCurrentOrganizationChanged(payload) {
    const currentOrganizationId = String(payload?.organization_id || "");
    if (!currentOrganizationId) {
      return;
    }

    syncCurrentOrganization(currentOrganizationId);
  }

  // Cadastro fica fora do layout interno da plataforma.
  if (screen === "create-account") {
    return (
      <CreateAccountPage
        onBackToLogin={goToLogin}
        onAccountCreated={(accountData) => {
          setRegistrationUserData(accountData);
          goToJoinOrganization();
        }}
      />
    );
  }

  if (screen === "join-organization") {
    return (
      <JoinOrganizationPage
        accountData={registrationUserData}
        onCreateOrganization={() =>
          goToOrganizationRegistration({ mode: "signup", source: "join-organization" })
        }
        onFinalizeJoin={handleFinalizeJoin}
        onBackToLogin={goToLogin}
      />
    );
  }

  if (screen === "organization-registration") {
    return (
      <OrganizationRegistrationPage
        mode={organizationRegistrationContext.mode}
        accountData={registrationUserData}
        onSubmit={handleOrganizationRegistrationSubmit}
        onBack={
          organizationRegistrationContext.source === "settings"
            ? () => goToScreen("settings")
            : goToJoinOrganization
        }
        onSubmitSuccess={
          organizationRegistrationContext.mode === "signup"
            ? goToLogin
            : () => {
                triggerRefresh();
                goToScreen("settings");
              }
        }
      />
    );
  }

  // Mapeia cada tela principal para título, subtítulo e componente.
  const pageMap = {
    dashboard: {
      title: "Diagnostic Summary",
      subtitle: "",
      component: (
        <DashboardPage
          onNavigate={goToScreen}
          data={analytics.dashboard}
          loading={analytics.loading}
        />
      )
    },
    assessment: {
      title: "Assessment Questionnaire",
      subtitle: "Evaluate practices using a standardized maturity scale.",
      component: (
        <AssessmentPage
          organizationId={analyticsFilters.organizationId}
          questionnaireId={analyticsFilters.questionnaireId}
          organizations={user?.organizations || []}
          cycleOptions={analytics.meta?.cycleOptions || []}
          organizationName={analytics.meta?.organizationName}
          onChangeOrganization={(id) => updateAnalyticsFilters({ organizationId: id, questionnaireId: "" })}
          onCycleCreated={(id) => updateAnalyticsFilters({ questionnaireId: id })}
          onViewResults={(qId) => {
            updateAnalyticsFilters({ questionnaireId: qId });
            goToScreen("results");
          }}
          onFinish={() => {
            triggerRefresh();
            goToScreen("results");
          }}
          onExitForm={() => {
            triggerRefresh();
          }}
          onFormStateChange={setDisableGlobalSelectors}
        />
      )
    },
    results: {
      title: "Diagnostic Detail",
      subtitle: "",
      component: (
        <ResultsPage
          data={analytics.results}
          overview={analytics.dashboard}
          loading={analytics.loading}
        />
      )
    },
    recommendations: {
      title: "Recommendations",
      subtitle:
        "CI/CD practices below 60% become recommendations. `Adopt now` covers not adopted or abandoned practices. `Consolidate` covers project/product-level practices not yet established.",
      component: (
        <RecommendationsPage
          data={analytics.recommendations}
          loading={analytics.loading}
        />
      )
    },
    history: {
      title: "Evolution by Cycle",
      subtitle: "",
      component: (
        <HistoryPage
          data={analytics.history}
          loading={analytics.loading}
          filters={analyticsFilters}
        />
      )
    },
    benchmark: {
      title: "Benchmark Comparison",
      subtitle: "Compare your organization's maturity against peer cohorts.",
      component: (
        <BenchmarkPage
          filters={analyticsFilters}
          organizationOptions={user?.organizations || []}
        />
      )
    },
    settings: {
      title: "Organization Settings",
      subtitle: "Review current members and apply removal permissions within the selected organization.",
      component: (
        <SettingsPage
          organizationId={analyticsFilters.organizationId}
          organizationOptions={user?.organizations || []}
          currentOrganizationId={user?.currentOrganizationId || analyticsFilters.organizationId}
          onProfileUpdated={updateUserProfile}
          onSelfRemoved={logout}
          onOrganizationQuit={handleOrganizationQuit}
          onOrganizationJoined={handleOrganizationJoined}
          onCurrentOrganizationChanged={handleCurrentOrganizationChanged}
          canQuitOrganization={(analytics.history?.historySeries || []).length === 0}
          onCreateOrganization={() =>
            goToOrganizationRegistration({
              mode: "add-organization",
              source: "settings",
              employeeId: user?.employeeId || null,
            })
          }
        />
      )
    }
  };


  if (user && pageMap[screen]) {
    const page = pageMap[screen];
    const hideCycleSelector = screen === "assessment" || 
      screen === "benchmark" || screen === "settings";
    return (
        <PlatformLayout
        activePage={screen}
        title={page.title}
        subtitle={page.subtitle}
        organization={analytics.meta.organizationName}
        userName={user.fullName || user.username}
        onNavigate={goToScreen}
        onLogout={logout}
        organizationOptions={user.organizations || []}
        selectedOrganizationId={user?.currentOrganizationId || analyticsFilters.organizationId}
        onOrganizationChange={(value) => syncCurrentOrganization(value, { persistCurrentOrganization: true })}
        cycleOptions={completeCycleOptions}
        selectedCycleId={selectedCompleteCycleId}
        onCycleChange={(value) => updateAnalyticsFilters({ questionnaireId: value })}
        usingMockData={analytics.usingMockData}
        analyticsError={analytics.error}
        analyticsLoading={analytics.loading}
        disableGlobalSelectors={disableGlobalSelectors}
        hideCycleSelector = {hideCycleSelector}
      >
        {page.component}
      </PlatformLayout>
    );
  }

  // Caso nenhuma tela interna esteja ativa, a porta de entrada continua sendo o login.
  return (
    <LoginPage
      onCreateAccountClick={goToCreateAccount}
      onLoginSuccess={(loggedUser) => {
        // Inicializa o usuário com seu nome e lista de empresas vinculadas.
        const newUser = { 
          username: loggedUser?.username || "Alex Silva",
          fullName: loggedUser?.full_name || loggedUser?.username || "Alex Silva",
          email: loggedUser?.email || "",
          employeeId: loggedUser?.employee_id || null,
          currentOrganizationId: loggedUser?.current_organization_id
            ? String(loggedUser.current_organization_id)
            : null,
          isAdmin: Boolean(loggedUser?.is_admin),
          organizations: loggedUser?.organizations || []
        };
        setUser(newUser);
        localStorage.setItem("zeppelin_user", JSON.stringify(newUser));

        // Se o usuário possuir empresas, define a primeira como o contexto inicial.
        if (loggedUser?.organizations && loggedUser.organizations.length > 0) {
          const initialOrganizationId = loggedUser?.current_organization_id
            ? String(loggedUser.current_organization_id)
            : String(loggedUser.organizations[0].id);
          syncCurrentOrganization(initialOrganizationId);
        }

        goToDashboard();
      }}
    />
  );
  // debug logging removed
}
