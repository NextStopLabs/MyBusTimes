import { v } from "convex/values";
import { query } from "./_generated/server";

export const getAllRegions = query({
  args: {},
  handler: async (ctx) => {
    const regions = await ctx.db.query("regions").collect();
    return regions.sort((a, b) => a.name.localeCompare(b.name));
  },
});

// Optional: Get only top-level regions (no parent)
export const getTopLevelRegions = query({
  args: {},
  handler: async (ctx) => {
    const regions = await ctx.db
      .query("regions")
      .filter((q) => q.eq(q.field("parentId"), undefined))
      .collect();
    return regions.sort((a, b) => a.name.localeCompare(b.name));
  },
});