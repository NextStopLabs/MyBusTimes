"use client";

import { useState } from "react";
import { useMutation } from "convex/react";
import { api } from "@/convex/_generated/api";
import { Id } from "@/convex/_generated/dataModel";

export function BanDeviceButton({
  deviceId,
  currentUserId,
  isBanned,
}: {
  deviceId: Id<"devices">;
  currentUserId: Id<"users">;
  isBanned: boolean;
}) {
  const banDevice = useMutation(api.bans.banDevice);
  const unbanDevice = useMutation(api.bans.unbanDevice);
  const [loading, setLoading] = useState(false);

  const handleBan = async () => {
    const reason = prompt("Reason for banning this device:");
    if (!reason?.trim()) return;

    setLoading(true);
    try {
      await banDevice({ deviceId, reason: reason.trim(), bannedBy: currentUserId });
      window.location.reload();
    } catch (e) {
      alert("Failed to ban device");
    } finally {
      setLoading(false);
    }
  };

  const handleUnban = async () => {
    if (!confirm("Unban this device?")) return;
    
    setLoading(true);
    try {
      await unbanDevice({ deviceId });
      window.location.reload();
    } catch (e) {
      alert("Failed to unban device");
    } finally {
      setLoading(false);
    }
  };

  if (isBanned) {
    return (
      <button
        type="button"
        className="staff-btn-small staff-btn-success"
        onClick={handleUnban}
        disabled={loading}
      >
        {loading ? "..." : "Unban"}
      </button>
    );
  }

  return (
    <button
      type="button"
      className="staff-btn-small staff-btn-danger"
      onClick={handleBan}
      disabled={loading}
    >
      {loading ? "..." : "Ban"}
    </button>
  );
}

export function BanIpButton({
  ipId,
  currentUserId,
  isBanned,
}: {
  ipId: Id<"ips">;
  currentUserId: Id<"users">;
  isBanned: boolean;
}) {
  const banIp = useMutation(api.bans.banIp);
  const unbanIp = useMutation(api.bans.unbanIp);
  const [loading, setLoading] = useState(false);

  const handleBan = async () => {
    const reason = prompt("Reason for banning this IP:");
    if (!reason?.trim()) return;

    setLoading(true);
    try {
      await banIp({ ipId, reason: reason.trim(), bannedBy: currentUserId });
      window.location.reload();
    } catch (e) {
      alert("Failed to ban IP");
    } finally {
      setLoading(false);
    }
  };

  const handleUnban = async () => {
    if (!confirm("Unban this IP?")) return;
    
    setLoading(true);
    try {
      await unbanIp({ ipId });
      window.location.reload();
    } catch (e) {
      alert("Failed to unban IP");
    } finally {
      setLoading(false);
    }
  };

  if (isBanned) {
    return (
      <button
        type="button"
        className="staff-btn-small staff-btn-success"
        onClick={handleUnban}
        disabled={loading}
      >
        {loading ? "..." : "Unban"}
      </button>
    );
  }

  return (
    <button
      type="button"
      className="staff-btn-small staff-btn-danger"
      onClick={handleBan}
      disabled={loading}
    >
      {loading ? "..." : "Ban"}
    </button>
  );
}