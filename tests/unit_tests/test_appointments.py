#
#   Thiscovery API - THIS Institute’s citizen science platform
#   Copyright (C) 2019 THIS Institute
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   A copy of the GNU Affero General Public License is available in the
#   docs folder of this project.  It is also available www.gnu.org/licenses/
#
import local.dev_config  # sets environment variables
import local.secrets  # sets environment variables
import datetime

from http import HTTPStatus
from pprint import pprint

import thiscovery_lib.utilities as utils
import tests.testing_utilities as test_utils
from src.appointments import AcuityAppointmentEvent
from src.common.acuity_utilities import AcuityClient


class TestAcuityAppointmentEvent(test_utils.BaseTestCase):
    test_data = {
        'event_body': "action=appointment.scheduled&id=399682887&calendarID=4038206&appointmentTypeID=14792299",
        'appointment_type_id': 14792299,
        'email': 'clive@email.co.uk',
        'project_task_id': '07af2fbe-5cd1-447f-bae1-3a2f8de82829',
        'status': 'active',
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.aae = AcuityAppointmentEvent(cls.test_data['event_body'], cls.logger)
        cls.aae.ddb_client.put_item(
            table_name=cls.aae.appointment_type_table,
            key=str(cls.test_data['appointment_type_id']),
            item_type='acuity_appointment_type',
            item_details=None,
            item={
                'project_task_id': cls.test_data['project_task_id'],
                'status': cls.test_data['status'],
            },
            update_allowed=True
        )

    @classmethod
    def tearDownClass(cls):
        cls.aae.ddb_client.delete_item(cls.aae.appointment_type_table, str(cls.test_data['appointment_type_id']))
        super().tearDownClass()

    def test_get_appointment_details(self):
        email, appointment_type_id = self.aae.get_appointment_details()
        self.assertEqual(self.test_data['email'], email)
        self.assertEqual(14792299, appointment_type_id)

    def test_get_project_task_id_and_status(self):
        project_task_id, status = self.aae.get_project_task_id_and_status()
        self.assertEqual(self.test_data['project_task_id'], project_task_id)
        self.assertEqual(self.test_data['status'], status)

    def test_main(self):
        status_code = self.aae.main()['statusCode']
        self.assertEqual(HTTPStatus.NO_CONTENT, status_code)
