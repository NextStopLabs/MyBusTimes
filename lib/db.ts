// lib/db.ts
import { fetchQuery, fetchMutation } from "convex/nextjs";
import { api } from "@/convex/_generated/api";

export async function createUser(user: {
  email: string;
  username: string;
  passwordHash: string;
}) {
  return await fetchMutation(api.users.create, user);
}

export async function getUserByEmail(email: string) {
  return await fetchQuery(api.users.getByEmail, { email });
}
