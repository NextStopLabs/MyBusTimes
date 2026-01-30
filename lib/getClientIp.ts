/**
 * Get client IP from a request, using the same normalization as track/check-ban
 * so stored and checked IPs always match.
 */
export function getClientIp(request: Request): string {
  const rawIp =
    request.headers.get("x-forwarded-for") ||
    request.headers.get("x-real-ip") ||
    request.headers.get("cf-connecting-ip") ||
    request.headers.get("true-client-ip") ||
    "unknown";
  const first = rawIp.split(",")[0].trim();
  // Normalize IPv6-mapped IPv4 addresses like ::ffff:127.0.0.1 to 127.0.0.1
  // and strip optional port or zone identifiers.
  let ip = first;
  // Remove IPv6 zone id (e.g., fe80::1%lo0)
  const percentIndex = ip.indexOf("%");
  if (percentIndex !== -1) ip = ip.slice(0, percentIndex);
  // If IPv6-mapped IPv4
  if (ip.startsWith("::ffff:")) {
    ip = ip.slice(7);
  }
  // Strip port if present (e.g., 127.0.0.1:12345)
  const colonPort = ip.lastIndexOf(":");
  if (colonPort !== -1 && ip.indexOf("]") === -1) {
    // If it's an IPv6 address (contains multiple colons) leave it alone.
    const colonCount = (ip.match(/:/g) || []).length;
    if (colonCount === 1) {
      ip = ip.split(":")[0];
    }
  }

  return ip;
}
