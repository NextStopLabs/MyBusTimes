"use client";

import React, { useState } from "react";
import { useMutation } from "convex/react";
import { api } from "@/convex/_generated/api";
import { Id } from "@/convex/_generated/dataModel";

export function MarkFlagReviewedButton({
  flagId,
  currentUserId,
}: {
  flagId: Id<"flaggedUsers">;
  currentUserId: Id<"users">;
}) {
  const markReviewed = useMutation(api.bans.markFlagReviewed);
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    setLoading(true);
    try {
      await markReviewed({ flagId, currentUserId });
      window.location.reload();
    } catch (e) {
      alert("Failed to mark as reviewed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      type="button"
      className="staff-btn"
      onClick={handleClick}
      disabled={loading}
    >
      {loading ? "..." : "Mark reviewed"}
    </button>
  );
}
