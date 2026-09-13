import json
from datetime import date, datetime, time
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.cache import cache
from django.core.management import call_command
from django.db import DatabaseError
from django.test import Client, TestCase
from django.utils import timezone

from fleet.models import MBTOperator, fleet, vehicleTransferRequest
from fleet.views import build_board_trip_windows, build_vehicle_blocks_for_timetables, normalize_trip_minutes, stops_can_intertwine
from main.models import featureToggle
from routes.models import duty, dutyTrip, dayType, route, timetableEntry
from tracking.models import Trip


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


class MassAssignOverrideTests(TestCase):
    """Regression tests: override-existing on the mass table logger must
    clear the day's trips and then log the newly assigned board."""

    def _aware(self, day, at):
        return timezone.make_aware(datetime.combine(day, at))

    def _make_board(self, operator, day, name, start, end):
        board = duty.objects.create(
            duty_name=name, duty_operator=operator, board_type="running-boards"
        )
        board.duty_day.add(day)
        dutyTrip.objects.create(
            duty=board, inbound=False,
            start_time=start, end_time=end,
            start_at="A", end_at="B",
        )
        return board

    def _setup_override_case(self):
        owner = get_user_model().objects.create_user(
            username="override_owner", password="x"
        )
        operator = MBTOperator.objects.create(
            operator_name="Override Test Op", operator_code="OVR",
            owner=owner,
        )
        vehicle = fleet.objects.create(
            operator=operator, fleet_number="1", reg="OVR1",
            in_service=True, features=[],
        )
        selected_date = date(2026, 8, 24)  # a Monday
        day, _ = dayType.objects.get_or_create(
            name=selected_date.strftime("%A")
        )
        board1 = self._make_board(operator, day, "Board 1", time(8, 0), time(9, 0))
        board2 = self._make_board(operator, day, "Board 2", time(10, 0), time(11, 0))
        Trip.objects.create(
            trip_vehicle=vehicle, trip_board=board1,
            trip_start_at=self._aware(selected_date, time(8, 0)),
            trip_end_at=self._aware(selected_date, time(9, 0)),
        )
        return owner, operator, vehicle, selected_date, board1, board2

    def _post_batch(self, owner, operator, assignments, selected_date):
        client = Client()
        client.force_login(owner)
        return client.post(
            f"/operator/{operator.operator_slug}/vehicles/mass-assign/api/batch/",
            data=json.dumps({
                "assignments": assignments,
                "date": selected_date.isoformat(),
                "override": True,
            }),
            content_type="application/json",
        )

    def test_override_clears_day_then_logs_new_board(self):
        owner, operator, vehicle, selected_date, board1, board2 = self._setup_override_case()

        resp = self._post_batch(
            owner, operator,
            [{"vehicle_id": vehicle.id, "board_id": board2.id}],
            selected_date,
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["results"][0]["success"], data)
        self.assertEqual(
            Trip.objects.filter(trip_vehicle=vehicle, trip_board=board1).count(), 0
        )
        self.assertEqual(
            Trip.objects.filter(trip_vehicle=vehicle, trip_board=board2).count(), 1
        )

    def test_override_with_empty_board_does_not_wipe_day(self):
        owner, operator, vehicle, selected_date, board1, _ = self._setup_override_case()
        empty_board = duty.objects.create(
            duty_name="Empty Board", duty_operator=operator,
            board_type="running-boards",
        )
        empty_board.duty_day.add(
            dayType.objects.get(name=selected_date.strftime("%A"))
        )

        resp = self._post_batch(
            owner, operator,
            [{"vehicle_id": vehicle.id, "board_id": empty_board.id}],
            selected_date,
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["results"][0]["success"], data)
        # Existing trips must be preserved.
        self.assertEqual(
            Trip.objects.filter(trip_vehicle=vehicle, trip_board=board1).count(), 1
        )


