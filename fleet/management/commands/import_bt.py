import re
import requests
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from fleet.models import MBTOperator, fleet, liverie, vehicleType
from routes.models import route, routeStop, stop

User = get_user_model()


class Command(BaseCommand):
    help = 'Full BusTimes importer (fleet + routes + stops)'

    # ==============================
    # ARGUMENTS
    # ==============================
    def add_arguments(self, parser):
        parser.add_argument('--url', required=True)
        parser.add_argument('--owner', required=True)
        parser.add_argument('--import_into')
        parser.add_argument('--routes-only', action='store_true')
        parser.add_argument('--fleet-only', action='store_true')

    # ==============================
    # HELPERS
    # ==============================
    def format_reg(self, reg):
        if not reg:
            return reg
        reg = reg.replace(' ', '').upper()
        return f"{reg[:-3]} {reg[-3:]}" if len(reg) >= 4 else reg
    
    def parse_route_description(self, description):
        if not description:
            return None, None
    
        if ' - ' in description:
            a, b = description.split(' - ', 1)
            return a.strip(), b.strip()
    
        if ' to ' in description.lower():
            parts = re.split(r'\s+to\s+', description, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()

        return description, None

    def find_existing_stop(self, cache, name, lat, lon, tol=0.0005):
        for s in cache:
            if s.stop_name == name:
                if abs(s.latitude - lat) < tol and abs(s.longitude - lon) < tol:
                    return s
        return None

    # ==============================
    # VEHICLE HELPERS
    # ==============================
    def get_or_create_mbt_type(self, bt_type, owner):
        if not bt_type:
            return None

        name = bt_type.get('name')
        if not name:
            return None

        obj = vehicleType.objects.filter(type_name=name).first()
        if obj:
            return obj

        return vehicleType.objects.create(
            type_name=name,
            active=True,
            hidden=False,
            double_decker=bt_type.get('double_decker', False),
            type=bt_type.get('style', 'Bus') or 'Bus',
            fuel=(bt_type.get('fuel') or 'Diesel').capitalize(),
            added_by=owner,
        )

    def get_or_create_mbt_livery(self, bt_livery, owner):
        if not bt_livery:
            return None, ''

        name = bt_livery.get('name')
        left = bt_livery.get('left', '')
        right = bt_livery.get('right', '')

        if not name:
            return None, left or ''

        obj = liverie.objects.filter(
            name=name,
            left_css=left,
            right_css=right
        ).first()

        if obj:
            return obj, ''

        return liverie.objects.create(
            name=name,
            colour=bt_livery.get('colour') or '#FFFFFF',
            left_css=left,
            right_css=right,
            text_colour='black',
            published=False,
            added_by=owner
        ), ''

    # ==============================
    # ROUTE + STOP IMPORT
    # ==============================
    # ==============================
    # ROUTES + STOPS
    # ==============================
       # ==============================
    # ROUTES + STOPS
    # ==============================
    def import_routes(self, mbt_operator, operator_noc):
        self.stdout.write(self.style.SUCCESS("\n=== Importing Routes + Stops (STABLE MODE) ==="))

        services_url = f"https://bustimes.org/api/services/?operator={operator_noc}"
        services = []

        while services_url:
            res = requests.get(services_url, timeout=15)
            res.raise_for_status()
            data = res.json()

            services += data.get('results', [])
            services_url = data.get('next')

        self.stdout.write(f"Loaded {len(services)} services")

        stops_url = "https://bustimes.org/api/stops/"
        stop_lookup = {}

        while stops_url:
            res = requests.get(stops_url, timeout=15)
            res.raise_for_status()
            data = res.json()

            for s in data.get("results", []):
                key = (s.get("name"), round(s.get("lat") or 0, 5), round(s.get("lon") or 0, 5))
                stop_lookup[key] = s

            stops_url = data.get("next")

        self.stdout.write(f"Loaded {len(stop_lookup)} stops")

        for service in services:
            line = service.get("line_name")
            desc = service.get("description")
            sid = service.get("id")

            inbound, outbound = self.parse_route_description(desc)

            route_obj, _ = route.objects.get_or_create(
                route_num=line,
                inbound_destination=inbound,
                outbound_destination=outbound,
            )

            route_obj.route_operators.add(mbt_operator)

            journeys = []
            url = f"https://bustimes.org/api/vehiclejourneys/?service={sid}"

            while url:
                try:
                    res = requests.get(url, timeout=15)

                    if res.status_code == 404:
                        break

                    res.raise_for_status()
                    data = res.json()

                    journeys += data.get("results", [])
                    url = data.get("next")

                except Exception:
                    break

            if not journeys:
                continue

            grouped = {}
            for j in journeys:
                grouped.setdefault(j.get("direction", "outbound"), []).append(j)

            for direction, jlist in grouped.items():

                best = max(jlist, key=lambda x: len(x.get("stops") or []))
                raw_stops = best.get("stops") or best.get("stop_times") or []

                stop_list = []

                for s in raw_stops:
                    name = s.get("name")
                    lat = s.get("lat")
                    lon = s.get("lon")

                    if not name or lat is None or lon is None:
                        continue

                    key = (name, round(lat, 5), round(lon, 5))
                    api_stop = stop_lookup.get(key)

                    stop_list.append({
                        "name": name,
                        "lat": lat,
                        "lon": lon,
                        "api_id": api_stop.get("id") if api_stop else None
                    })

                inbound_flag = direction.lower() == "inbound"

                routeStop.objects.filter(route=route_obj, inbound=inbound_flag).delete()
                rs = routeStop.objects.create(
                    route=route_obj,
                    inbound=inbound_flag,
                    stops=stop_list,
                    circular=False,
                )

    # ==============================
    # FLEET IMPORT
    # ==============================
    def import_fleet(self, mbt_operator, operator_noc, owner):
        self.stdout.write(self.style.SUCCESS("\n=== Importing Fleet ==="))

        url = f"https://bustimes.org/api/vehicles/?operator={operator_noc}"
        vehicles = []

        while url:
            r = requests.get(url)
            r.raise_for_status()
            d = r.json()
            vehicles += d.get('results', [])
            url = d.get('next')

        grouped = {}
        for v in vehicles:
            reg = v.get('reg')
            if reg:
                grouped.setdefault(reg, []).append(v)

        for reg, items in grouped.items():
            items.sort(key=lambda x: x.get('withdrawn', False))
            v = items[0]

            reg = self.format_reg(reg)

            vt = self.get_or_create_mbt_type(v.get('vehicle_type'), owner)
            lv, colour = self.get_or_create_mbt_livery(v.get('livery'), owner)

            obj, created = fleet.objects.get_or_create(
                operator=mbt_operator,
                reg=reg,
                defaults={
                    "fleet_number": v.get('fleet_code'),
                    "vehicleType": vt,
                    "livery": lv,
                    "colour": colour,
                    "in_service": not v.get('withdrawn', False),
                    "branding": v.get('branding'),
                    "name": v.get('name'),
                    "notes": v.get('notes'),
                    "features": v.get('special_features') or [],
                    "last_modified_by": owner,
                }
            )

            if not created:
                if not obj.in_service and not v.get('withdrawn'):
                    obj.in_service = True
                    obj.save()

    # ==============================
    # MAIN
    # ==============================
    def handle(self, *args, **opts):
        url = opts['url']
        owner = User.objects.get(username=opts['owner'])

        slug = re.search(r'/operators/([^/]+)', url).group(1)

        data = requests.get(f"https://bustimes.org/api/operators/?slug={slug}").json()['results'][0]

        mbt_operator, _ = MBTOperator.objects.get_or_create(
            operator_code=data['noc'],
            defaults={
                "operator_name": data.get('name'),
                "operator_slug": slug,
                "owner": owner
            }
        )

        if not opts.get('routes_only'):
            self.import_fleet(mbt_operator, data['noc'], owner)

        if not opts.get('fleet_only'):
            self.import_routes(mbt_operator, data['noc'])
