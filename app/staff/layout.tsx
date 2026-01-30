import { headers } from "next/headers";
import { getCurrentUser } from "@/lib/auth";
import { redirect } from "next/navigation";
import Link from "next/link";

export default async function StaffLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const headersList = await headers();
  const cookieHeader = headersList.get("cookie") || "";
  const user = await getCurrentUser(cookieHeader);

  if (!user?.isStaff && !user?.isSuperuser) {
    redirect("/");
  }

  return (
    <div className="content">
      {children}
    </div>
  );
}
