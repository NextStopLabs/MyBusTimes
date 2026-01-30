import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const create = mutation({
  args: {
    email: v.string(),
    username: v.string(),
    passwordHash: v.string()
  },
  handler: async (ctx, { email, username, passwordHash }) => {
    // Avoid duplicates
    const existing = await ctx.db
      .query("users")
      .withIndex("by_email", (q) => q.eq("email", email))
      .first();
    if (existing) {
      return { error: "User already exists" };
    }

    return await ctx.db.insert("users", {
      email,
      username,
      passwordHash: passwordHash,
      joinDate: Date.now(),
      updatedDate: Date.now(),
      active: true,
      banned: false,
      isStaff: false,
      isSuperuser: false,
      staffTeamId: undefined,
    });
  },
});

export const getCurrentUser = query({
  args: {},
  handler: async (ctx) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      return null;
    }
    
    const user = await ctx.db
      .query("users")
      .withIndex("by_email", (q) => q.eq("email", identity.email!))
      .first();
    
    return user;
  },
});

export const getByEmail = query({
  args: { email: v.string() },
  handler: async (ctx, { email }) => {
    return await ctx.db
      .query("users")
      .withIndex("by_email", (q) => q.eq("email", email))
      .first();
  },
});

export const getById = query({
  args: { userId: v.id("users") },
  handler: async (ctx, { userId }) => {
    return await ctx.db.get(userId);
  },
});

export const getUserDevices = query({
  args: { userId: v.id("users") },
  handler: async (ctx, { userId }) => {
    return await ctx.db
      .query("devices")
      .withIndex("by_user", (q) => q.eq("userId", userId))
      .collect();
  },
});

export const getUserIps = query({
  args: { userId: v.id("users") },
  handler: async (ctx, { userId }) => {
    return await ctx.db
      .query("ips")
      .withIndex("by_user", (q) => q.eq("userId", userId))
      .collect();
  },
});

export const getUserBans = query({
  args: { userId: v.id("users") },
  handler: async (ctx, { userId }) => {
    return await ctx.db
      .query("bans")
      .withIndex("by_user", (q) => q.eq("userId", userId))
      .collect();
  },
});

/** List all users – for staff portal. */
export const listUsers = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db.query("users").collect();
  },
});

/** Update user (staff/superuser/active) – caller must be staff/superuser. */
export const updateUser = mutation({
  args: {
    currentUserId: v.id("users"),
    targetUserId: v.id("users"),
    isStaff: v.optional(v.boolean()),
    isSuperuser: v.optional(v.boolean()),
    active: v.optional(v.boolean()),
  },
  handler: async (ctx, { currentUserId, targetUserId, isStaff, isSuperuser, active }) => {
    const current = await ctx.db.get(currentUserId);
    if (!current || (!current.isStaff && !current.isSuperuser)) {
      throw new Error("Unauthorized");
    }
    const updates: { isStaff?: boolean; isSuperuser?: boolean; active?: boolean; updatedDate?: number } = {};
    if (isStaff !== undefined) updates.isStaff = isStaff;
    if (isSuperuser !== undefined) updates.isSuperuser = isSuperuser;
    if (active !== undefined) updates.active = active;
    if (Object.keys(updates).length > 0) {
      updates.updatedDate = Date.now();
      await ctx.db.patch(targetUserId, updates);
    }
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

    // Create a ban for the device's user
    const banId = await ctx.db.insert("bans", {
      userId: device.userId,
      reason: `Device ban: ${reason}`,
      bannedAt: Date.now(),
      bannedBy,
      active: true,
    });

    // Link the device to the ban
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
    // Find the ban device entry
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

    // Create a ban for the IP's user
    const banId = await ctx.db.insert("bans", {
      userId: ip.userId,
      reason: `IP ban: ${reason}`,
      bannedAt: Date.now(),
      bannedBy,
      active: true,
    });

    // Link the IP to the ban
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
    // Find the ban IP entry
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

export const deactivateBan = mutation({
  args: {
    banId: v.id("bans"),
    currentUserId: v.id("users"),
  },
  handler: async (ctx, { banId, currentUserId }) => {
    const ban = await ctx.db.get(banId);
    if (!ban) throw new Error("Ban not found");

    // Deactivate the ban
    await ctx.db.patch(banId, { active: false });

    // Update user
    await ctx.db.patch(ban.userId, { banned: false });

    return { success: true };
  },
});