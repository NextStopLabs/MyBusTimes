import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  users: defineTable({
    username: v.string(),
    passwordHash: v.string(),
    email: v.string(),
    joinDate: v.number(),
    updatedDate: v.number(),
    active: v.boolean(),
    banned: v.boolean(),
    isStaff: v.boolean(),
    isSuperuser: v.boolean(),
    staffTeamId: v.optional(v.id("staffTeams")),
  }).index("by_email", ["email"]),

  staffTeams: defineTable({
    name: v.string(),
  }),

  staffPerms: defineTable({
    name: v.string(),
    slug: v.string(),
  }),

  staffTeamPerms: defineTable({
    staffTeamId: v.id("staffTeams"),
    permId: v.id("staffPerms"),
  }),

  userProfiles: defineTable({
    userId: v.id("users"),
    pfp: v.optional(v.string()),
    banner: v.optional(v.string()),
    themeId: v.optional(v.id("themes")),
    darkMode: v.boolean(),
    otherDetails: v.object({
      had_free_trial: v.boolean(),
    }),
  }),

  userBadges: defineTable({
    userId: v.id("users"),
    badgeId: v.id("badges"),
  }),

  themes: defineTable({
    name: v.string(),
    public: v.boolean(),
    darkCss: v.string(),
    lightCss: v.string(),
    weight: v.number(),
  }),

  badges: defineTable({
    name: v.string(),
    foreground: v.string(),
    background: v.string(),
    additionalCss: v.optional(v.string()),
    selfAssign: v.boolean(),
  }),

  devices: defineTable({
    userId: v.id("users"),
    fingerprint: v.string(),
    details: v.string(),
    ip: v.string(),
    timesUsed: v.number(),
    lastUsed: v.number(),
  })
    .index("by_user", ["userId"])
    .index("by_fingerprint", ["fingerprint"]),

  ips: defineTable({
    userId: v.id("users"),
    ip: v.string(),
    timesUsed: v.number(),
    lastUsed: v.number(),
  })
    .index("by_user", ["userId"])
    .index("by_ip", ["ip"]),

  bans: defineTable({
    userId: v.id("users"),
    reason: v.string(),
    bannedAt: v.number(),
    bannedBy: v.id("users"),
    active: v.boolean(),
  }).index("by_user", ["userId"]),

  banDevices: defineTable({
    banId: v.id("bans"),
    deviceId: v.id("devices"),
  }).index("by_device", ["deviceId"]),

  banIps: defineTable({
    banId: v.id("bans"),
    ipId: v.id("ips"),
  }).index("by_ip", ["ipId"]),

  flaggedUsers: defineTable({
    userId: v.id("users"),
    reason: v.string(),
    flaggedAt: v.number(),
    relatedBanId: v.optional(v.id("bans")),
    reviewed: v.boolean(),
  }).index("by_user", ["userId"]),

  operators: defineTable({
    name: v.string(),
    code: v.string(),
    slug: v.string(),
    details: v.any(),
    ownerId: v.id("users"),
    groupId: v.optional(v.id("groups")),
    organisationId: v.optional(v.id("groups")),
    verified: v.boolean(),
    publicNotes: v.optional(v.string()),
  }),

  regions: defineTable({
    name: v.string(),
    code: v.string(),
    parentId: v.optional(v.id("regions")),
  }),

  operatorRegions: defineTable({
    operatorId: v.id("operators"),
    regionId: v.id("regions"),
  }),

  vehicles: defineTable({
    operatorId: v.id("operators"),
    fleetNumber: v.string(),
    fleetNumberSorting: v.string(),
    reg: v.string(),
    prevReg: v.optional(v.string()),
    liveryId: v.optional(v.id("liveries")),
    details: v.any(),
    features: v.any(),
    notes: v.optional(v.string()),
    typeId: v.id("vehicleTypes"),
    isInService: v.boolean(),
    isForSale: v.boolean(),
    lastEditedBy: v.id("users"),
  }),

  routes: defineTable({
    routeNumber: v.string(),
    routeName: v.string(),
    destinations: v.any(),
    details: v.any(),
    hidden: v.boolean(),
    linkedRouteId: v.optional(v.id("routes")),
    relatedRouteId: v.optional(v.id("routes")),
    routeTypeId: v.id("routeTypes"),
  }),

  routeOperators: defineTable({
    routeId: v.id("routes"),
    operatorId: v.id("operators"),
  }),
});
