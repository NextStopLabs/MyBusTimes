import type { Metadata } from "next";
import "@/app/narrow.css";

export const metadata: Metadata = {
  title: "Logout - MyBusTimes",
  description: "Logout from MyBusTimes",
};

export default function LogoutLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}