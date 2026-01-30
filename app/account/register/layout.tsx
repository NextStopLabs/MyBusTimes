import type { Metadata } from "next";

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