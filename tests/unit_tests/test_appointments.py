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
import copy

from http import HTTPStatus

import src.appointments as app
import thiscovery_lib.utilities as utils
from testing_utilities import AppointmentsTestCase


class TestAcuityAppointment(AppointmentsTestCase):

    def test_01_get_appointment_details_ok(self):
        aa1 = copy.copy(self.aa1)
        result = aa1.get_appointment_info_from_acuity()
        self.assertEqual(self.test_data['email'], result['email'])
        self.assertEqual(self.test_data['email'], aa1.participant_email)
        self.assertEqual(self.test_data['calendar_name'], result['calendar'])

    def test_02_ddb_dump_and_load_ok(self):
        aa1 = copy.copy(self.aa1)
        dump_result = aa1.ddb_dump()
        self.assertEqual(HTTPStatus.OK, dump_result['ResponseMetadata']['HTTPStatusCode'])
        with self.assertRaises(AttributeError):
            aa1.type
        aa1.ddb_load()
        self.assertEqual('acuity-appointment', aa1.type)
        self.clear_appointments_table()

    def test_03_get_appointment_item_from_ddb_ok(self):
        aa1 = copy.copy(self.aa1)
        aa1.ddb_dump()
        result = aa1.get_appointment_item_from_ddb()
        self.assertEqual('acuity-appointment', result['type'])
        self.clear_appointments_table()

    def test_04_update_link_ok(self):
        aa1 = copy.copy(self.aa1)
        aa1.ddb_dump()
        test_link = 'www.thiscovery.org'
        result = aa1.update_link(test_link)
        self.assertEqual(HTTPStatus.OK, result)
        self.assertEqual(test_link, aa1.link)
        self.clear_appointments_table()

    def test_05_get_participant_user_id_ok(self):
        result = self.aa1.get_participant_user_id()
        self.assertEqual(self.test_data['participant_user_id'], result)

    def test_06_ddb_load_non_existent_appointment_id(self):
        non_existent_id = 'this-is-not-a-real-id'
        aa = app.AcuityAppointment(appointment_id=non_existent_id)
        with self.assertRaises(utils.ObjectDoesNotExistError) as context:
            aa.ddb_load()
        err = context.exception
        err_msg = err.args[0]
        self.assertEqual(f'Appointment {non_existent_id} could not be found in Dynamodb', err_msg)
