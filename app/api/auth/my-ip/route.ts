import { NextResponse } from "next/server";
import { getClientIp } from "@/lib/getClientIp";

export async function GET(request: Request) {
  const ip = getClientIp(request);
  return NextResponse.json({ ip });
}
