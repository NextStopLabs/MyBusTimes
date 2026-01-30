import { v } from "convex/values";
import { query, mutation } from "./_generated/server";

export const checkBanStatus = query({
  args: {
    userId: v.optional(v.id("users")),
    fingerprint: v.string(),
    ip: v.string(),
  },
  handler: async (ctx, { userId, fingerprint, ip }) => {
    // Check if user is directly banned
    if (userId) {
      const userBan = await ctx.db
        .query("bans")
        .withIndex("by_user", (q) => q.eq("userId", userId))
        .filter((q) => q.eq(q.field("active"), true))
        .first();
      
      if (userBan) {
        return { 
          banned: true, 
          reason: userBan.reason,
          type: "user"
        };
      }
    }

    // Check if device is banned
    const device = await ctx.db
      .query("devices")
      .withIndex("by_fingerprint", (q) => q.eq("fingerprint", fingerprint))
      .first();
    
    if (device) {
      const deviceBan = await ctx.db
        .query("banDevices")
        .withIndex("by_device", (q) => q.eq("deviceId", device._id))
        .first();
      
      if (deviceBan) {
        const ban = await ctx.db.get(deviceBan.banId);
        if (ban?.active) {
          const needsFlag = userId && userId !== ban.userId
            ? { userId, reason: "Used banned device", relatedBanId: ban._id }
            : undefined;
          return { banned: true, reason: ban.reason, type: "device", needsFlag };
        }
        if (!ban) {
          return { banned: true, reason: "Your access has been restricted.", type: "device" };
        }
      }
    }

    // Check if IP is banned (check all ips rows for this IP - same IP can exist for multiple users)
    const ipRecords = await ctx.db
      .query("ips")
      .withIndex("by_ip", (q) => q.eq("ip", ip))
      .collect();

    for (const ipRecord of ipRecords) {
      const ipBan = await ctx.db
        .query("banIps")
        .withIndex("by_ip", (q) => q.eq("ipId", ipRecord._id))
        .first();

      if (ipBan) {
        const ban = await ctx.db.get(ipBan.banId);
        if (ban?.active) {
          const needsFlag = userId && userId !== ban.userId
            ? { userId, reason: "Used banned IP", relatedBanId: ban._id }
            : undefined;
          return { banned: true, reason: ban.reason, type: "ip", needsFlag };
        }
        // banIps row exists but bans document is missing (orphaned) – still treat as banned
        if (!ban) {
          return { banned: true, reason: "Your access has been restricted.", type: "ip" };
        }
      }
    }

    return { banned: false };
  },
});

/** Called from API when checkBanStatus returns needsFlag – queries cannot write, so flagging is done via this mutation. */
export const flagUserForBan = mutation({
  args: {
    userId: v.id("users"),
    reason: v.string(),
    relatedBanId: v.id("bans"),
  },
  handler: async (ctx, { userId, reason, relatedBanId }) => {
    const existing = await ctx.db
      .query("flaggedUsers")
      .withIndex("by_user", (q) => q.eq("userId", userId))
      .filter((q) => q.eq(q.field("reviewed"), false))
      .first();

    if (!existing) {
      await ctx.db.insert("flaggedUsers", {
        userId,
        reason,
        flaggedAt: Date.now(),
        relatedBanId,
        reviewed: false,
      });
    }
    return { success: true };
  },
});

// Create a ban
export const createBan = mutation({
  args: {
    userId: v.id("users"),
    reason: v.string(),
    bannedBy: v.id("users"),
    banDevices: v.boolean(),
    banIps: v.boolean(),
  },
  handler: async (ctx, { userId, reason, bannedBy, banDevices, banIps }) => {
    // Create the ban
    const banId = await ctx.db.insert("bans", {
      userId,
      reason,
      bannedAt: Date.now(),
      bannedBy,
      active: true,
    });

    // Update user ban status
    await ctx.db.patch(userId, { banned: true });

    // Ban all user's devices
    if (banDevices) {
      const devices = await ctx.db
        .query("devices")
        .withIndex("by_user", (q) => q.eq("userId", userId))
        .collect();
      
      for (const device of devices) {
        await ctx.db.insert("banDevices", {
          banId,
          deviceId: device._id,
        });
      }
    }

    // Ban all user's IPs
    if (banIps) {
      const ips = await ctx.db
        .query("ips")
        .withIndex("by_user", (q) => q.eq("userId", userId))
        .collect();
      
      for (const ip of ips) {
        await ctx.db.insert("banIps", {
          banId,
          ipId: ip._id,
        });
      }
    }

    return { success: true, banId };
  },
});

