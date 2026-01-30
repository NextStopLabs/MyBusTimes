import { fetchQuery } from "convex/nextjs";
import { api } from "@/convex/_generated/api";
import { Id } from "@/convex/_generated/dataModel";
import { headers } from "next/headers";
import { getCurrentUser } from "@/lib/auth";
import { redirect } from "next/navigation";
import { BanUserForm } from "./BanUserForm";
import { Breadcrumb } from "@/app/components/Breadcrumb";
import { UnbanButton, EditUserForm } from "./StaffUserActions";
import { BanDeviceButton, BanIpButton } from "./DeviceIpActions";
import Link from "next/link";

export default async function StaffUserPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  
  // Check if current user is staff
  const headersList = await headers();
  const cookieHeader = headersList.get("cookie") || "";
  const currentUser = await getCurrentUser(cookieHeader);

  if (!currentUser?.isStaff && !currentUser?.isSuperuser) {
    redirect("/");
  }

  // Fetch user data
  const userId = id as Id<"users">;
  const user = await fetchQuery(api.users.getById, { userId });
  const devices = await fetchQuery(api.users.getUserDevices, { userId });
  const ips = await fetchQuery(api.users.getUserIps, { userId });
  const bans = await fetchQuery(api.users.getUserBans, { userId });

  // Check ban status for each device and IP
  const deviceBanStatuses = await Promise.all(
    devices.map(d => fetchQuery(api.bans.getDeviceBanStatus, { deviceId: d._id }))
  );
  const ipBanStatuses = await Promise.all(
    ips.map(ip => fetchQuery(api.bans.getIpBanStatus, { ipId: ip._id }))
  );

  if (!user) {
    return <div>User not found</div>;
  }

  const activeBan = bans.find((b) => b.active);

  const breadcrumbs = [{ label: "Home", href: "/" },{ label: "Staff Portal", href: "/staff" },{ label: "Users", href: "/staff/users" }, { label: user.username, href: `/staff/user/${userId}` }];

  return (
    <>
      <Breadcrumb items={breadcrumbs} />
      <Link href="/staff/users">← Back to Users</Link>
      <h1>User Management: {user.username}</h1>

      <section className="staff-card">
        <h2>User Information</h2>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <tbody>
            <tr>
              <td style={{ padding: "0.5em 0.75em 0", fontWeight: "bold" }}>Username:</td>
              <td style={{ padding: "0.5em 0.75em 0" }}>{user.username}</td>
            </tr>
            <tr>
              <td style={{ padding: "0.5em 0.75em", fontWeight: "bold" }}>Email:</td>
              <td style={{ padding: "0.5em 0.75em" }}>{user.email}</td>
            </tr>
            <tr>
              <td style={{ padding: "0.5em 0.75em", fontWeight: "bold" }}>User ID:</td>
              <td style={{ padding: "0.5em 0.75em", fontSize: "0.85em" }}>{user._id}</td>
            </tr>
            <tr>
              <td style={{ padding: "0.5em 0.75em", fontWeight: "bold" }}>Joined:</td>
              <td style={{ padding: "0.5em 0.75em" }}>{new Date(user.joinDate).toLocaleString()}</td>
            </tr>
            <tr>
              <td style={{ padding: "0.5em 0.75em", fontWeight: "bold" }}>Status:</td>
              <td style={{ padding: "0.5em 0.75em" }}>
                {user.banned ? (
                  <span className="staff-status-banned">BANNED</span>
                ) : user.active ? (
                  <span className="staff-status-active">✓ Active</span>
                ) : (
                  <span className="staff-status-inactive">Inactive</span>
                )}
              </td>
            </tr>
            <tr>
              <td style={{ padding: "0.5em 0.75em", fontWeight: "bold" }}>Staff:</td>
              <td style={{ padding: "0.5em 0.75em" }}>{user.isStaff ? "Yes" : "No"}</td>
            </tr>
            <tr>
              <td style={{ padding: "0.5em 0.75em", fontWeight: "bold" }}>Superuser:</td>
              <td style={{ padding: "0.5em 0.75em" }}>{user.isSuperuser ? "Yes" : "No"}</td>
            </tr>
          </tbody>
        </table>
      </section>

      {activeBan && (
        <section className="staff-card staff-card--danger">
          <h2>⚠️ Active Ban</h2>
          <p><strong>Reason:</strong> {activeBan.reason}</p>
          <p><strong>Banned At:</strong> {new Date(activeBan.bannedAt).toLocaleString()}</p>
          <p><strong>Banned By:</strong> {activeBan.bannedBy}</p>
          {currentUser?.id && (
            <p style={{ marginTop: "12px" }}>
              <UnbanButton banId={activeBan._id} currentUserId={currentUser.id as Id<"users">} />
            </p>
          )}
        </section>
      )}

      {currentUser?.id && (
        <EditUserForm user={user} currentUserId={currentUser.id as Id<"users">} />
      )}

      <section className="staff-card">
        <h2>Devices ({devices.length})</h2>
        {devices.length === 0 ? (
          <p>No devices tracked</p>
        ) : (
          <div className="staff-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Fingerprint</th>
                  <th>Details</th>
                  <th>Last IP</th>
                  <th style={{ textAlign: "right" }}>Times Used</th>
                  <th>Last Used</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {devices.map((device, idx) => (
                  <tr key={device._id}>
                    <td style={{ fontFamily: "monospace", fontSize: "0.85em" }}>
                      {device.fingerprint.slice(0, 12)}...
                    </td>
                    <td style={{ fontSize: "0.85em" }}>
                      {JSON.parse(device.details).userAgent?.slice(0, 50)}...
                    </td>
                    <td style={{ fontFamily: "monospace" }}>{device.ip}</td>
                    <td style={{ textAlign: "right" }}>{device.timesUsed}</td>
                    <td>{new Date(device.lastUsed).toLocaleString()}</td>
                    <td>
                      {currentUser?.id && (
                        <BanDeviceButton
                          deviceId={device._id}
                          currentUserId={currentUser.id as Id<"users">}
                          isBanned={deviceBanStatuses[idx]?.banned || false}
                        />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="staff-card">
        <h2>IP Addresses ({ips.length})</h2>
        {ips.length === 0 ? (
          <p>No IPs tracked</p>
        ) : (
          <div className="staff-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>IP Address</th>
                  <th style={{ textAlign: "right" }}>Times Used</th>
                  <th>Last Used</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {ips.map((ip, idx) => (
                  <tr key={ip._id}>
                    <td style={{ fontFamily: "monospace" }}>{ip.ip}</td>
                    <td style={{ textAlign: "right" }}>{ip.timesUsed}</td>
                    <td>{new Date(ip.lastUsed).toLocaleString()}</td>
                    <td>
                      {currentUser?.id && (
                        <BanIpButton
                          ipId={ip._id}
                          currentUserId={currentUser.id as Id<"users">}
                          isBanned={ipBanStatuses[idx]?.banned || false}
                        />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {!user.banned && currentUser.id && (
        <BanUserForm
          userId={userId}
          currentUserId={currentUser.id as Id<"users">}
          deviceCount={devices.length}
          ipCount={ips.length}
        />
      )}

      {bans.length > 0 && (
        <section className="staff-card">
          <h2>Ban History ({bans.length})</h2>
          <div className="staff-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Reason</th>
                  <th>Banned At</th>
                  <th>Banned By</th>
                </tr>
              </thead>
              <tbody>
                {bans.map((ban) => (
                  <tr key={ban._id}>
                    <td>
                      {ban.active ? (
                        <span className="staff-status-banned">Active</span>
                      ) : (
                        <span className="staff-status-inactive">Inactive</span>
                      )}
                    </td>
                    <td>{ban.reason}</td>
                    <td>{new Date(ban.bannedAt).toLocaleString()}</td>
                    <td style={{ fontFamily: "monospace", fontSize: "0.85em" }}>{ban.bannedBy}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}