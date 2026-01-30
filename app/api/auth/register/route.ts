import { NextResponse } from "next/server";
import { hashPassword } from "@/lib/auth";
import { z } from "zod";
import { fetchMutation } from "convex/nextjs";
import { api } from "@/convex/_generated/api";

const bodySchema = z.object({
  email: z.string().email(),
  username: z.string(),
  password: z.string().min(8),
});

export async function POST(req: Request) {
  const body = bodySchema.parse(await req.json());
  const hashed = await hashPassword(body.password);

  const convexUrl = process.env.NEXT_PUBLIC_CONVEX_URL!;
  console.log("Convex URL:", convexUrl);

  // call the Convex mutation directly
  try {
    const result = await fetchMutation(api.users.create, {
      email: body.email,
      username: body.username,
      passwordHash: hashed,
    });

    return NextResponse.json({ success: true, user: result });

  } catch (err) {
    console.error("Convex call failed:", err);
    return NextResponse.json(
      { message: "Internal server error" },
      { status: 500 }
    );
  }
}
