from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from main.models import CustomUser, region
from fleet.models import (
    liverie, vehicleType, group, organisation, MBTOperator, companyUpdate,
    helperPerm, helper, fleet, fleetChange, operatorType, reservedOperatorName, ticket
)
from django.conf import settings
import json
from pathlib import Path


class FleetModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username="testuser", password="testpass")
        self.region = region.objects.create(region_name="Test Region", region_code="TR1")
        self.group = group.objects.create(group_name="Test Group", group_owner=self.user)
        self.organisation = organisation.objects.create(organisation_name="Test Org", organisation_owner=self.user)

        self.operator = MBTOperator.objects.create(
            operator_name="Test Operator",
            operator_code="TOP",
            owner=self.user,
            group=self.group,
            organisation=self.organisation
        )
        self.operator.region.set([self.region])

        self.livery = liverie.objects.create(
            name="Test Livery",
            colour="#FF0000",
            added_by=self.user
        )

        self.vehicle_type = vehicleType.objects.create(
            type_name="Single Decker",
            added_by=self.user,
            aproved_by=self.user
        )

        self.fleet = fleet.objects.create(
            operator=self.operator,
            fleet_number="1234",
            reg="AB12 XYZ",
            livery=self.livery,
            vehicleType=self.vehicle_type,
            last_modified_by=self.user,
            features={}
        )

    def test_str_methods(self):
        self.assertEqual(str(self.livery), f"{self.livery.id} - {self.livery.name}")
        self.assertEqual(str(self.vehicle_type), "Single Decker")
        self.assertEqual(str(self.group), "Test Group")
        self.assertEqual(str(self.organisation), "Test Org")
        self.assertEqual(str(self.operator), "Test Operator")
        self.assertEqual(str(self.fleet), "1234 - AB12 XYZ - Test Livery - Test Operator - Single Decker")

    def test_company_update_str(self):
        update = companyUpdate.objects.create(operator=self.operator, update_text="New update")
        self.assertIn("New update", str(update))

    def test_helper_and_perm_str(self):
        perm = helperPerm.objects.create(perm_name="Access Panel", perms_level=2)
        self.assertEqual(str(perm), "Access Panel (Level 2)")
        helper_obj = helper.objects.create(operator=self.operator, helper=self.user)
        helper_obj.perms.add(perm)
        self.assertEqual(str(helper_obj), f"{self.operator.operator_name} - {self.user.username}")

    def test_fleet_change_str(self):
        change = fleetChange.objects.create(
            vehicle=self.fleet,
            operator=self.operator,
            user=self.user,
            approved_by=self.user
        )
        self.assertIn("1234", str(change))

    def test_operator_type_str(self):
        op_type = operatorType.objects.create(operator_type_name="Virtual Company")
        self.assertEqual(str(op_type), "Virtual Company")

    def test_reserved_operator_name_str(self):
        reserved = reservedOperatorName.objects.create(operator_name="Test Bus", owner=self.user)
        self.assertIn("Not Approved", str(reserved))

    def test_reserved_operator_name_validation(self):
        json_dir = Path(settings.MEDIA_ROOT) / "JSON"
        json_dir.mkdir(parents=True, exist_ok=True)
        forbidden_file = json_dir / "non-reservable-names.json"
        forbidden_file.write_text(json.dumps(["badword", "test"]))

        reserved = reservedOperatorName(operator_name="BadWord Ltd", owner=self.user)
        with self.assertRaises(ValidationError):
            reserved.clean()

    def test_reserved_operator_name_blocks_other_users(self):
        other_user = CustomUser.objects.create_user(username="otheruser", password="testpass")
        reservedOperatorName.objects.create(operator_name="Reserved Bus", owner=self.user)

        reservation = reservedOperatorName.blocking_reservation_for_user("reserved bus", other_user)

        self.assertIsNotNone(reservation)

    def test_reserved_operator_name_blocks_other_users_with_mixed_capitals(self):
        other_user = CustomUser.objects.create_user(username="otheruser", password="testpass")
        reservedOperatorName.objects.create(operator_name="Reserved Bus", owner=self.user)

        reservation = reservedOperatorName.blocking_reservation_for_user("rEsErVeD bUs", other_user)

        self.assertIsNotNone(reservation)

    def test_reserved_operator_name_blocks_names_containing_reserved_name(self):
        other_user = CustomUser.objects.create_user(username="otheruser", password="testpass")
        reservedOperatorName.objects.create(operator_name="Reserved Bus", owner=self.user)

        reservation = reservedOperatorName.blocking_reservation_for_user("My Reserved Bus Company", other_user)

        self.assertIsNotNone(reservation)

    def test_reserved_operator_name_allows_owner(self):
        reservedOperatorName.objects.create(operator_name="Reserved Bus", owner=self.user)

        reservation = reservedOperatorName.blocking_reservation_for_user("Reserved Bus", self.user)

        self.assertIsNone(reservation)

    def test_reserved_operator_name_blocks_superuser_when_not_owner_or_allowed(self):
        superuser = CustomUser.objects.create_superuser(
            username="superuser",
            email="super@example.com",
            password="testpass",
        )
        reservedOperatorName.objects.create(operator_name="Reserved Bus", owner=self.user)

        reservation = reservedOperatorName.blocking_reservation_for_user("Reserved Bus", superuser)

        self.assertIsNotNone(reservation)

    def test_reserved_operator_name_allows_whitelisted_user(self):
        other_user = CustomUser.objects.create_user(username="otheruser", password="testpass")
        reservation = reservedOperatorName.objects.create(operator_name="Reserved Bus", owner=self.user)
        reservation.allowed_users.add(other_user)

        blocking_reservation = reservedOperatorName.blocking_reservation_for_user("Reserved Bus", other_user)

        self.assertIsNone(blocking_reservation)

    def test_reserved_operator_name_check_endpoint_blocks_other_users(self):
        other_user = CustomUser.objects.create_user(username="otheruser", password="testpass")
        reservedOperatorName.objects.create(operator_name="Reserved Bus", owner=self.user)
        self.client.force_login(other_user)

        response = self.client.get('/operator/reserved-name/check/', {'operator_name': 'My rEsErVeD bUs Company'})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['reserved'])
        self.assertEqual(
            response.json()['message'],
            "This operator name (Reserved Bus) is reserved, if you think this is a mistake please open a ticket via discord or on the site",
        )

    def test_ticket_str(self):
        t = ticket.objects.create(
            operator=self.operator,
            ticket_name="Daily Pass",
            ticket_price=3.50
        )
        self.assertEqual(str(t), "Daily Pass - Test Operator")
