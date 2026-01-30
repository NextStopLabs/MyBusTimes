import { v } from "convex/values";
import { mutation } from "./_generated/server";

export const logAccess = mutation({
  args: {
    userId: v.id("users"),
    fingerprint: v.string(),
    deviceDetails: v.string(),
    ip: v.string(),
  },
  handler: async (ctx, { userId, fingerprint, deviceDetails, ip }) => {
    const now = Date.now();

    // Log device
    const existingDevice = await ctx.db
      .query("devices")
      .withIndex("by_fingerprint", (q) => q.eq("fingerprint", fingerprint))
      .first();

    if (existingDevice) {
      await ctx.db.patch(existingDevice._id, {
        timesUsed: existingDevice.timesUsed + 1,
        lastUsed: now,
        ip: ip,
      });
    } else {
      await ctx.db.insert("devices", {
        userId,
        fingerprint,
        details: deviceDetails,
        ip,
        timesUsed: 1,
        lastUsed: now,
      });
    }

    // Log IP
    const existingIp = await ctx.db
      .query("ips")
      .filter((q) => 
        q.and(
          q.eq(q.field("ip"), ip),
          q.eq(q.field("userId"), userId)
        )
      )
      .first();

    if (existingIp) {
      await ctx.db.patch(existingIp._id, {
        timesUsed: existingIp.timesUsed + 1,
        lastUsed: now,
      });
    } else {
      await ctx.db.insert("ips", {
        userId,
        ip,
        timesUsed: 1,
        lastUsed: now,
      });
    }

    return { success: true };
  },
});