from django.test import TestCase

from fleet.views import build_vehicle_blocks_for_timetables, normalize_trip_minutes
from routes.models import route, timetableEntry


class RunningBoardGenerationTests(TestCase):
    def test_normalize_trip_minutes_rolls_after_midnight(self):
        start, end = normalize_trip_minutes("20:20", "00:27")

        self.assertEqual(start, 20 * 60 + 20)
        self.assertEqual(end, (24 * 60) + 27)

    def test_vehicle_blocks_do_not_overlap_when_trips_cross_midnight(self):
        route_instance = route.objects.create(route_num="N1", route_name="Night Service")
        outbound = timetableEntry.objects.create(
            route=route_instance,
            inbound=False,
            active=True,
            stop_times={
                "Derby Bus Station_idx_0": {
                    "stopname": "Derby Bus Station (Bay 26)",
                    "order": 0,
                    "times": ["20:20", "20:27"],
                },
                "York Rail Station_idx_1": {
                    "stopname": "York Rail Station",
                    "order": 1,
                    "times": ["00:27", "00:34"],
                },
            },
        )
        inbound = timetableEntry.objects.create(
            route=route_instance,
            inbound=True,
            active=True,
            stop_times={
                "York Rail Station_idx_0": {
                    "stopname": "York Rail Station",
                    "order": 0,
                    "times": ["20:20", "20:27"],
                },
                "Derby Bus Station_idx_1": {
                    "stopname": "Derby Bus Station (Bay 26)",
                    "order": 1,
                    "times": ["00:12", "00:19"],
                },
            },
        )

        blocks = build_vehicle_blocks_for_timetables([outbound, inbound], "both")

        self.assertGreaterEqual(len(blocks), 4)
        for block in blocks:
            previous_end = None
            for trip in block["trips"]:
                if previous_end is not None:
                    self.assertGreaterEqual(trip["start_minutes"], previous_end)
                previous_end = trip["end_minutes"]