/** List flagged users with user info – for staff portal. */
export const listFlaggedUsers = query({
  args: { unreviewedOnly: v.optional(v.boolean()) },
  handler: async (ctx, { unreviewedOnly = true }) => {
    const flags = await ctx.db.query("flaggedUsers").collect();
    const filtered = unreviewedOnly ? flags.filter((f) => !f.reviewed) : flags;
    return Promise.all(
      filtered.map(async (f) => {
        const user = await ctx.db.get(f.userId);
        return {
          _id: f._id,
          userId: f.userId,
          reason: f.reason,
          flaggedAt: f.flaggedAt,
          relatedBanId: f.relatedBanId,
          reviewed: f.reviewed,
          username: user?.username ?? "(unknown)",
          email: user?.email ?? "(unknown)",
        };
      })
    );
  },
});

export const deactivateBan = mutation({
  args: {
    banId: v.id("bans"),
    currentUserId: v.id("users"),
  },
  handler: async (ctx, { banId, currentUserId }) => {
    const ban = await ctx.db.get(banId);
    if (!ban) throw new Error("Ban not found");

    await ctx.db.patch(banId, { active: false });
    await ctx.db.patch(ban.userId, { banned: false });

    return { success: true };
  },
});

export const banDevice = mutation({
  args: {
    deviceId: v.id("devices"),
    reason: v.string(),
    bannedBy: v.id("users"),
  },
  handler: async (ctx, { deviceId, reason, bannedBy }) => {
    const device = await ctx.db.get(deviceId);
    if (!device) throw new Error("Device not found");

    const banId = await ctx.db.insert("bans", {
      userId: device.userId,
      reason: `Device ban: ${reason}`,
      bannedAt: Date.now(),
      bannedBy,
      active: true,
    });

    await ctx.db.insert("banDevices", {
      banId,
      deviceId,
    });

    return { success: true, banId };
  },
});

export const unbanDevice = mutation({
  args: {
    deviceId: v.id("devices"),
  },
  handler: async (ctx, { deviceId }) => {
    const banDevice = await ctx.db
      .query("banDevices")
      .withIndex("by_device", (q) => q.eq("deviceId", deviceId))
      .first();

    if (banDevice) {
      await ctx.db.delete(banDevice._id);
    }

    return { success: true };
  },
});

export const banIp = mutation({
  args: {
    ipId: v.id("ips"),
    reason: v.string(),
    bannedBy: v.id("users"),
  },
  handler: async (ctx, { ipId, reason, bannedBy }) => {
    const ip = await ctx.db.get(ipId);
    if (!ip) throw new Error("IP not found");

    const banId = await ctx.db.insert("bans", {
      userId: ip.userId,
      reason: `IP ban: ${reason}`,
      bannedAt: Date.now(),
      bannedBy,
      active: true,
    });

    await ctx.db.insert("banIps", {
      banId,
      ipId,
    });

    return { success: true, banId };
  },
});

export const unbanIp = mutation({
  args: {
    ipId: v.id("ips"),
  },
  handler: async (ctx, { ipId }) => {
    const banIp = await ctx.db
      .query("banIps")
      .withIndex("by_ip", (q) => q.eq("ipId", ipId))
      .first();

    if (banIp) {
      await ctx.db.delete(banIp._id);
    }

    return { success: true };
  },
});

export const getDeviceBanStatus = query({
  args: { deviceId: v.id("devices") },
  handler: async (ctx, { deviceId }) => {
    const banDevice = await ctx.db
      .query("banDevices")
      .withIndex("by_device", (q) => q.eq("deviceId", deviceId))
      .first();
    
    if (banDevice) {
      const ban = await ctx.db.get(banDevice.banId);
      return { banned: true, ban };
    }
    
    return { banned: false };
  },
});

export const getIpBanStatus = query({
  args: { ipId: v.id("ips") },
  handler: async (ctx, { ipId }) => {
    const banIp = await ctx.db
      .query("banIps")
      .withIndex("by_ip", (q) => q.eq("ipId", ipId))
      .first();
    
    if (banIp) {
      const ban = await ctx.db.get(banIp.banId);
      return { banned: true, ban };
    }
    
    return { banned: false };
  },
});

// Helper function to flag users
async function flagUser(ctx: any, userId: any, reason: string, banId: any) {
  const existing = await ctx.db
    .query("flaggedUsers")
    .filter((q: any) => 
      q.and(
        q.eq(q.field("userId"), userId),
        q.eq(q.field("reviewed"), false)
      )
    )
    .first();
  
  if (!existing) {
    await ctx.db.insert("flaggedUsers", {
      userId,
      reason,
      flaggedAt: Date.now(),
      relatedBanId: banId,
      reviewed: false,
    });
  }
}

/** Mark a flagged user as reviewed. */
export const markFlagReviewed = mutation({
  args: {
    flagId: v.id("flaggedUsers"),
    currentUserId: v.id("users"),
  },
  handler: async (ctx, { flagId, currentUserId }) => {
    const current = await ctx.db.get(currentUserId);
    if (!current || (!current.isStaff && !current.isSuperuser)) {
      throw new Error("Unauthorized");
    }
    await ctx.db.patch(flagId, { reviewed: true });
    return { success: true };
  },
});