class DeleteErrorHandlingTests(TestCase):
    """Regression tests: route/board/vehicle deletes must degrade to a
    redirect + error message instead of a 500 when the database reports
    an error mid-delete (e.g. timeouts or lock contention on objects
    with a large amount of linked history)."""

    def _make_owner_operator(self, username, code):
        owner = get_user_model().objects.create_user(
            username=username, password="x"
        )
        operator = MBTOperator.objects.create(
            operator_name=f"{code} op", operator_code=code, owner=owner,
        )
        return owner, operator

    def _enable(self, *names):
        for name in names:
            featureToggle.objects.create(name=name, enabled=True)

    def test_route_delete_database_error_redirects(self):
        owner, operator = self._make_owner_operator("del_err_route", "DERRR")
        self._enable("delete_routes", "edit_routes")
        route_instance = route.objects.create(route_num="DERR", route_name="Err")
        route_instance.route_operators.add(operator)

        client = Client()
        client.force_login(owner)
        with mock.patch.object(route, "delete", side_effect=DatabaseError("boom")):
            resp = client.post(
                f"/operator/{operator.operator_slug}/route/{route_instance.id}/delete/"
            )

        self.assertEqual(resp.status_code, 302)
        self.assertTrue(route.objects.filter(id=route_instance.id).exists())

    def test_board_delete_database_error_redirects(self):
        owner, operator = self._make_owner_operator("del_err_board", "DERRB")
        self._enable("delete_boards")
        board = duty.objects.create(
            duty_name="Err Board", duty_operator=operator,
            board_type="running-boards",
        )

        client = Client()
        client.force_login(owner)
        with mock.patch.object(duty, "delete", side_effect=DatabaseError("boom")):
            resp = client.get(
                f"/operator/{operator.operator_slug}/running-boards/delete/{board.id}/"
            )

        self.assertEqual(resp.status_code, 302)
        self.assertTrue(duty.objects.filter(id=board.id).exists())

    def test_vehicle_delete_database_error_redirects(self):
        owner, operator = self._make_owner_operator("del_err_vehicle", "DERRV")
        self._enable("delete_vehicles")
        vehicle = fleet.objects.create(
            operator=operator, fleet_number="DERRV", reg="DERRV",
            features=[],
        )

        client = Client()
        client.force_login(owner)
        with mock.patch.object(fleet, "delete", side_effect=DatabaseError("boom")):
            resp = client.post(
                f"/operator/{operator.operator_slug}/vehicles/{vehicle.id}/delete/"
            )

        self.assertEqual(resp.status_code, 302)
        self.assertTrue(fleet.objects.filter(id=vehicle.id).exists())


