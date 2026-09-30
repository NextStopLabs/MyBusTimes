import json
import re
import logging
import time
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import fleet, fleetChange
from django.utils.timezone import now
import threading

logger = logging.getLogger(__name__)

# Store old fleet instances with timestamps for cleanup
# Format: {pk: (fleet_instance, timestamp)}
_old_fleets = {}
_OLD_FLEETS_TTL = 60  # seconds - entries older than this are pruned
_OLD_FLEETS_LOCK = threading.Lock()


def _cleanup_stale_entries():
    """Remove entries older than TTL to prevent unbounded growth."""
    with _OLD_FLEETS_LOCK:
        cutoff = time.time() - _OLD_FLEETS_TTL
        stale_keys = [k for k, (_, ts) in _old_fleets.items() if ts < cutoff]
        for k in stale_keys:
            _old_fleets.pop(k, None)

def _safe_operator_name(vehicle):
    """Return operator name without raising on dangling FKs."""
    if not getattr(vehicle, "operator_id", None):
        return "Unknown Operator"
    try:
        op = vehicle.operator
        return op.operator_name if op else "Unknown Operator"
    except Exception:
        return f"Unknown Operator ({vehicle.operator_id})"


def _safe_operator_for_change(vehicle):
    """Return operator instance for fleetChange, or None if dangling."""
    if not getattr(vehicle, "operator_id", None):
        return None
    try:
        return vehicle.operator
    except Exception:
        return None


def _safe_type_name(vehicle):
    if not getattr(vehicle, "vehicleType_id", None):
        return "Unknown Type"
    try:
        vt = vehicle.vehicleType
        return vt.type_name if vt else "Unknown Type"
    except Exception:
        return f"Unknown Type ({vehicle.vehicleType_id})"


def _safe_livery_name(vehicle):
    if not getattr(vehicle, "livery_id", None):
        return "No Livery"
    try:
        lv = vehicle.livery
        return lv.name if lv else "No Livery"
    except Exception:
        return f"No Livery ({vehicle.livery_id})"


def _safe_livery_css(vehicle):
    if not getattr(vehicle, "livery_id", None):
        return "No Livery CSS"
    try:
        lv = vehicle.livery
        return lv.left_css if lv else "No Livery CSS"
    except Exception:
        return "No Livery CSS"


def normalize_fleet_number(fleet_number):
    """
    Normalize fleet_number for sorting:
    Pad numeric parts with leading zeros to fixed length (e.g. 10 digits),
    convert to lowercase.
    Example: '10A' -> '0000000010a', '2B' -> '0000000002b'
    """
    def pad_num(m):
        return m.group().zfill(10)
    return re.sub(r'\d+', pad_num, (fleet_number or '').lower())

@receiver(pre_save, sender=fleet)
def store_old_fleet(sender, instance, **kwargs):
    # Always normalize fleet_number before saving (whether creating or updating)
    instance.fleet_number_sort = normalize_fleet_number(instance.fleet_number)

    # Periodically clean up stale entries to prevent unbounded growth
    _cleanup_stale_entries()

    # Only store old instance if updating (i.e., already exists)
    old = None
    if instance.pk:
        try:
            old = fleet.objects.get(pk=instance.pk)
        except fleet.DoesNotExist:
            old = None

        if old is not None:
            with _OLD_FLEETS_LOCK:
                _old_fleets[instance.pk] = (old, time.time())

@receiver(post_save, sender=fleet)
def track_fleet_changes(sender, instance, created, **kwargs):
    if created:
        return  # Skip logging for new items

    with _OLD_FLEETS_LOCK:
        entry = _old_fleets.pop(instance.pk, None)
    if not entry:
        return
    old_instance, _ = entry  # Unpack tuple (instance, timestamp)

    changes = []

    def add_change(field, old_value, new_value):
        if old_value != new_value:
            changes.append({
                "item": field,
                "from": str(old_value),
                "to": str(new_value),
            })

    # Compare fields
    add_change("in_service", old_instance.in_service, instance.in_service)
    add_change("for_sale", old_instance.for_sale, instance.for_sale)
    add_change("preserved", old_instance.preserved, instance.preserved)
    add_change("on_load", old_instance.on_load, instance.on_load)
    add_change("open_top", old_instance.open_top, instance.open_top)
    add_change("reg", old_instance.reg, instance.reg)
    add_change("prev_reg", old_instance.prev_reg, instance.prev_reg)
    add_change("colour", old_instance.colour, instance.colour)
    add_change("type_details", old_instance.type_details, instance.type_details)
    add_change("length", old_instance.length, instance.length)
    add_change("features", old_instance.features, instance.features)
    add_change("branding", old_instance.branding, instance.branding)
    add_change("notes", old_instance.notes, instance.notes)
    add_change("name", old_instance.name, instance.name)
    add_change("fleet_number", old_instance.fleet_number, instance.fleet_number)
    add_change("fleet_number_sort", old_instance.fleet_number_sort, instance.fleet_number_sort)
    add_change("depot", old_instance.depot, instance.depot)

    if old_instance.livery_id != instance.livery_id:
        if old_instance.livery_id:
            add_change("livery_name", _safe_livery_name(old_instance), _safe_livery_name(instance))
            add_change("livery_css", _safe_livery_css(old_instance), _safe_livery_css(instance))
        else:
            add_change("livery_name", "No Livery", _safe_livery_name(instance))
            add_change("livery_css", "No Livery CSS", _safe_livery_css(instance))

    if old_instance.vehicleType_id != instance.vehicleType_id:
        old_type = _safe_type_name(old_instance)
        new_type = _safe_type_name(instance)
        add_change("type", old_type, new_type)

    if old_instance.operator_id != instance.operator_id:
        old_operator = _safe_operator_name(old_instance)
        new_operator = _safe_operator_name(instance)
        add_change("operator", old_operator, new_operator)

    # If changes exist, save to `fleetChange`
    if changes:
        fleetChange.objects.create(
            vehicle=instance,
            operator=_safe_operator_for_change(instance),
            changes=json.dumps(changes),  # Store all changes here
            message=instance.summary,
            user=instance.last_modified_by,  # you must pass this manually somehow if not on instance
            approved_by=instance.last_modified_by,  # temporary fallback
            approved_at=now()
        )
