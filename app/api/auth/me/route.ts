import { NextResponse } from "next/server";
import cookie from "cookie";
import { verifyToken } from "@/lib/auth";
import { fetchQuery } from "convex/nextjs";
import { api } from "@/convex/_generated/api";

export async function GET(request: Request) {
  const cookieHeader = request.headers.get("cookie") || "";
  const parsed = cookie.parse(cookieHeader || "");
  const token = parsed.token;

  if (!token) {
    return NextResponse.json({ user: null });
  }

  const payload = verifyToken(token);
  if (!payload || typeof payload !== "object") {
    return NextResponse.json({ user: null });
  }

  // token contains email and userId based on login implementation
  const email = (payload as any).email;
  if (!email) return NextResponse.json({ user: null });

  const user = await fetchQuery(api.users.getByEmail, { email });
  if (!user) return NextResponse.json({ user: null });

  return NextResponse.json({ 
    user: { 
      id: user._id, 
      username: user.username, 
      email: user.email,
      isStaff: user.isStaff,
      isSuperuser: user.isSuperuser,
    } 
  });
}