from django.test import TestCase

from fleet.models import group, reservedOperatorName
from main.models import CustomUser


class GroupReservationTests(TestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(username="reservation-owner")
        self.other_user = CustomUser.objects.create_user(username="group-user")

    def test_create_group_blocks_reserved_operator_name(self):
        reservedOperatorName.objects.create(operator_name="Reserved Bus", owner=self.owner)
        self.client.force_login(self.other_user)

        response = self.client.post('/group/create/', {
            'group_name': 'My Reserved Bus Group',
            'order_by': group.OrderBy.FLEET_NUMBER,
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(group.objects.filter(group_name__iexact='My Reserved Bus Group').exists())

    def test_edit_group_blocks_reserved_operator_name(self):
        existing_group = group.objects.create(group_name="Normal Group", group_owner=self.other_user)
        reservedOperatorName.objects.create(operator_name="Reserved Bus", owner=self.owner)
        self.client.force_login(self.other_user)

        response = self.client.post(f'/group/{existing_group.group_name}/edit/', {
            'group_name': 'Reserved Bus Fans',
            'order_by': group.OrderBy.FLEET_NUMBER,
        })

        existing_group.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(existing_group.group_name, "Normal Group")
