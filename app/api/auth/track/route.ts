import { NextResponse } from "next/server";
import { fetchMutation } from "convex/nextjs";
import { api } from "@/convex/_generated/api";
import { getClientIp } from "@/lib/getClientIp";

export async function POST(request: Request) {
  const { userId, fingerprint, deviceDetails } = await request.json();
  const ip = getClientIp(request);

  await fetchMutation(api.tracking.logAccess, {
    userId,
    fingerprint,
    deviceDetails,
    ip,
  });

  return NextResponse.json({ success: true });
}