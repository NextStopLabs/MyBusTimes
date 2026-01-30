import { fetchQuery } from "convex/nextjs";
import { api } from "@/convex/_generated/api";
import Link from "next/link";
import { MarkFlagReviewedButton } from "./MarkFlagReviewedButton";
import { headers } from "next/headers";
import { getCurrentUser } from "@/lib/auth";
import { Breadcrumb } from "@/app/components/Breadcrumb";
import { Id } from "@/convex/_generated/dataModel";

export default async function StaffFlaggedPage() {
  const headersList = await headers();
  const cookieHeader = headersList.get("cookie") || "";
  const currentUser = await getCurrentUser(cookieHeader);
  const flagged = await fetchQuery(api.bans.listFlaggedUsers, { unreviewedOnly: true });

  const breadcrumbs = [{ label: "Home", href: "/" },{ label: "Staff Portal", href: "/staff" },{ label: "Flagged Users", href: "/staff/flagged" }];

  return (
    <>
      <Breadcrumb items={breadcrumbs} />
      <h1>Flagged Users</h1>
      <p className="staff-muted">
        Users flagged for using a banned IP or device (e.g. different account on same network).
        Review and optionally ban from their user page.
      </p>
      {flagged.length === 0 ? (
        <p>No unreviewed flags.</p>
      ) : (
        <div className="staff-table-wrap">
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>Reason</th>
                <th>Flagged at</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {flagged.map((f) => (
                <tr key={f._id}>
                  <td>
                    <Link href={`/staff/user/${f.userId}`} style={{ fontWeight: 500 }}>
                      {f.username}
                    </Link>
                    <br />
                    <span className="staff-status-inactive" style={{ fontSize: "0.85em" }}>{f.email}</span>
                  </td>
                  <td>{f.reason}</td>
                  <td>{new Date(f.flaggedAt).toLocaleString()}</td>
                  <td>
                    <Link href={`/staff/user/${f.userId}`} style={{ marginRight: "12px" }}>
                      View user
                    </Link>
                    {currentUser?.id && (
                      <MarkFlagReviewedButton flagId={f._id} currentUserId={currentUser.id as Id<"users">} />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
