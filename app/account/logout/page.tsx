"use client";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";


export default function LogoutPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirmLogout() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/logout", { method: "POST" });
      if (res.ok) {
        window.location.href = "/";
      } else {
        const data = await res.json().catch(() => ({}));
        setError((data as any).message || "Logout failed");
        setLoading(false);
      }
    } catch (e) {
      setError("Network error");
      setLoading(false);
    }
  }

  return (
    <div className="max-w-md mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Confirm Logout</h1>

      <p className="mb-4">Are you sure you want to sign out?</p>

      {error && <p className="text-red-500 mb-2">{error}</p>}

      <div className="flex gap-3">
        <button
          className="bg-red-600 text-white px-4 py-2 rounded"
          onClick={confirmLogout}
          disabled={loading}
        >
          {loading ? "Signing out..." : "Sign out"}
        </button>

        <button
          className="border px-4 py-2 rounded"
          onClick={() => router.back()}
          disabled={loading}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
