import type { Metadata } from "next";
import "@/app/narrow.css";

export const metadata: Metadata = {
  title: "Register - MyBusTimes",
  description: "Register for MyBusTimes",
};

export default function RegisterLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}