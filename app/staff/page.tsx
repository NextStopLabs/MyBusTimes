import { fetchQuery } from "convex/nextjs";
import { api } from "@/convex/_generated/api";
import { Breadcrumb } from "@/app/components/Breadcrumb";
import Link from "next/link";

export default async function StaffPortalPage() {
  const [userCount, flaggedCount] = await Promise.all([
    fetchQuery(api.users.listUsers, {}).then((u) => u.length),
    fetchQuery(api.bans.listFlaggedUsers, { unreviewedOnly: true }).then((f) => f.length),
  ]);

  const breadcrumbs = [{ label: "Home", href: "/" },{ label: "Staff Portal", href: "/staff" }];

  return (
    <>
      <Breadcrumb items={breadcrumbs} />
      <h1>Staff Portal</h1>
      <p className="staff-muted">User management and moderation.</p>
      <div className="staff-dashboard-grid">
        <Link href="/staff/users" className="staff-dashboard-card">
          <h2>Users</h2>
          <p className="staff-dashboard-count">{userCount}</p>
          <p className="staff-dashboard-desc">View and manage all users</p>
        </Link>
        <Link href="/staff/flagged" className="staff-dashboard-card">
          <h2>Flagged</h2>
          <p className="staff-dashboard-count">{flaggedCount}</p>
          <p className="staff-dashboard-desc">Users flagged (e.g. used banned IP/device)</p>
        </Link>
      </div>
    </>
  );
}
