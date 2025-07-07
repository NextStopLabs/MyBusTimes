from django.test import TestCase
from .models import route, stop, serviceUpdate, dayType, timetableEntry, routeStop, duty, dutyTrip, transitAuthoritiesColour
from fleet.models import MBTOperator
from django.contrib.auth import get_user_model
from gameData.models import game
from datetime import datetime, date, time

class RouteModelsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.operator = MBTOperator.objects.create(operator_name="Test Operator", operator_code="TST", owner=self.user)
        self.route = route.objects.create(
            route_num="X12",
            route_name="Mainstone",
            inbound_destination="Fairhaven",
            outbound_destination="Mainstone"
        )
        self.route.route_operators.set([self.operator])

        self.daytype = dayType.objects.create(name="Weekday")

        self.g = game.objects.create(game_name="Test Game")
        self.stop = stop.objects.create(
            stop_name="Test Stop",
            latitude=52.0,
            longitude=0.1,
            game=self.g
        )

    def test_route_str(self):
        expected = "X12 - Mainstone - Fairhaven - Mainstone"
        self.assertEqual(str(self.route), expected)

    def test_day_type_str(self):
        self.assertEqual(str(self.daytype), "Weekday")

    def test_stop_str(self):
        self.assertEqual(str(self.stop), "Test Stop")

    def test_service_update_str(self):
        update = serviceUpdate.objects.create(
            start_date=date.today(),
            end_date=date.today(),
            update_title="Route Closure",
            update_description="Closed for works."
        )
        update.effected_route.set([self.route])
        expected = f"X12 - {date.today()} - {date.today()}"
        self.assertEqual(str(update), expected)

    def test_timetable_entry_str(self):
        entry = timetableEntry.objects.create(
            route=self.route,
            inbound=True
        )
        entry.day_type.set([self.daytype])
        expected = f"X12 - Inbound - (Weekday)"
        self.assertEqual(str(entry), expected)

    def test_route_stop_str(self):
        rs = routeStop.objects.create(route=self.route, inbound=True, circular=False, stops={"stops": []})
        self.assertEqual(str(rs), str(self.route.id))

    def test_duty_str(self):
        d = duty.objects.create(duty_name="D1", board_type="duty")
        d.duty_day.set([self.daytype])
        self.assertEqual(str(d), "D1 (Duty)")

    def test_duty_trip_str(self):
        d = duty.objects.create(duty_name="D2")
        dt = dutyTrip.objects.create(
            duty=d,
            route="X12",
            start_time=time(8, 0),
            end_time=time(9, 0),
            start_at="Stop A",
            end_at="Stop B"
        )
        expected = "D2 - X12 - Stop A to Stop B"
        self.assertEqual(str(dt), expected)

    def test_transit_authority_colour_str(self):
        t = transitAuthoritiesColour.objects.create(
            authority_code="TFL",
            primary_colour="#000000",
            secondary_colour="#FFFFFF"
        )
        self.assertEqual(str(t), "TFL")
