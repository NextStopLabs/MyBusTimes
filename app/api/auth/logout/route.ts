import { NextResponse } from "next/server";
import cookie from "cookie";

export async function POST() {
  const setCookie = cookie.serialize("token", "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    path: "/",
    maxAge: 0,
  });

  return NextResponse.json({ success: true }, { headers: { "Set-Cookie": setCookie } });
}
