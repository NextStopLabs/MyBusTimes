import json
from datetime import date, time, datetime, timedelta

from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model

from fleet.models import MBTOperator, fleet
from routes.models import duty, dutyTrip, dayType
from tracking.models import Trip


def aware(d, t):
    return timezone.make_aware(datetime.combine(d, t))


class OverrideReproTest(TestCase):
    def test_override_clears_then_logs(self):
        User = get_user_model()
        owner = User.objects.create_user(username="override_owner", password="x")
        op = MBTOperator.objects.create(
            operator_name="Override Test Op", operator_code="OVR", owner=owner
        )
        vehicle = fleet.objects.create(
            operator=op, fleet_number="1", reg="OVR1", in_service=True
        )

        selected_date = date(2026, 8, 24)  # a Monday
        day = dayType.objects.create(name=selected_date.strftime("%A"))

        board1 = duty.objects.create(
            duty_name="Board 1", duty_operator=op, board_type="running-boards"
        )
        board1.duty_day.add(day)
        dutyTrip.objects.create(
            duty=board1, inbound=False,
            start_time=time(8, 0), end_time=time(9, 0),
            start_at="A", end_at="B",
        )

        board2 = duty.objects.create(
            duty_name="Board 2", duty_operator=op, board_type="running-boards"
        )
        board2.duty_day.add(day)
        dutyTrip.objects.create(
            duty=board2, inbound=False,
            start_time=time(10, 0), end_time=time(11, 0),
            start_at="C", end_at="D",
        )

        # Existing trip: board 1 already logged on this vehicle for the day
        Trip.objects.create(
            trip_vehicle=vehicle, trip_board=board1,
            trip_start_at=aware(selected_date, time(8, 0)),
            trip_end_at=aware(selected_date, time(9, 0)),
        )

        c = Client()
        c.force_login(owner)
        url = f"/operator/{op.operator_slug}/vehicles/mass-assign/api/batch/"
        resp = c.post(
            url,
            data=json.dumps({
                "assignments": [{"vehicle_id": vehicle.id, "board_id": board2.id}],
                "date": selected_date.isoformat(),
                "override": True,
            }),
            content_type="application/json",
        )
        print("STATUS:", resp.status_code)
        print("BODY:", resp.content.decode()[:2000])

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["results"][0]["success"], data)

        remaining_board1 = Trip.objects.filter(
            trip_vehicle=vehicle, trip_board=board1
        ).count()
        new_board2 = Trip.objects.filter(
            trip_vehicle=vehicle, trip_board=board2
        ).count()
        print("remaining board1 trips:", remaining_board1)
        print("new board2 trips:", new_board2)
        self.assertEqual(remaining_board1, 0)
        self.assertEqual(new_board2, 1)
