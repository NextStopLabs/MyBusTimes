"use client";

import { useState } from "react";
import { useMutation } from "convex/react";
import { api } from "@/convex/_generated/api";
import { Id } from "@/convex/_generated/dataModel";

type UserRow = {
  _id: Id<"users">;
  isStaff: boolean;
  isSuperuser: boolean;
  active: boolean;
};

export function UnbanButton({
  banId,
  currentUserId,
}: {
  banId: Id<"bans">;
  currentUserId: Id<"users">;
}) {
  const deactivateBan = useMutation(api.bans.deactivateBan);
  const [loading, setLoading] = useState(false);

  const handleUnban = async () => {
    if (!confirm("Unban this user? They will be able to access the site again.")) return;
    setLoading(true);
    try {
      await deactivateBan({ banId, currentUserId });
      window.location.reload();
    } catch (e) {
      alert("Failed to unban");
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      type="button"
      className="staff-btn staff-btn-success"
      onClick={handleUnban}
      disabled={loading}
    >
      {loading ? "..." : "Unban user"}
    </button>
  );
}

export function EditUserForm({
  user,
  currentUserId,
}: {
  user: UserRow;
  currentUserId: Id<"users">;
}) {
  const updateUser = useMutation(api.users.updateUser);
  const [isStaff, setIsStaff] = useState(user.isStaff);
  const [isSuperuser, setIsSuperuser] = useState(user.isSuperuser);
  const [active, setActive] = useState(user.active);
  const [loading, setLoading] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await updateUser({
        currentUserId,
        targetUserId: user._id,
        isStaff,
        isSuperuser,
        active,
      });
      window.location.reload();
    } catch (e) {
      alert("Failed to update user");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="staff-card staff-card--info">
      <h2>Edit user</h2>
      <form onSubmit={handleSave}>
        <div className="staff-form-group">
          <label>
            <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
            <span>Active</span>
          </label>
        </div>
        <div className="staff-form-group">
          <label>
            <input type="checkbox" checked={isStaff} onChange={(e) => setIsStaff(e.target.checked)} />
            <span>Staff</span>
          </label>
        </div>
        <div className="staff-form-group" style={{ marginBottom: "1rem" }}>
          <label>
            <input type="checkbox" checked={isSuperuser} onChange={(e) => setIsSuperuser(e.target.checked)} />
            <span>Superuser</span>
          </label>
        </div>
        <button type="submit" className="staff-btn" disabled={loading}>
          {loading ? "Saving..." : "Save"}
        </button>
      </form>
    </section>
  );
}
