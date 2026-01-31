import type { Metadata } from "next";
import "@/app/narrow.css";

export const metadata: Metadata = {
  title: "Login - MyBusTimes",
  description: "Login to MyBusTimes",
};

export default function LoginLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}