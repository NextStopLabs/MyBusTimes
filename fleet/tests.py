from django.test import TestCase
from django.utils import timezone
from datetime import date, time

from fleet.views import build_board_trip_windows, build_vehicle_blocks_for_timetables, normalize_trip_minutes, stops_can_intertwine
from routes.models import dutyTrip, route, timetableEntry


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

    def test_circular_route_trips_chain_onto_one_vehicle(self):
        route_instance = route.objects.create(route_num="C1", route_name="Circular Service")
        circular = timetableEntry.objects.create(
            route=route_instance,
            inbound=False,
            circular=True,
            active=True,
            stop_times={
                "High St_idx_0": {
                    "stopname": "High St",
                    "order": 0,
                    "times": ["07:00", "07:40", "08:20"],
                },
                "High St Loop_idx_1": {
                    "stopname": "High St",
                    "order": 1,
                    "times": ["07:30", "08:10", "08:50"],
                },
            },
        )

        blocks = build_vehicle_blocks_for_timetables([circular], "both")

        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["trip_count"], 3)

    def test_rest_minutes_requires_layover_between_chained_trips(self):
        route_instance = route.objects.create(route_num="R2", route_name="Rest Service")
        outbound = timetableEntry.objects.create(
            route=route_instance,
            inbound=False,
            active=True,
            stop_times={
                "A_idx_0": {"stopname": "A", "order": 0, "times": ["07:00"]},
                "B_idx_1": {"stopname": "B", "order": 1, "times": ["07:30"]},
            },
        )
        inbound = timetableEntry.objects.create(
            route=route_instance,
            inbound=True,
            active=True,
            stop_times={
                "B_idx_0": {"stopname": "B", "order": 0, "times": ["07:32"]},
                "A_idx_1": {"stopname": "A", "order": 1, "times": ["08:02"]},
            },
        )

        blocks_0 = build_vehicle_blocks_for_timetables([outbound, inbound], "both")
        blocks_3 = build_vehicle_blocks_for_timetables([outbound, inbound], "both", rest_minutes=3)

        self.assertEqual(len(blocks_0), 1)
        self.assertEqual(len(blocks_3), 2)

    def test_intertwine_minimises_boards_for_similarly_named_terminals(self):
        route_a = route.objects.create(route_num="A1", route_name="Outbound")
        route_b = route.objects.create(route_num="B1", route_name="Return")
        outbound = timetableEntry.objects.create(
            route=route_a,
            inbound=False,
            active=True,
            stop_times={
                "central_idx_0": {"stopname": "Central Bus Station (Stand A)", "order": 0, "times": ["08:00", "09:10"]},
                "riverside_idx_1": {"stopname": "Riverside Terminus", "order": 1, "times": ["08:30", "09:40"]},
            },
        )
        inbound = timetableEntry.objects.create(
            route=route_b,
            inbound=True,
            active=True,
            stop_times={
                "riverside_idx_0": {"stopname": "Riverside Terminal", "order": 0, "times": ["08:35", "09:45"]},
                "central_idx_1": {"stopname": "Central Bus Stn (Stand C)", "order": 1, "times": ["09:05", "10:15"]},
            },
        )

        blocks = build_vehicle_blocks_for_timetables(
            [outbound, inbound], "both", intertwine=True,
        )

        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["trip_count"], 4)

    def test_intertwine_matches_stops_that_are_geographically_close(self):
        # Two terminal names that share no words should still be treated as the
        # same practical stop when their coordinates are within the intertwine
        # radius (one mile). This lets routes that terminate close together
        # interleave their vehicles even when the timetable names differ.
        close_a = (52.675579, -2.448044)
        close_b = (52.681463, -2.453917)  # ~764 m from close_a

        self.assertFalse(
            stops_can_intertwine("Terminal Alpha North", "Unrelated Delta Name", None, None)
        )
        self.assertTrue(
            stops_can_intertwine(
                "Terminal Alpha North", "Unrelated Delta Name", close_a, close_b
            )
        )

        far_c = (52.701056, -2.516615)  # several km away
        self.assertFalse(
            stops_can_intertwine(
                "Terminal Alpha North", "Unrelated Delta Name", close_a, far_c
            )
        )

    def test_board_trip_windows_roll_end_and_following_trips_after_midnight(self):
        service_date = date(2026, 6, 5)
        trips = [
            dutyTrip(start_time=time(23, 40), end_time=time(0, 20)),
            dutyTrip(start_time=time(0, 35), end_time=time(1, 5)),
        ]

        windows = build_board_trip_windows(trips, service_date)

        first_start = timezone.localtime(windows[0][1])
        first_end = timezone.localtime(windows[0][2])
        second_start = timezone.localtime(windows[1][1])
        second_end = timezone.localtime(windows[1][2])

        self.assertEqual(first_start.date(), service_date)
        self.assertEqual(first_end.date(), date(2026, 6, 6))
        self.assertEqual(second_start.date(), date(2026, 6, 6))
        self.assertEqual(second_end.date(), date(2026, 6, 6))
        self.assertGreater(windows[0][2], windows[0][1])
        self.assertGreater(windows[1][1], windows[0][2])

    def test_board_trip_windows_keep_daytime_trips_in_chronological_order(self):
        service_date = date(2026, 6, 5)
        trips = [
            dutyTrip(start_time=time(8, 0), end_time=time(8, 30)),
            dutyTrip(start_time=time(21, 0), end_time=time(21, 30)),
        ]

        windows = build_board_trip_windows(trips, service_date)

        self.assertEqual([window[0].start_time for window in windows], [time(8, 0), time(21, 0)])
        self.assertTrue(all(window[1].date() == service_date for window in windows))

    def test_board_trip_windows_prefer_midnight_gap_when_gaps_tie(self):
        service_date = date(2026, 6, 5)
        trips = [
            dutyTrip(start_time=time(8, 0), end_time=time(8, 30)),
            dutyTrip(start_time=time(20, 0), end_time=time(20, 30)),
        ]

        windows = build_board_trip_windows(trips, service_date)

        self.assertEqual([window[0].start_time for window in windows], [time(8, 0), time(20, 0)])
