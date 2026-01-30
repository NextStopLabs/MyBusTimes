import { fetchQuery } from "convex/nextjs";
import { api } from "@/convex/_generated/api";
import { Breadcrumb } from "@/app/components/Breadcrumb";
import Link from "next/link";

export default async function StaffUsersPage() {
  const users = await fetchQuery(api.users.listUsers, {});

  const breadcrumbs = [{ label: "Home", href: "/" },{ label: "Staff Portal", href: "/staff" },{ label: "Users", href: "/staff/users" }];

  return (
    <>
      <Breadcrumb items={breadcrumbs} />
      <h1>All Users</h1>
      <p className="staff-muted">{users.length} user(s). Click a row to manage.</p>
      <div className="staff-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Status</th>
              <th style={{ textAlign: "center" }}>Staff</th>
              <th style={{ textAlign: "center" }}>Superuser</th>
              <th>Joined</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user._id}>
                <td>
                  <Link href={`/staff/user/${user._id}`} style={{ fontWeight: 500 }}>
                    {user.username}
                  </Link>
                </td>
                <td>{user.email}</td>
                <td>
                  {user.banned ? (
                    <span className="staff-status-banned">Banned</span>
                  ) : user.active ? (
                    <span className="staff-status-active">Active</span>
                  ) : (
                    <span className="staff-status-inactive">Inactive</span>
                  )}
                </td>
                <td style={{ textAlign: "center" }}>{user.isStaff ? "Yes" : "—"}</td>
                <td style={{ textAlign: "center" }}>{user.isSuperuser ? "Yes" : "—"}</td>
                <td>{new Date(user.joinDate).toLocaleDateString()}</td>
                <td>
                  <Link href={`/staff/user/${user._id}`}>View / Manage</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
