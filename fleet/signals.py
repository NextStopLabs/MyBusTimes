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

    if old_instance.livery != instance.livery:
        if old_instance.livery:
            add_change("livery_name", old_instance.livery.name, instance.livery.name if instance.livery else "No Livery")
            add_change("livery_css", old_instance.livery.left_css, instance.livery.left_css if instance.livery else "No Livery CSS")
        else:
            add_change("livery_name", "No Livery", instance.livery.name if instance.livery else "No Livery")
            add_change("livery_css", "No Livery CSS", instance.livery.left_css if instance.livery else "No Livery CSS")

    if old_instance.vehicleType_id != instance.vehicleType_id:
        old_type = old_instance.vehicleType.type_name if old_instance.vehicleType else "Unknown Type"
        new_type = instance.vehicleType.type_name if instance.vehicleType else "Unknown Type"
        add_change("type", old_type, new_type)

    if old_instance.operator_id != instance.operator_id:
        old_operator = old_instance.operator.operator_name if old_instance.operator else "Unknown Operator"
        new_operator = instance.operator.operator_name if instance.operator else "Unknown Operator"
        add_change("operator", old_operator, new_operator)

    # If changes exist, save to `fleetChange`
    if changes:
        fleetChange.objects.create(
            vehicle=instance,
            operator=instance.operator,
            changes=json.dumps(changes),  # Store all changes here
            message=instance.summary,
            user=instance.last_modified_by,  # you must pass this manually somehow if not on instance
            approved_by=instance.last_modified_by,  # temporary fallback
            approved_at=now()
        )