class VehicleTransferScheduleTests(TestCase):
    """The 'Schedule Transfer?' controls on the vehicle edit forms must store
    the chosen date/time on the resulting pending transfer request."""

    def _setup_case(self, suffix):
        cache.clear()
        owner_a = get_user_model().objects.create_user(
            username=f"sched_owner_a_{suffix}", password="x"
        )
        owner_b = get_user_model().objects.create_user(
            username=f"sched_owner_b_{suffix}", password="x"
        )
        op_a = MBTOperator.objects.create(
            operator_name=f"Sched A {suffix}", operator_code=f"SCHA{suffix}",
            owner=owner_a,
        )
        op_b = MBTOperator.objects.create(
            operator_name=f"Sched B {suffix}", operator_code=f"SCHB{suffix}",
            owner=owner_b,
        )
        featureToggle.objects.get_or_create(
            name="edit_vehicles", defaults={"enabled": True}
        )
        featureToggle.objects.get_or_create(
            name="mass_edit_vehicles", defaults={"enabled": True}
        )
        return owner_a, owner_b, op_a, op_b

    def _make_vehicle(self, operator, number):
        return fleet.objects.create(
            operator=operator, fleet_number=number, reg=f"SCH{number}",
            in_service=True, features=[],
        )

    def _pending_request(self, op_a, op_b):
        return vehicleTransferRequest.objects.get(
            from_operator=op_a, to_operator=op_b,
            status=vehicleTransferRequest.PENDING,
        )

    def test_single_edit_scheduled_transfer_stores_datetime(self):
        owner_a, _, op_a, op_b = self._setup_case("t1")
        vehicle = self._make_vehicle(op_a, "T1")
        client = Client()
        client.force_login(owner_a)

        resp = client.post(
            f"/operator/{op_a.operator_slug}/vehicle/edit/{vehicle.id}/",
            {
                "operator": str(op_b.id),
                "schedule_transfer": "on",
                "transfer_scheduled_for": "2030-05-01T10:00",
            },
        )

        self.assertIn(resp.status_code, (301, 302))
        req = self._pending_request(op_a, op_b)
        self.assertEqual(list(req.vehicles.all()), [vehicle])
        self.assertEqual(
            req.scheduled_for, timezone.make_aware(datetime(2030, 5, 1, 10, 0))
        )
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.operator, op_a)
        self.assertFalse(vehicle.in_service)

    def test_single_edit_schedule_without_datetime_blocks_move(self):
        owner_a, _, op_a, op_b = self._setup_case("t2")
        vehicle = self._make_vehicle(op_a, "T2")
        client = Client()
        client.force_login(owner_a)

        resp = client.post(
            f"/operator/{op_a.operator_slug}/vehicle/edit/{vehicle.id}/",
            {
                "operator": str(op_b.id),
                "in_service": "on",
                "schedule_transfer": "on",
                "transfer_scheduled_for": "",
            },
        )

        self.assertIn(resp.status_code, (301, 302))
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.operator, op_a)
        self.assertTrue(vehicle.in_service)
        self.assertFalse(
            vehicleTransferRequest.objects.filter(
                from_operator=op_a, to_operator=op_b,
                status=vehicleTransferRequest.PENDING,
            ).exists()
        )
        messages = [m.message for m in get_messages(resp.wsgi_request)]
        self.assertTrue(
            any("Schedule Transfer" in m for m in messages), messages
        )

    def test_single_edit_schedule_in_the_past_blocks_move(self):
        owner_a, _, op_a, op_b = self._setup_case("t3")
        vehicle = self._make_vehicle(op_a, "T3")
        client = Client()
        client.force_login(owner_a)

        resp = client.post(
            f"/operator/{op_a.operator_slug}/vehicle/edit/{vehicle.id}/",
            {
                "operator": str(op_b.id),
                "schedule_transfer": "on",
                "transfer_scheduled_for": "2020-01-01T10:00",
            },
        )

        self.assertIn(resp.status_code, (301, 302))
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.operator, op_a)
        self.assertFalse(
            vehicleTransferRequest.objects.filter(
                from_operator=op_a, to_operator=op_b,
                status=vehicleTransferRequest.PENDING,
            ).exists()
        )

    def test_mass_edit_scheduled_transfer_groups_into_one_request(self):
        owner_a, _, op_a, op_b = self._setup_case("t4")
        vehicle1 = self._make_vehicle(op_a, "T4A")
        vehicle2 = self._make_vehicle(op_a, "T4B")
        client = Client()
        client.force_login(owner_a)

        resp = client.post(
            f"/operator/{op_a.operator_slug}/vehicles/mass-edit-bus/"
            f"?ids={vehicle1.id},{vehicle2.id}",
            {
                "edit_operator": "on",
                "operator": str(op_b.id),
                "schedule_transfer": "on",
                "transfer_scheduled_for": "2030-06-01T12:00",
            },
        )

        self.assertIn(resp.status_code, (301, 302))
        req = self._pending_request(op_a, op_b)
        self.assertEqual(set(req.vehicles.all()), {vehicle1, vehicle2})
        self.assertEqual(
            req.scheduled_for, timezone.make_aware(datetime(2030, 6, 1, 12, 0))
        )

    def test_single_edit_form_hides_schedule_row_initially(self):
        owner_a, _, op_a, _ = self._setup_case("t5")
        vehicle = self._make_vehicle(op_a, "T5")
        client = Client()
        client.force_login(owner_a)

        resp = client.get(
            f"/operator/{op_a.operator_slug}/vehicle/edit/{vehicle.id}/"
        )

        self.assertEqual(resp.status_code, 200)
        self.assertContains(
            resp, 'id="schedule-transfer-row" style="display:none;"'
        )

    def test_single_edit_scheduled_transfer_to_controlled_operator_stays_pending(self):
        owner_a, _, op_a, _ = self._setup_case("t7")
        op_c = MBTOperator.objects.create(
            operator_name="Sched C t7", operator_code="SCHCt7", owner=owner_a,
        )
        vehicle = self._make_vehicle(op_a, "T7")
        client = Client()
        client.force_login(owner_a)

        resp = client.post(
            f"/operator/{op_a.operator_slug}/vehicle/edit/{vehicle.id}/",
            {
                "operator": str(op_c.id),
                "in_service": "on",
                "schedule_transfer": "on",
                "transfer_scheduled_for": "2030-07-01T09:00",
            },
        )

        self.assertIn(resp.status_code, (301, 302))
        req = vehicleTransferRequest.objects.get(
            from_operator=op_a, to_operator=op_c,
            status=vehicleTransferRequest.SCHEDULED,
        )
        self.assertEqual(list(req.vehicles.all()), [vehicle])
        self.assertEqual(
            req.scheduled_for, timezone.make_aware(datetime(2030, 7, 1, 9, 0))
        )
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.operator, op_a)
        self.assertTrue(vehicle.in_service)

        # Once the date arrives, the command moves the bus automatically.
        vehicleTransferRequest.objects.filter(pk=req.pk).update(
            scheduled_for=timezone.now() - timezone.timedelta(minutes=1)
        )
        call_command("process_scheduled_transfers")
        req.refresh_from_db()
        self.assertEqual(req.status, vehicleTransferRequest.APPROVED)
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.operator, op_c)
        self.assertTrue(vehicle.in_service)

    def test_mass_edit_scheduled_transfer_to_controlled_operator_stays_pending(self):
        owner_a, _, op_a, _ = self._setup_case("t8")
        op_c = MBTOperator.objects.create(
            operator_name="Sched C t8", operator_code="SCHCt8", owner=owner_a,
        )
        vehicle = self._make_vehicle(op_a, "T8")
        client = Client()
        client.force_login(owner_a)

        resp = client.post(
            f"/operator/{op_a.operator_slug}/vehicles/mass-edit-bus/"
            f"?ids={vehicle.id}",
            {
                "edit_operator": "on",
                "operator": str(op_c.id),
                "schedule_transfer": "on",
                "transfer_scheduled_for": "2030-08-01T09:00",
            },
        )

        self.assertIn(resp.status_code, (301, 302))
        req = vehicleTransferRequest.objects.get(
            from_operator=op_a, to_operator=op_c,
            status=vehicleTransferRequest.SCHEDULED,
        )
        self.assertEqual(list(req.vehicles.all()), [vehicle])
        self.assertEqual(
            req.scheduled_for, timezone.make_aware(datetime(2030, 8, 1, 9, 0))
        )
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.operator, op_a)

    def test_scheduled_command_skips_future_dates(self):
        owner_a, _, op_a, _ = self._setup_case("t9")
        op_c = MBTOperator.objects.create(
            operator_name="Sched C t9", operator_code="SCHCt9", owner=owner_a,
        )
        vehicle = self._make_vehicle(op_a, "T9")
        req = vehicleTransferRequest.objects.create(
            from_operator=op_a, to_operator=op_c, from_user=owner_a,
            status=vehicleTransferRequest.SCHEDULED,
            scheduled_for=timezone.now() + timezone.timedelta(days=1),
        )
        req.vehicles.add(vehicle)
        vehicle.in_service = False
        vehicle.save(update_fields=["in_service"])

        call_command("process_scheduled_transfers")

        req.refresh_from_db()
        self.assertEqual(req.status, vehicleTransferRequest.SCHEDULED)
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.operator, op_a)

    def test_scheduled_command_declines_stale_ownership(self):
        owner_a, owner_b, op_a, _ = self._setup_case("t10")
        op_c = MBTOperator.objects.create(
            operator_name="Sched C t10", operator_code="SCHCt10", owner=owner_a,
        )
        vehicle = self._make_vehicle(op_a, "T10")
        req = vehicleTransferRequest.objects.create(
            from_operator=op_a, to_operator=op_c, from_user=owner_a,
            status=vehicleTransferRequest.SCHEDULED,
            scheduled_for=timezone.now() - timezone.timedelta(minutes=1),
        )
        req.vehicles.add(vehicle)
        # Bus has since moved elsewhere; the schedule is stale.
        vehicle.operator = owner_b_operator = MBTOperator.objects.create(
            operator_name="Sched X t10", operator_code="SCHXt10", owner=owner_b,
        )
        vehicle.save(update_fields=["operator"])

        call_command("process_scheduled_transfers")

        req.refresh_from_db()
        self.assertEqual(req.status, vehicleTransferRequest.DECLINED)
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.operator, owner_b_operator)

    def test_cancel_scheduled_transfer_restores_service(self):
        owner_a, _, op_a, _ = self._setup_case("t11")
        op_c = MBTOperator.objects.create(
            operator_name="Sched C t11", operator_code="SCHCt11", owner=owner_a,
        )
        vehicle = self._make_vehicle(op_a, "T11")
        req = vehicleTransferRequest.objects.create(
            from_operator=op_a, to_operator=op_c, from_user=owner_a,
            status=vehicleTransferRequest.SCHEDULED,
            scheduled_for=timezone.now() + timezone.timedelta(days=1),
        )
        req.vehicles.add(vehicle)
        vehicle.in_service = False
        vehicle.save(update_fields=["in_service"])
        client = Client()
        client.force_login(owner_a)

        resp = client.post(
            f"/operator/{op_a.operator_slug}/vehicles/transfer/{req.id}/cancel/"
        )

        self.assertIn(resp.status_code, (301, 302))
        req.refresh_from_db()
        self.assertEqual(req.status, vehicleTransferRequest.CANCELLED)
        vehicle.refresh_from_db()
        self.assertTrue(vehicle.in_service)
        self.assertEqual(vehicle.operator, op_a)

    def test_mass_edit_form_hides_schedule_row_initially(self):
        owner_a, _, op_a, _ = self._setup_case("t6")
        vehicle = self._make_vehicle(op_a, "T6")
        client = Client()
        client.force_login(owner_a)

        resp = client.get(
            f"/operator/{op_a.operator_slug}/vehicles/mass-edit-bus/"
            f"?ids={vehicle.id}"
        )

        self.assertEqual(resp.status_code, 200)
        self.assertContains(
            resp, 'id="schedule-transfer-row" style="display:none;"'
        )

    def test_due_scheduled_transfer_executes_on_fleet_page_visit(self):
        owner_a, _, op_a, _ = self._setup_case("t12")
        op_c = MBTOperator.objects.create(
            operator_name="Sched C t12", operator_code="SCHCt12", owner=owner_a,
        )
        vehicle = self._make_vehicle(op_a, "T12")
        req = vehicleTransferRequest.objects.create(
            from_operator=op_a, to_operator=op_c, from_user=owner_a,
            status=vehicleTransferRequest.SCHEDULED,
            scheduled_for=timezone.now() - timezone.timedelta(minutes=1),
        )
        req.vehicles.add(vehicle)
        vehicle.in_service = False
        vehicle.save(update_fields=["in_service"])
        client = Client()
        client.force_login(owner_a)

        # Visiting a fleet page processes due transfers lazily, no cron needed.
        resp = client.get(f"/operator/{op_a.operator_slug}/vehicles/api/")

        self.assertEqual(resp.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.status, vehicleTransferRequest.APPROVED)
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.operator, op_c)
        self.assertTrue(vehicle.in_service)

    def test_vehicle_detail_shows_scheduled_move_notice(self):
        owner_a, _, op_a, _ = self._setup_case("t13")
        op_c = MBTOperator.objects.create(
            operator_name="Sched C t13", operator_code="SCHCt13", owner=owner_a,
        )
        vehicle = self._make_vehicle(op_a, "T13")
        req = vehicleTransferRequest.objects.create(
            from_operator=op_a, to_operator=op_c, from_user=owner_a,
            status=vehicleTransferRequest.SCHEDULED,
            scheduled_for=timezone.make_aware(datetime(2030, 9, 1, 9, 0)),
        )
        req.vehicles.add(vehicle)
        featureToggle.objects.get_or_create(
            name="view_vehicles", defaults={"enabled": True}
        )
        client = Client()
        client.force_login(owner_a)

        resp = client.get(
            f"/operator/{op_a.operator_slug}/vehicles/{vehicle.id}/"
        )

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Scheduled to move to")
        self.assertContains(resp, op_c.operator_name)

    def test_mass_table_log_autofill_skips_slotting_under_override(self):
        # Regression: on an already-logged day, auto-fill must still pull
        # every day-valid board when "clear existing trips" (override) is
        # ticked, instead of slotting past the existing trips.
        cache.clear()
        owner = get_user_model().objects.create_user(
            username="autofill_owner", password="x"
        )
        operator = MBTOperator.objects.create(
            operator_name="Autofill Op", operator_code="AUTOF",
            owner=owner,
        )
        featureToggle.objects.get_or_create(
            name="mass_log_trips", defaults={"enabled": True}
        )
        client = Client()
        client.force_login(owner)

        resp = client.get(f"/operator/{operator.operator_slug}/vehicles/mass-assign")

        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn(
            "if (!override && b.first_trip_start && blockedUntil) {", content
        )
        self.assertNotIn(
            "if (b.first_trip_start && blockedUntil) {", content
        )
