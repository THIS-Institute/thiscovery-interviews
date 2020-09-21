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
import datetime

from http import HTTPStatus
from pprint import pprint

import src.common.utilities as utils
import tests.testing_utilities as test_utils
from src.appointments import AcuityAppointment, AcuityEvent, APPOINTMENTS_TABLE
from src.common.dynamodb_utilities import Dynamodb
from src.common.acuity_utilities import AcuityClient


def clear_appointments_table():
    ddb_client = Dynamodb()
    ddb_client.delete_all(
        table_name=APPOINTMENTS_TABLE,
    )


class TestAcuityAppointment(test_utils.BaseTestCase):
    test_data = {
        'appointment_id': 399682887,
        'appointment_type_id': 14792299,
        'calendar_name': 'André',
        'email': 'clive@email.co.uk',
        'project_task_id': '07af2fbe-5cd1-447f-bae1-3a2f8de82829',
        'status': 'active',
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.aa = AcuityAppointment(
            appointment_id=cls.test_data['appointment_id'],
            logger=cls.logger,
            type_id=cls.test_data['appointment_type_id'],
        )
        cls.aa.ddb_client.put_item(
            table_name=cls.aa.appointment_type_table,
            key=str(cls.test_data['appointment_type_id']),
            item_type='acuity_appointment_type',
            item_details=None,
            item={
                'project_task_id': cls.test_data['project_task_id'],
                'status': cls.test_data['status'],
                'user_specific_interview_link': True,
            },
            update_allowed=True,
        )
        clear_appointments_table()

    def test_01_get_appointment_type_id_to_name_map_ok(self):
        result = self.aa.get_appointment_type_id_to_name_map()
        self.assertEqual('Development appointment', result['14649911'])
        self.assertEqual('Test appointment', result['14792299'])

    def test_02_get_appointment_name_ok(self):
        result = self.aa.get_appointment_name()
        self.assertEqual('Test appointment', result)

    def test_03_get_appointment_details_ok(self):
        email, type_id = self.aa.get_appointment_details()
        self.assertEqual(self.test_data['email'], email)
        self.assertEqual(self.aa.type_id, type_id)
        self.assertEqual(self.test_data['calendar_name'], self.aa.calendar_name)

    def test_04_store_in_dynamodb_ok(self):
        result = self.aa.store_in_dynamodb()
        self.assertEqual(HTTPStatus.OK, result['ResponseMetadata']['HTTPStatusCode'])
        clear_appointments_table()

    def test_05_update_link_ok(self):
        self.aa.store_in_dynamodb()
        result = self.aa.update_link('www.thiscovery.org')
        self.assertEqual(HTTPStatus.OK, result['ResponseMetadata']['HTTPStatusCode'])
        clear_appointments_table()

    def test_06_get_appointment_item_from_ddb_ok(self):
        self.aa.store_in_dynamodb()
        result = self.aa.get_appointment_item_from_ddb()
        self.assertEqual('acuity-appointment', result['type'])
        clear_appointments_table()

    def test_07_get_appointment_type_info_from_ddb_ok(self):
        project_task_id, type_status = self.aa.get_appointment_type_info_from_ddb()
        self.assertEqual(self.test_data['project_task_id'], project_task_id)
        self.assertEqual(self.test_data['status'], type_status)


class TestAcuityEvent(test_utils.BaseTestCase):
    test_data = {
        'event_body': "action=appointment.scheduled&id=399682887&calendarID=4038206&appointmentTypeID=14792299",
    }

    def test_08_init_ok(self):
        ae = AcuityEvent(
            acuity_event=self.test_data['event_body'],
            logger=self.logger,
        )
        self.assertEqual('scheduled', ae.action)
        self.assertEqual('399682887', ae.appointment_id)
        self.assertEqual('4038206', ae.calendar_id)
        self.assertEqual('14792299', ae.type_id)
        self.assertEqual('active', ae.appointment.type_status)

    def test_get_appointment_details(self):
        email, appointment_type_id = self.aae.appointment.get_appointment_details()
        self.assertEqual(self.test_data['email'], email)
        self.assertEqual(14792299, appointment_type_id)

    def test_get_project_task_id_and_status(self):
        project_task_id, status = self.aae.appointment.get_appointment_type_info_from_ddb()
        self.assertEqual(self.test_data['project_task_id'], project_task_id)
        self.assertEqual(self.test_data['status'], status)

    def test_process_event(self):
        status_code = self.aae.process()['statusCode']
        self.assertEqual(HTTPStatus.NO_CONTENT, status_code)
