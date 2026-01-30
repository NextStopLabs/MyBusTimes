'use client'
import { useState } from 'react';
import { useMutation } from "convex/react";
import { api } from "@/convex/_generated/api";
import { Id } from "@/convex/_generated/dataModel";

export function BanUserForm({ 
  userId, 
  currentUserId,
  deviceCount,
  ipCount
}: { 
  userId: Id<"users">; 
  currentUserId: Id<"users">;
  deviceCount: number;
  ipCount: number;
}) {
  const [reason, setReason] = useState("");
  const [banDevices, setBanDevices] = useState(true);
  const [banIps, setBanIps] = useState(true);
  const [loading, setLoading] = useState(false);
  
  const createBan = useMutation(api.bans.createBan);

  const handleBan = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!reason.trim()) {
      alert("Please provide a ban reason");
      return;
    }

    if (!confirm(`Are you sure you want to ban this user?\n\nDevices: ${banDevices ? deviceCount : 0}\nIPs: ${banIps ? ipCount : 0}`)) {
      return;
    }

    setLoading(true);
    try {
      await createBan({
        userId,
        reason: reason.trim(),
        bannedBy: currentUserId,
        banDevices,
        banIps,
      });
      
      alert("User banned successfully");
      window.location.reload();
    } catch (error) {
      console.error("Ban error:", error);
      alert("Failed to ban user");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="staff-card staff-card--warn">
      <h2>⚠️ Ban User</h2>
      <form onSubmit={handleBan}>
        <div className="staff-form-group">
          <label style={{ display: "block", marginBottom: "0.25rem", fontWeight: "bold" }}>
            Ban Reason:
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Enter reason for ban..."
            required
          />
        </div>
        <div className="staff-form-group">
          <label>
            <input
              type="checkbox"
              checked={banDevices}
              onChange={(e) => setBanDevices(e.target.checked)}
            />
            <span>Ban all devices ({deviceCount} devices)</span>
          </label>
        </div>
        <div className="staff-form-group" style={{ marginBottom: "1.25rem" }}>
          <label>
            <input
              type="checkbox"
              checked={banIps}
              onChange={(e) => setBanIps(e.target.checked)}
            />
            <span>Ban all IP addresses ({ipCount} IPs)</span>
          </label>
        </div>
        <button type="submit" className="staff-btn staff-btn-danger" disabled={loading}>
          {loading ? "Banning..." : "🔨 Ban User"}
        </button>
      </form>
    </section>
  );
}