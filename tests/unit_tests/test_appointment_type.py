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

import appointments as app
from testing_utilities import AppointmentsTestCase


class TestAppointmentType(AppointmentsTestCase):

    @classmethod
    def setUpClass(cls):
        cls.at = app.AppointmentType()
        cls.at.type_id = str(cls.test_data['dev_appointment_type_id'])

    def test_01_get_appointment_type_id_to_info_map_ok(self):
        result = self.at.get_appointment_type_id_to_info_map()
        app_type = result[self.at.type_id]
        del app_type['calendarIDs']  # ignore associated calendars as we might frequently add/remove calendars
        expected_type = {
            'active': True,
            'addonIDs': [],
            # 'calendarIDs': [4038206, 3887437],
            'category': '_Tech development',
            'classSize': None,
            'color': '#AC53B4',
            'description': '',
            'duration': 30,
            'formIDs': [1606751],
            'id': 14649911,
            'image': '',
            'name': 'Development appointment',
            'paddingAfter': 0,
            'paddingBefore': 0,
            'price': '0.00',
            'private': True,
            'schedulingUrl': 'https://app.acuityscheduling.com/schedule.php?owner=19499339&appointmentType=14649911',
            'type': 'service'
        }
        self.assertEqual(expected_type, app_type)

    def test_02_get_appointment_type_info_from_acuity_ok(self):
        at = copy.copy(self.at)
        at.get_appointment_type_info_from_acuity()
        self.assertEqual('Development appointment', at.name)
        self.assertEqual('_Tech development', at.category)

    def test_03_ddb_dump_and_load_ok(self):
        at = copy.copy(self.at)
        at.get_appointment_type_info_from_acuity()
        dump_result = at.ddb_dump(update_allowed=True)
        self.assertEqual(HTTPStatus.OK, dump_result['ResponseMetadata']['HTTPStatusCode'])
        with self.assertRaises(AttributeError):
            at.type
        at.ddb_load()
        self.assertEqual('acuity-appointment-type', at.type)

    def test_04_as_dict_ok(self):
        at = copy.copy(self.at)
        at.get_appointment_type_info_from_acuity()
        expected_result = {
            'category': '_Tech development',
            'has_link': None,
            'name': 'Development appointment',
            'project_task_id': None,
            'send_notifications': None,
            'templates': None,
            'type_id': '14649911',
        }
        self.assertEqual(expected_result, at.as_dict())

    def test_05_from_dict_ok(self):
        at = copy.copy(self.at)
        at.get_appointment_type_info_from_acuity()
        at.from_dict(
            {
                'has_link': True,
                'templates': 'test_template',
                'project_task_id': self.test_data['project_task_id'],
            }
        )
        expected_result = {
            'category': '_Tech development',
            'has_link': True,
            'name': 'Development appointment',
            'project_task_id': self.test_data['project_task_id'],
            'send_notifications': None,
            'templates': 'test_template',
            'type_id': '14649911',
        }
        self.assertDictEqual(expected_result, at.as_dict())