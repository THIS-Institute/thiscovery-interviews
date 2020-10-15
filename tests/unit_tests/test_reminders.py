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
import datetime
import time

from dateutil import parser
from http import HTTPStatus
from pprint import pprint

import src.appointments as app
import src.reminders as rem

import common.utilities as utils
import tests.test_data as test_data
import tests.testing_utilities as test_utils
from src.common.dynamodb_utilities import Dynamodb


TEST_DATETIME_1 = datetime.datetime(
    year=2020,
    month=9,
    day=27,
    hour=13,
    minute=40,
    second=45,
)

TEST_DATETIME_2 = datetime.datetime(
    year=2020,
    month=10,
    day=1,
    hour=13,
    minute=40,
    second=45,
)


class RemindersTestCase(test_utils.BaseTestCase, test_utils.DdbMixin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rh = rem.RemindersHandler(
            logger=cls.logger
        )
        cls.populate_appointments_table()

    def test_01_get_appointments_to_be_reminded_ok(self):
        result = self.rh.get_appointments_to_be_reminded(now=TEST_DATETIME_1)
        expected_result = ['448161724']
        self.assertEqual(expected_result, result)

    def test_02_get_appointments_to_be_reminded_excludes_appointments_that_have_just_been_notified(self):
        result = self.rh.get_appointments_to_be_reminded(now=TEST_DATETIME_2)
        expected_result = list()
        self.assertEqual(expected_result, result)

    def test_03_send_reminders_ok(self):
        self.clear_notifications_table()
        rh = rem.RemindersHandler(logger=self.logger)
        rh.target_appointment_ids = rh.get_appointments_to_be_reminded(now=TEST_DATETIME_1)
        now = utils.now_with_tz()
        result = rh.send_reminders()
        expected_result = [
            (HTTPStatus.NO_CONTENT, '448161724')
        ]
        self.assertEqual(expected_result, result)

        # check notification
        notifications = self.ddb_client.scan(
            table_name=self.notifications_table,
            table_name_verbatim=True,
        )
        self.assertEqual(1, len(notifications))
        attributes_to_ignore = [
            'created',
            'id',
            'modified',
            'processing_error_message',
            'processing_fail_count',
            'processing_status',
        ]
        for n in notifications:
            for a in attributes_to_ignore:
                del n[a]
        expected_notifications = [{
            'details': {
                'custom_properties': {
                    'appointment_date': 'Sunday 28 September 2025',
                    'appointment_duration': '30 minutes',
                    'appointment_reschedule_url': 'https://app.acuityscheduling.com/schedule.php?owner=19499339&action=appt&id%5B%5D=ab81fa72b0d0c1dead5057103c292bd3',
                    'appointment_time': '13:00',
                    'interview_url': 'We will call you on the phone number provided',
                    'interviewer_first_name': 'André',
                    'project_short_name': 'PSFU-05-pub-act',
                    'user_first_name': 'Altha'
                },
                'template_name': 'NA_interview_reminder_web_participant',
                'to_recipient_email': 'altha@email.co.uk'
            },
            'label': 'NA_interview_reminder_web_participant_altha@email.co.uk',
            'type': 'transactional-email'
        }]
        self.assertCountEqual(expected_notifications, notifications)

        # check appointment latest notification updated in ddb
        appointment = app.AcuityAppointment(appointment_id='448161724')
        appointment.ddb_load()
        latest_notification_datetime = parser.parse(appointment.latest_participant_notification)
        difference = abs(now - latest_notification_datetime)
        self.assertLess(difference.seconds, 20)

        # new reminder attempt results in no notification
        self.clear_notifications_table()
        result = rem.interview_reminder_handler(dict(), context=None)
        expected_result = list()
        self.assertEqual(expected_result, result)
        notifications = self.ddb_client.scan(
            table_name=self.notifications_table,
            table_name_verbatim=True,
        )
        self.assertEqual(0, len(notifications))

    def test_04_send_reminders_no_appointments_to_remind(self):
        rh = copy.copy(self.rh)
        rh.target_appointment_ids = rh.get_appointments_to_be_reminded(now=TEST_DATETIME_2)
        result = rh.send_reminders()
        self.assertEqual(list(), result)
        self.clear_notifications_table()
        notifications = self.ddb_client.scan(
            table_name=self.notifications_table,
            table_name_verbatim=True,
        )
        self.assertEqual(list(), notifications)
