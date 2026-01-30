import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";
import cookie from "cookie";
import { fetchQuery } from "convex/nextjs";
import { api } from "@/convex/_generated/api";


// Hash a password before storing
export async function hashPassword(password: string) {
  const salt = await bcrypt.genSalt(12);
  return bcrypt.hash(password, salt);
}

// Verify a password
export async function verifyPassword(password: string, hash: string) {
  return bcrypt.compare(password, hash);
}

// Create a signed JWT
export function createToken(payload: object) {
  return jwt.sign(payload, process.env.JWT_SECRET!, {
    expiresIn: "365d",
  });
}

// Verify a token
export function verifyToken(token: string) {
  try {
    return jwt.verify(token, process.env.JWT_SECRET!);
  } catch {
    return null;
  }
}

export async function getCurrentUser(cookieHeader: string) {
  const parsed = cookie.parse(cookieHeader || "");
  const token = parsed.token;

  if (!token) return null;

  const payload = verifyToken(token);
  if (!payload || typeof payload !== "object") return null;

  const email = (payload as any).email;
  if (!email) return null;

  const user = await fetchQuery(api.users.getByEmail, { email });
  if (!user) return null;

  return {
    id: user._id,
    username: user.username,
    email: user.email,
    isStaff: user.isStaff,
    isSuperuser: user.isSuperuser,
  };
}