import { useEffect, useState } from "react";
import { addOrganization } from "../services/auth";
import {
  deleteOrganizationMember,
  loadOrganizationSettings,
  quitOrganizationMembership,
  setCurrentOrganization,
  updateCurrentUserProfile,
} from "../services/settings";
import { OrganizationOverviewCard } from "../components/OrganizationOverviewCard";

export function SettingsPage({
  organizationId,
  organizationOptions = [],
  onProfileUpdated,
  onSelfRemoved,
  onCreateOrganization,
  onOrganizationQuit,
  onOrganizationJoined,
  currentOrganizationId,
  onCurrentOrganizationChanged,
  canQuitOrganization: canQuitOrganizationProp,
}) {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const [deletingId, setDeletingId] = useState(null);
  const [isQuittingOrganization, setIsQuittingOrganization] = useState(false);
  const [joiningOrganizationId, setJoiningOrganizationId] = useState(null);
  const [switchingCurrentOrganizationId, setSwitchingCurrentOrganizationId] = useState(null);
  const [selectedOrganizationId, setSelectedOrganizationId] = useState(
    organizationId ? String(organizationId) : ""
  );
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const canQuitBecauseOfMembership = organizationOptions.length > 1;
  const canQuitBecauseOfQuestionnaires =
    typeof canQuitOrganizationProp === "boolean" ? canQuitOrganizationProp : true;
  const canQuitOrganization = canQuitBecauseOfMembership && canQuitBecauseOfQuestionnaires;
  const quitRestrictionReason = !canQuitBecauseOfMembership
    ? "You need to stay linked to at least one organization before quitting this one."
    : !canQuitBecauseOfQuestionnaires
      ? "You can't leave this organization due to submitted linked questionnaires."
      : "";
  const [profileForm, setProfileForm] = useState({
    firstName: "",
    lastName: "",
  });

  useEffect(() => {
    if (!organizationId) {
      setSettings(null);
      setError("");
      setFeedback("");
      return;
    }

    let ignore = false;

    async function syncSettings() {
      setLoading(true);
      setError("");
      setFeedback("");

      try {
        const payload = await loadOrganizationSettings(organizationId);
        if (!ignore) {
          setSettings(payload);
          setProfileForm({
            firstName: payload.current_user?.first_name || "",
            lastName: payload.current_user?.last_name || "",
          });
        }
      } catch (requestError) {
        if (!ignore) {
          setSettings(null);
          setError(requestError.message);
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }

    syncSettings();
    return () => {
      ignore = true;
    };
  }, [organizationId]);

  useEffect(() => {
    if (organizationId) {
      setSelectedOrganizationId(String(organizationId));
    }
  }, [organizationId]);

  function handleProfileChange(event) {
    const { name, value } = event.target;
    setProfileForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  async function handleProfileSubmit(event) {
    event.preventDefault();
    setError("");
    setFeedback("");
    setIsSavingProfile(true);

    try {
      const payload = await updateCurrentUserProfile({
        first_name: profileForm.firstName,
        last_name: profileForm.lastName,
      });

      setSettings((current) => {
        if (!current) return current;
        return {
          ...current,
          current_user: {
            ...current.current_user,
            first_name: payload.first_name,
            last_name: payload.last_name,
            full_name: payload.full_name,
          },
          members: current.members.map((member) =>
            member.is_current_user
              ? {
                  ...member,
                  name: payload.full_name,
                }
              : member
          ),
        };
      });
      setProfileForm({
        firstName: payload.first_name || "",
        lastName: payload.last_name || "",
      });
      setFeedback("Your name was updated.");

      if (typeof onProfileUpdated === "function") {
        onProfileUpdated({
          username: payload.username,
          fullName: payload.full_name,
          email: payload.email,
        });
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSavingProfile(false);
    }
  }

  async function handleDeleteMember(member) {
    const confirmationMessage = member.is_current_user
      ? "Remove your access to this organization?"
      : `Remove ${member.name} from this organization?`;

    if (!window.confirm(confirmationMessage)) {
      return;
    }

    setDeletingId(member.id);
    setError("");
    setFeedback("");

    try {
      const payload = await deleteOrganizationMember(member.id);

      if (payload.deleted_self) {
        setFeedback("Your access to this organization was removed.");
        if (typeof onSelfRemoved === "function") {
          onSelfRemoved();
        }
        return;
      }

      setSettings((current) => {
        if (!current) return current;
        return {
          ...current,
          organization: {
            ...current.organization,
            member_count: Math.max(0, (current.organization.member_count || 1) - 1),
          },
          members: current.members.filter((item) => item.id !== member.id),
        };
      });
      setFeedback(`${member.name} was removed from the organization.`);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setDeletingId(null);
    }
  }

  async function handleQuitOrganization() {
    if (!selectedOrganizationId) {
      setError("No organization selected.");
      return;
    }

    if (!window.confirm("Do you want to quit this organization?")) {
      return;
    }

    setIsQuittingOrganization(true);
    setError("");
    setFeedback("");

    try {
      const payload = await quitOrganizationMembership(selectedOrganizationId);
      setFeedback("Your membership in this organization was removed.");

      if (typeof onOrganizationQuit === "function") {
        onOrganizationQuit(payload);
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsQuittingOrganization(false);
    }
  }

  async function handleJoinOrganization(organizationToJoin) {
    if (!organizationToJoin?.id) {
      setError("Invalid organization selected.");
      return;
    }

    setJoiningOrganizationId(String(organizationToJoin.id));
    setError("");
    setFeedback("");

    try {
      const payload = await addOrganization({ organization_id: organizationToJoin.id });

      setFeedback(payload.message || "Organization linked to your profile.");
      if (typeof onOrganizationJoined === "function") {
        onOrganizationJoined({
          organization_id: payload.organization_id || organizationToJoin.id,
          organization_name: payload.organization_name || organizationToJoin.name,
          organization_country:
            payload.organization_country ||
            organizationToJoin.organization_country ||
            organizationToJoin.country ||
            "Brazil",
          organization_sector:
            payload.organization_sector ||
            organizationToJoin.organization_sector ||
            organizationToJoin.sector ||
            "",
        });
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setJoiningOrganizationId(null);
    }
  }

  async function handleSetCurrentOrganization(organizationToSet) {
    if (!organizationToSet?.id) {
      setError("Invalid organization selected.");
      return;
    }

    const nextId = String(organizationToSet.id);
    if (nextId === String(currentOrganizationId || "")) {
      return;
    }

    setSwitchingCurrentOrganizationId(nextId);
    setError("");
    setFeedback("");

    try {
      const payload = await setCurrentOrganization(nextId);
      setFeedback(payload.current_organization_name
        ? `Current organization updated to ${payload.current_organization_name}.`
        : "Current organization updated.");

      if (typeof onCurrentOrganizationChanged === "function") {
        onCurrentOrganizationChanged({
          organization_id: payload.current_organization_id || organizationToSet.id,
          organization_name: payload.current_organization_name || organizationToSet.name,
        });
      }

      setSelectedOrganizationId(nextId);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSwitchingCurrentOrganizationId(null);
    }
  }

  if (!organizationId) {
    return (
      <section className="panel">
        <div className="empty-state">
          Select an organization to review members and manage removal permissions.
        </div>
      </section>
    );
  }

  if (loading) {
    return (
      <section className="panel">
        <p>Loading organization settings...</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="panel">
        <p className="feedback error">{error}</p>
      </section>
    );
  }

  if (!settings) {
    return (
      <section className="panel">
        <div className="empty-state">Organization settings are not available yet.</div>
      </section>
    );
  }

  const { organization, current_user: currentUser, members } = settings;

  return (
    <>
      <OrganizationOverviewCard
        organization={organization}
        organizationOptions={organizationOptions}
        currentOrganizationId={currentOrganizationId}
        selectedOrganizationId={selectedOrganizationId}
        onSelectOrganization={setSelectedOrganizationId}
        onSetCurrentOrganization={handleSetCurrentOrganization}
        currentUser={currentUser}
        feedback={feedback}
        onCreateOrganization={onCreateOrganization}
        onQuitOrganization={handleQuitOrganization}
        onJoinOrganization={handleJoinOrganization}
        isQuitting={isQuittingOrganization}
        joiningOrganizationId={joiningOrganizationId}
        switchingCurrentOrganizationId={switchingCurrentOrganizationId}
        canQuitOrganization={canQuitOrganization}
        quitRestrictionReason={quitRestrictionReason}
      />

      <section className="panel">
        <div className="section-head">
          <div>
            {/* <p className="eyebrow">Your membership</p> */}
            <h3>Personal Information</h3>
            <p>This section identifies the account linked to the current session and lets you update your displayed name.</p>
          </div>
        </div>

        <div className="grid-3">
          <div className="context-card">
            <span>Full name</span>
            <strong>{currentUser.full_name || currentUser.username}</strong>
          </div>
          <div className="context-card">
            <span>Email</span>
            <strong>{currentUser.email || "Not available"}</strong>
          </div>
          <div className="context-card">
            <span>Username</span>
            <strong>{currentUser.username}</strong>
          </div>
        </div>

        <div className="grid-3" style={{ marginTop: "0.75rem" }}>
          <div className="context-card">
            <span>Organization role</span>
            <strong>{currentUser.role || "Not defined"}</strong>
          </div>
          <div className="context-card">
            <span>Permission</span>
            <strong>{currentUser.is_admin ? "Can remove any member" : "Can remove only self"}</strong>
          </div>
          <div className="context-card">
            <span>Account status</span>
            <strong>Active</strong>
          </div>
        </div>

        <form className="settings-profile-form" onSubmit={handleProfileSubmit}>
          <div className="grid-3">
            <label>
              First name
              <input
                name="firstName"
                type="text"
                value={profileForm.firstName}
                onChange={handleProfileChange}
                placeholder="First name"
              />
            </label>
            <label>
              Last name
              <input
                name="lastName"
                type="text"
                value={profileForm.lastName}
                onChange={handleProfileChange}
                placeholder="Last name"
              />
            </label>
            <div className="settings-profile-form__actions">
              <button className="btn-primary-ui" type="submit" disabled={isSavingProfile}>
                {isSavingProfile ? "Saving..." : "Save name"}
              </button>
            </div>
          </div>
        </form>
      </section>

    </>
  );
}
