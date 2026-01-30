import { NextResponse } from "next/server";
import { verifyPassword, createToken } from "@/lib/auth";
import cookie from "cookie";
import { getUserByEmail } from "@/lib/db";

export async function POST(request: Request) {
  const { email, password } = await request.json();

  // Lookup user
  const user = await getUserByEmail(email);

  if (!user) {
    return NextResponse.json(
      { message: "Invalid credentials" },
      { status: 401 }
    );
  }

  // Check hashed password
  const valid = await verifyPassword(password, user.passwordHash);
  if (!valid) {
    return NextResponse.json(
      { message: "Invalid credentials" },
      { status: 401 }
    );
  }

  // Sign JWT
  const token = createToken({ userId: user._id, email });

  // Set HTTP-only cookie
  const setCookie = cookie.serialize("token", token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    path: "/",
    maxAge: 60 * 60 * 24 * 365
  });

  return NextResponse.json({ success: true }, { headers: { "Set-Cookie": setCookie } });
}
