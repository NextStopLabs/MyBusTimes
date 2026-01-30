import Link from "next/link";
import "./narrow.css";
import { Metadata } from "next";
import { Breadcrumb } from "./components/Breadcrumb";

export const metadata: Metadata = {
  title: "404 - Page Not Found",
  description: "Oops! The page you are looking for does not exist.",
};

export default function NotFound() {
  const breadcrumbs = [{ label: "Home", href: "/" }, { label: "Oops! Page not Found", href: "/" }];

  return (
    <>
      <Breadcrumb items={breadcrumbs} />
      <h1 style={{ textAlign:"center" }}>404 - Page Not Found</h1>
      <p style={{ textAlign:"center" }}>Sorry, the page you're looking for doesn't exist.</p>
      <Link style={{ textAlign:"center", display: "block" }} href="/">Go back home</Link>
    </>
  );
}
