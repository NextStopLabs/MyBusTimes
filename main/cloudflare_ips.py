import requests
import ipaddress
import time
import logging

logger = logging.getLogger(__name__)

CLOUDFLARE_IPV4_URL = "https://www.cloudflare.com/ips-v4"
CLOUDFLARE_IPV6_URL = "https://www.cloudflare.com/ips-v6"

# TTL cache for Cloudflare networks (refreshes every 6 hours)
_cf_cache = {
    'data': None,
    'expires_at': 0
}
_CF_CACHE_TTL = 6 * 60 * 60  # 6 hours in seconds


def is_cloudflare_ip(ip):
    ipv4_nets, ipv6_nets = get_cloudflare_networks()

    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        return False  # invalid IP, don't treat as CF but also don't ban it yet

    if ip_obj.version == 4:
        return any(ip_obj in net for net in ipv4_nets)
    else:
        return any(ip_obj in net for net in ipv6_nets)


def get_cloudflare_networks():
    """Fetch Cloudflare IP networks with TTL-based caching (6 hours)."""
    global _cf_cache
    
    now = time.time()
    if _cf_cache['data'] is not None and now < _cf_cache['expires_at']:
        return _cf_cache['data']
    
    try:
        ipv4_text = requests.get(CLOUDFLARE_IPV4_URL, timeout=5).text.strip().splitlines()
        ipv6_text = requests.get(CLOUDFLARE_IPV6_URL, timeout=5).text.strip().splitlines()

        ipv4_nets = [ipaddress.ip_network(cidr) for cidr in ipv4_text]
        ipv6_nets = [ipaddress.ip_network(cidr) for cidr in ipv6_text]

        _cf_cache['data'] = (ipv4_nets, ipv6_nets)
        _cf_cache['expires_at'] = now + _CF_CACHE_TTL
        
        return _cf_cache['data']
    except Exception as e:
        logger.warning(f"Failed to fetch Cloudflare IPs: {e}")
        # Return cached data if available, even if expired
        if _cf_cache['data'] is not None:
            return _cf_cache['data']
        # Return empty lists as fallback
        return ([], [])
