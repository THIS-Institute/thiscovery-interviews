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
import json
import unittest

from http import HTTPStatus
from pprint import pprint

import src.appointments as app
import common.utilities as utils
import tests.testing_utilities as test_utils
from src.common.constants import TEST_TEMPLATES, DEFAULT_TEMPLATES, INTERVIEWER_BOOKING_RESCHEDULING
from src.common.dynamodb_utilities import Dynamodb
from local.secrets import TESTER_EMAIL_MAP
from tests.test_data import td


class TestAcuityEventProcessing(test_utils.BaseTestCase):
    maxDiff = None
    """
    - no notifications created if appointment type has send_notifications == False
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.notifications_table = f"thiscovery-core-{utils.get_environment_name()}-notifications"
        cls.ddb_client = Dynamodb()
        cls.ddb_client.delete_all(table_name=cls.notifications_table, table_name_verbatim=True)
        cls.clear_appointments_table()

    @classmethod
    def clear_appointments_table(cls):
        cls.ddb_client.delete_all(
            table_name=app.APPOINTMENTS_TABLE,
        )

    def common_routine(self, appointment_id, calendar_id, appointment_type_id, expected_notifications):
        event_body = f"action=appointment.scheduled" \
                     f"&id={appointment_id}" \
                     f"&calendarID={calendar_id}" \
                     f"&appointmentTypeID={appointment_type_id}"

        result = test_utils.test_post(
            local_method=app.interview_appointment_api,
            aws_url='v1/interview-appointment',
            request_body=event_body
        )
        self.assertEqual(HTTPStatus.OK, result['statusCode'])

        # check notifications that were created in notifications table
        notifications = self.ddb_client.scan(
            table_name=self.notifications_table,
            table_name_verbatim=True,
        )
        self.assertEqual(3, len(notifications))
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
        self.assertCountEqual(expected_notifications, notifications)

    def test_01_process_booking_no_link_ok(self):
        expected_notifications = [
            {
                'details': {
                    'custom_properties': {
                        'anon_project_specific_user_id': '64cdc867-e53d-40c9-adda-f0271bcf1063',
                        'appointment_date': 'Friday 02 October '
                                            '2020 at 13:15',
                        'appointment_duration': '45 minutes',
                        'interviewer_url': 'Participant did not '
                                           'provide a phone '
                                           'number. Please contact '
                                           'them by email to '
                                           'obtain a contact '
                                           'number',
                        'project_short_name': 'PSFU-05-pub-act',
                        'user_email': 'clive@email.co.uk',
                        'user_first_name': 'Clive',
                        'user_last_name': 'Cresswell'
                    },
                    'template_name': 'non-existent',
                    'to_recipient_email': 'fred@email.co.uk'
                },
                'label': 'non-existent_fred@email.co.uk',
                'type': 'transactional-email'
            },
            {
                'details': {
                    'custom_properties': {
                        'anon_project_specific_user_id': '64cdc867-e53d-40c9-adda-f0271bcf1063',
                        'appointment_date': 'Friday 02 October '
                                            '2020 at 13:15',
                        'appointment_duration': '45 minutes',
                        'interviewer_url': 'Participant did not '
                                           'provide a phone '
                                           'number. Please contact '
                                           'them by email to '
                                           'obtain a contact '
                                           'number',
                        'project_short_name': 'PSFU-05-pub-act',
                        'user_email': 'clive@email.co.uk',
                        'user_first_name': 'Clive',
                        'user_last_name': 'Cresswell'
                    },
                    'template_name': 'non-existent',
                    'to_recipient_email': 'andre.sartori@thisinstitute.cam.ac.uk'
                },
                'label': 'non-existent_andre.sartori@thisinstitute.cam.ac.uk',
                'type': 'transactional-email'
            },
            {
                'details': {
                    'custom_properties': {
                        'appointment_date': 'Friday 02 October '
                                            '2020 at 13:15',
                        'appointment_duration': '45 minutes',
                        'appointment_reschedule_url': 'https://app.acuityscheduling.com/schedule.php?owner=19499339&action=appt&id%5B%5D=9edb5e9373f203a9398073e132eb0e7a',
                        'interview_url': 'We will call you on the '
                                         'phone number provided',
                        'project_short_name': 'PSFU-05-pub-act',
                        'user_first_name': 'Clive'
                    },
                    'template_name': 'non-existent',
                    'to_recipient_email': 'clive@email.co.uk'
                },
                'label': 'non-existent_clive@email.co.uk',
                'type': 'transactional-email'
            }]
        self.common_routine(
            appointment_id=td['dev_appointment_no_link_id'],
            calendar_id=td['calendar_id'],
            appointment_type_id=td['dev_appointment_no_link_type_id'],
            expected_notifications=expected_notifications
        )

    def test_02_process_booking_no_link_participant_not_in_thiscovery_database_ok(self):
        expected_notifications = [
            {
                'details': {
                    'custom_properties': {
                        'anon_project_specific_user_id': None,
                        'appointment_date': 'Thursday 01 October 2020 at 14:15',
                        'appointment_duration': '45 minutes',
                        'interviewer_url': 'Please call participant on 01234567890',
                        'project_short_name': 'PSFU-05-pub-act',
                        'user_email': 'greg@email.co.uk',
                        'user_first_name': 'Greg',
                        'user_last_name': 'Gregory',
                    },
                    'template_name': 'non-existent',
                    'to_recipient_email': 'fred@email.co.uk'
                },
                'label': 'non-existent_fred@email.co.uk',
                'type': 'transactional-email'
            },
            {
                'details': {
                    'custom_properties': {
                        'anon_project_specific_user_id': None,
                        'appointment_date': 'Thursday 01 October 2020 at 14:15',
                        'appointment_duration': '45 minutes',
                        'interviewer_url': 'Please call participant on 01234567890',
                        'project_short_name': 'PSFU-05-pub-act',
                        'user_email': 'greg@email.co.uk',
                        'user_first_name': 'Greg',
                        'user_last_name': 'Gregory',
                    },
                    'template_name': 'non-existent',
                    'to_recipient_email': 'andre.sartori@thisinstitute.cam.ac.uk'
                },
                'label': 'non-existent_andre.sartori@thisinstitute.cam.ac.uk',
                'type': 'transactional-email'
            },
            {
                'details': {
                    'custom_properties': {
                        'appointment_date': 'Thursday 01 October 2020 at 14:15',
                        'appointment_duration': '45 minutes',
                        'appointment_reschedule_url': 'https://app.acuityscheduling.com/schedule.php?owner=19499339&action=appt&id%5B%5D=2824c95d706bea4ec6604986b9358cd9',
                        'interview_url': 'We will call you on the phone number provided',
                        'project_short_name': 'PSFU-05-pub-act',
                        'user_first_name': 'Greg'
                    },
                    'template_name': 'non-existent',
                    'to_recipient_email': 'greg@email.co.uk'
                },
                'label': 'non-existent_greg@email.co.uk',
                'type': 'transactional-email'
            }]
        self.common_routine(
            appointment_id=td['dev_appointment_no_link_participant_not_in_thiscovery_database_id'],
            calendar_id=td['calendar_id'],
            appointment_type_id=td['dev_appointment_no_link_type_id'],
            expected_notifications=expected_notifications
        )
