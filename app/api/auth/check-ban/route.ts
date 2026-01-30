import { NextResponse } from "next/server";
import { fetchQuery, fetchMutation } from "convex/nextjs";
import { api } from "@/convex/_generated/api";
import { getClientIp } from "@/lib/getClientIp";

export async function POST(request: Request) {
  const body = await request.json();
  const { userId, fingerprint, ip: bodyIp } = body;

  // Use IP from body if client sent it (from /api/auth/my-ip); otherwise from request headers.
  const ip = typeof bodyIp === "string" && bodyIp.length > 0 ? bodyIp : getClientIp(request);

  const banStatus = await fetchQuery(api.bans.checkBanStatus, {
    userId: userId || undefined,
    fingerprint,
    ip,
  });

  // Queries cannot write; flagging is done via mutation so it actually persists
  if (banStatus.needsFlag) {
    await fetchMutation(api.bans.flagUserForBan, banStatus.needsFlag);
  }

  const { needsFlag: _strip, ...response } = banStatus;
  return NextResponse.json(response);
}