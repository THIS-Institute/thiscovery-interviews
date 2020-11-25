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
import json
import os
import time

from http import HTTPStatus

import src.appointments as app
import tests.testing_utilities as test_utils
import thiscovery_dev_tools.testing_tools as test_tools
from local.secrets import TESTER_EMAIL_MAP
from tests.test_data import td


class TestAcuityEventProcessing(test_tools.BaseTestCase, test_utils.DdbMixin):
    maxDiff = None
    """
    - no notifications created if appointment type has send_notifications == False
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.set_notifications_table()
        cls.clear_appointments_table()

    def setUp(self):
        self.ddb_client.delete_all(table_name=self.notifications_table, table_name_verbatim=True)

    def common_routine(self, appointment_id, calendar_id, appointment_type_id, event_type='scheduled'):
        event_body = f"action=appointment.{event_type}" \
                     f"&id={appointment_id}" \
                     f"&calendarID={calendar_id}" \
                     f"&appointmentTypeID={appointment_type_id}"

        result = test_tools.test_post(
            local_method=app.interview_appointment_api,
            aws_url='v1/interview-appointment',
            request_body=event_body
        )
        self.assertEqual(HTTPStatus.OK, result['statusCode'])
        return result

    def common_routine_with_notifications(self, appointment_id, calendar_id, appointment_type_id,
                                          expected_notifications, event_type='scheduled'):
        self.common_routine(appointment_id, calendar_id, appointment_type_id, event_type=event_type)

        # check notifications that were created in notifications table
        notifications = self.ddb_client.scan(
            table_name=self.notifications_table,
            table_name_verbatim=True,
        )
        self.assertEqual(len(expected_notifications), len(notifications))
        attributes_to_ignore = [
            'created',
            'id',
            'modified',
            'processing_error_message',
            'processing_fail_count',
            'processing_status',
        ]
        # if running_on_aws, template names will not have NA_ appended to the beginning
        if os.environ['TEST_ON_AWS'] == 'True':
            for n in expected_notifications:
                n['label'] = n['label'].replace('NA_', '')
                n['details']['template_name'] = n['details']['template_name'].replace('NA_', '')

        for n in notifications:
            for a in attributes_to_ignore:
                del n[a]
        self.assertCountEqual(expected_notifications, notifications)

    def test_01_process_booking_no_link_ok(self):
        common_custom_properties = {
            'appointment_date': 'Thursday 02 October 2025',
            'appointment_duration': '45 minutes',
            'appointment_time': '13:15',
            'interviewer_first_name': 'André',
            'project_short_name': 'PSFU-05-pub-act',
            'user_first_name': 'Clive'
        }
        researcher_custom_properties = {
            **common_custom_properties,
            'anon_project_specific_user_id': '64cdc867-e53d-40c9-adda-f0271bcf1063',
            'appointment_type_name': 'Development appointment - no link',
            'interviewer_url': 'Participant did not provide a phone number. '
                               'Please contact them by email to obtain a contact number',
            'user_email': 'clive@email.co.uk',
            'user_last_name': 'Cresswell'
        }
        fred_notification = {
            'details': {
                'template_name': 'NA_interview_booked_researcher',
                'to_recipient_email': 'fred@email.co.uk',
                'custom_properties': researcher_custom_properties
            },
            'label': 'NA_interview_booked_researcher_fred@email.co.uk',
            'type': 'transactional-email',
        }
        tester_notification = {
            'details': {
                'template_name': 'NA_interview_booked_researcher',
                'to_recipient_email': TESTER_EMAIL_MAP[self.env_name],
                'custom_properties': researcher_custom_properties
            },
            'label': f'NA_interview_booked_researcher_{TESTER_EMAIL_MAP[self.env_name]}',
            'type': 'transactional-email',
        }
        participant_notification = {
            'details': {
                'custom_properties': {
                    **common_custom_properties,
                    'appointment_reschedule_url': 'https://app.acuityscheduling.com/schedule.php?owner=19499339&action=appt&id%5B%5D=9edb5e9373f203a9398073e132eb0e7a',
                    'interview_url': 'We will call you on the phone number provided',
                },
                'template_name': 'NA_interview_booked_web_participant',
                'to_recipient_email': 'clive@email.co.uk'
            },
            'label': 'NA_interview_booked_web_participant_clive@email.co.uk',
            'type': 'transactional-email'
        }
        expected_notifications = [
            fred_notification,
            tester_notification,
            participant_notification,
        ]
        self.common_routine_with_notifications(
            appointment_id=td['dev_appointment_no_link_id'],
            calendar_id=td['calendar_id'],
            appointment_type_id=td['dev_appointment_no_link_type_id'],
            expected_notifications=expected_notifications
        )

    def test_02_process_booking_no_link_participant_not_in_thiscovery_database_ok(self):
        common_custom_properties = {
            'appointment_date': 'Wednesday 01 October 2025',
            'appointment_duration': '45 minutes',
            'appointment_time': '14:15',
            'interviewer_first_name': 'André',
            'project_short_name': 'PSFU-05-pub-act',
            'user_first_name': 'Greg',
        }
        researcher_custom_properties = {
            **common_custom_properties,
            'anon_project_specific_user_id': None,
            'appointment_type_name': 'Development appointment - no link',
            'interviewer_url': 'Please call participant on 01234567890',
            'user_email': 'greg@email.co.uk',
            'user_last_name': 'Gregory',
        }
        fred_notification = {
            'details': {
                'template_name': 'NA_interview_booked_researcher',
                'to_recipient_email': 'fred@email.co.uk',
                'custom_properties': researcher_custom_properties
            },
            'label': 'NA_interview_booked_researcher_fred@email.co.uk',
            'type': 'transactional-email',
        }
        tester_notification = {
            'details': {
                'template_name': 'NA_interview_booked_researcher',
                'to_recipient_email': TESTER_EMAIL_MAP[self.env_name],
                'custom_properties': researcher_custom_properties
            },
            'label': f'NA_interview_booked_researcher_{TESTER_EMAIL_MAP[self.env_name]}',
            'type': 'transactional-email',
        }
        participant_notification = {
            'details': {
                'custom_properties': {
                    **common_custom_properties,
                    'appointment_reschedule_url': 'https://app.acuityscheduling.com/schedule.php?owner=19499339&action=appt&id%5B%5D=2824c95d706bea4ec6604986b9358cd9',
                    'interview_url': 'We will call you on the phone number provided',
                },
                'template_name': 'NA_interview_booked_web_participant',
                'to_recipient_email': 'greg@email.co.uk',
            },
            'label': 'NA_interview_booked_web_participant_greg@email.co.uk',
            'type': 'transactional-email'
        }
        expected_notifications = [
            fred_notification,
            tester_notification,
            participant_notification,
        ]
        self.common_routine_with_notifications(
            appointment_id=td['dev_appointment_no_link_participant_not_in_thiscovery_database_id'],
            calendar_id=td['calendar_id'],
            appointment_type_id=td['dev_appointment_no_link_type_id'],
            expected_notifications=expected_notifications
        )

    def test_03_process_booking_no_link_participant_does_not_have_user_project_ok(self):
        common_custom_properties = {
            'appointment_date': 'Wednesday 15 October 2025',
            'appointment_duration': '45 minutes',
            'appointment_time': '11:00',
            'interviewer_first_name': 'André',
            'project_short_name': 'PSFU-05-pub-act',
            'user_first_name': 'Eddie',
        }
        researcher_custom_properties = {
            **common_custom_properties,
            'anon_project_specific_user_id': None,
            'appointment_type_name': 'Development appointment - no link',
            'interviewer_url': 'Participant did not provide a phone number. Please contact them by email to obtain a contact number',
            'user_email': 'eddie@email.co.uk',
            'user_last_name': 'Eagleton',
        }
        fred_notification = {
            'details': {
                'template_name': 'NA_interview_booked_researcher',
                'to_recipient_email': 'fred@email.co.uk',
                'custom_properties': researcher_custom_properties
            },
            'label': 'NA_interview_booked_researcher_fred@email.co.uk',
            'type': 'transactional-email',
        }
        tester_notification = {
            'details': {
                'template_name': 'NA_interview_booked_researcher',
                'to_recipient_email': TESTER_EMAIL_MAP[self.env_name],
                'custom_properties': researcher_custom_properties
            },
            'label': f'NA_interview_booked_researcher_{TESTER_EMAIL_MAP[self.env_name]}',
            'type': 'transactional-email',
        }
        participant_notification = {
            'details': {
                'custom_properties': {
                    **common_custom_properties,
                    'appointment_reschedule_url': 'https://app.acuityscheduling.com/schedule.php?owner=19499339&action=appt&id%5B%5D=3b7422961f0ef184e484a94e04e237c9',
                    'interview_url': 'We will call you on the phone number provided',
                },
                'template_name': 'NA_interview_booked_web_participant',
                'to_recipient_email': 'eddie@email.co.uk',
            },
            'label': 'NA_interview_booked_web_participant_eddie@email.co.uk',
            'type': 'transactional-email'
        }
        expected_notifications = [
            fred_notification,
            tester_notification,
            participant_notification,
        ]
        self.common_routine_with_notifications(
            appointment_id=td['dev_appointment_no_link_participant_does_not_have_user_project'],
            calendar_id=td['calendar_id'],
            appointment_type_id=td['dev_appointment_no_link_type_id'],
            expected_notifications=expected_notifications
        )

    def test_04_process_booking_no_link_no_notifications_ok(self):
        result = self.common_routine(
            appointment_id=td['dev_appointment_id'],
            calendar_id=td['calendar_id'],
            appointment_type_id=td['dev_appointment_type_id'],
        )
        result_body = json.loads(result['body'])
        self.assertEqual(HTTPStatus.OK, result_body[0]['ResponseMetadata']['HTTPStatusCode'])
        self.assertIsNone(result_body[1])
        self.assertIsNone(result_body[2])
        # check no notifications were created in notifications table
        notifications = self.ddb_client.scan(
            table_name=self.notifications_table,
            table_name_verbatim=True,
        )
        self.assertEqual(0, len(notifications))

    def test_05_process_booking_with_link_ok(self):
        self.common_routine(
            appointment_id=td['test_appointment_id'],
            calendar_id=td['calendar_id'],
            appointment_type_id=td['test_appointment_type_id'],
        )
        input(
            f"You should now receive an email with subject line\n"
            f"'[thiscovery-interviews] Appointment 399682887 scheduled'\n"
            f"Please reply with the following text in the body of your email:\n\n"
            f"https://meet.myinterview.com/3c52b95f-4a31-454b-8e0a-69061f424ce5\n"
            f"env={self.env_name}\n\n"
            f"Once you have replied to that email, please enter 'y' to confirm:"
        )
        # check notifications
        common_custom_properties = {
            'appointment_date': 'Monday 30 June 2025',
            'appointment_duration': '30 minutes',
            'appointment_time': '10:15',
            'interviewer_first_name': 'André',
            'project_short_name': 'PSFU-05-pub-act',
            'user_first_name': 'Clive'
        }
        researcher_custom_properties = {
            **common_custom_properties,
            'anon_project_specific_user_id': '64cdc867-e53d-40c9-adda-f0271bcf1063',
            'appointment_type_name': 'Test appointment',
            "interviewer_url": "https://meet.myinterview.com/5f64ccbd-b2e3-44e9-aed2-53c55cca4ef5",
            'user_email': 'clive@email.co.uk',
            'user_last_name': 'Cresswell'
        }
        fred_notification = {
            'details': {
                'template_name': 'interview_booked_researcher',
                'to_recipient_email': 'fred@email.co.uk',
                'custom_properties': researcher_custom_properties
            },
            'label': 'interview_booked_researcher_fred@email.co.uk',
            'type': 'transactional-email',
        }
        tester_notification = {
            'details': {
                'template_name': 'interview_booked_researcher',
                'to_recipient_email': TESTER_EMAIL_MAP[self.env_name],
                'custom_properties': researcher_custom_properties
            },
            'label': f'interview_booked_researcher_{TESTER_EMAIL_MAP[self.env_name]}',
            'type': 'transactional-email',
        }
        participant_notification = {
            'details': {
                'custom_properties': {
                    **common_custom_properties,
                    'appointment_reschedule_url': 'https://app.acuityscheduling.com/schedule.php?owner=19499339&action=appt&id%5B%5D=9d20ba8fc7801ff9bc599861c72937ca',
                    "interview_url": "<a href=\"https://meet.myinterview.com/3c52b95f-4a31-454b-8e0a-69061f424ce5\" style=\"color:#dd0031\" rel=\"noopener\">https://meet.myinterview.com/3c52b95f-4a31-454b-8e0a-69061f424ce5</a>",
                },
                'template_name': 'interview_booked_web_participant',
                'to_recipient_email': 'clive@email.co.uk'
            },
            'label': 'interview_booked_web_participant_clive@email.co.uk',
            'type': 'transactional-email'
        }
        expected_notifications = [
            fred_notification,
            tester_notification,
            participant_notification,
        ]
        time.sleep(15)
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
                try:
                    del n[a]
                except KeyError:
                    pass
        self.assertCountEqual(expected_notifications, notifications)

    def test_06_process_rescheduling_same_calendar_no_link_ok(self):
        common_custom_properties = {
            'appointment_date': 'Thursday 02 October 2025',
            'appointment_duration': '45 minutes',
            'appointment_time': '13:15',
            'interviewer_first_name': 'André',
            'project_short_name': 'PSFU-05-pub-act',
            'user_first_name': 'Clive'
        }
        researcher_custom_properties = {
            **common_custom_properties,
            'anon_project_specific_user_id': '64cdc867-e53d-40c9-adda-f0271bcf1063',
            'appointment_type_name': 'Development appointment - no link',
            'interviewer_url': 'Participant did not provide a phone number. '
                               'Please contact them by email to obtain a contact number',
            'user_email': 'clive@email.co.uk',
            'user_last_name': 'Cresswell'
        }
        fred_notification = {
            'details': {
                'template_name': 'NA_interview_rescheduled_researcher',
                'to_recipient_email': 'fred@email.co.uk',
                'custom_properties': researcher_custom_properties
            },
            'label': 'NA_interview_rescheduled_researcher_fred@email.co.uk',
            'type': 'transactional-email',
        }
        tester_notification = {
            'details': {
                'template_name': 'NA_interview_rescheduled_researcher',
                'to_recipient_email': TESTER_EMAIL_MAP[self.env_name],
                'custom_properties': researcher_custom_properties
            },
            'label': f'NA_interview_rescheduled_researcher_{TESTER_EMAIL_MAP[self.env_name]}',
            'type': 'transactional-email',
        }
        participant_notification = {
            'details': {
                'custom_properties': {
                    **common_custom_properties,
                    'appointment_reschedule_url': 'https://app.acuityscheduling.com/schedule.php'
                                                  '?owner=19499339&action=appt&id%5B%5D=9edb5e9373f203a9398073e132eb0e7a',
                    'interview_url': 'We will call you on the phone number provided',
                },
                'template_name': 'NA_interview_rescheduled_web_participant',
                'to_recipient_email': 'clive@email.co.uk'
            },
            'label': 'NA_interview_rescheduled_web_participant_clive@email.co.uk',
            'type': 'transactional-email'
        }
        expected_notifications = [
            fred_notification,
            tester_notification,
            participant_notification,
        ]
        # create original booking
        self.common_routine(
            appointment_id=td['dev_appointment_no_link_id'],
            calendar_id=td['calendar_id'],
            appointment_type_id=td['dev_appointment_no_link_type_id'],
        )
        self.clear_notifications_table()

        # test rescheduling routine
        self.common_routine_with_notifications(
            appointment_id=td['dev_appointment_no_link_id'],
            calendar_id=td['calendar_id'],
            appointment_type_id=td['dev_appointment_no_link_type_id'],
            expected_notifications=expected_notifications,
            event_type='rescheduled'
        )

    def test_07_process_rescheduling_same_calendar_with_link_already_generated(self):
        # put original booking info in ddb
        original_booking_ddb_item = {
            "acuity_info": {
                "addonIDs": [],
                "amountPaid": "0.00",
                "appointmentTypeID": 14792299,
                "calendar": "André",
                "calendarID": 4038206,
                "calendarTimezone": "Europe/London",
                "canceled": False,
                "canClientCancel": True,
                "canClientReschedule": True,
                "category": "_Tech development",
                "certificate": None,
                "classID": None,
                "confirmationPage": "https://app.acuityscheduling.com/schedule.php?owner=19499339&action=appt&id%5B%5D=9d20ba8fc7801ff9bc599861c72937ca",
                "date": "June 30, 2025",
                "dateCreated": "June 29, 2020",
                "datetime": "2025-06-30T10:15:00+0100",
                "datetimeCreated": "2020-06-29T16:45:48-0500",
                "duration": "30",
                "email": "clive@email.co.uk",
                "endTime": "10:45",
                "firstName": "Clive",
                "forms": [],
                "formsText": "Name: Clive Cresswell\nPhone: \nEmail: clive@email.co.uk\n",
                "id": 399682887,
                "isVerified": False,
                "labels": None,
                "lastName": "Cresswell",
                "location": "",
                "notes": "DO NOT DELETE. Appointment used for automated testing.",
                "paid": "no",
                "phone": "",
                "price": "0.00",
                "priceSold": "0.00",
                "scheduledBy": "REDACTED",
                "time": "10:15",
                "timezone": "Europe/London",
                "type": "Test appointment"
            },
            "appointment_date": "2025-06-30",
            "appointment_id": "399682887",
            "appointment_type": {
                "category": "Tech development",
                "details": None,
                "has_link": True,
                "id": "14792299",
                "name": "Test appointment",
                "project_task_id": "273b420e-09cb-419c-8b57-b393595dba78",
                "send_notifications": True,
                "templates": None,
                "type": "acuity-appointment-type",
                "type_id": "14792299"
            },
            "calendar_id": "4038206",
            "calendar_name": "André",
            "created": "2020-11-25 23:21:23.862092+00:00",
            # "details": None,
            # "id": "399682887",
            "latest_participant_notification": "2020-11-25 23:23:39.899191+00:00",
            "link": "https://meet.myinterview.com/3c52b95f-4a31-454b-8e0a-69061f424ce5",
            "modified": "2020-11-25 23:23:39.901344+00:00",
            "participant_email": "clive@email.co.uk",
            "participant_user_id": None,
            # "type": "acuity-appointment"
        }
        self.ddb_client.put_item(
            table_name=app.APPOINTMENTS_TABLE,
            key="399682887",
            item_type="acuity-appointment",
            item_details=None,
            item=original_booking_ddb_item
        )

        common_custom_properties = {
            'appointment_date': 'Monday 30 June 2025',
            'appointment_duration': '30 minutes',
            'appointment_time': '10:15',
            'interviewer_first_name': 'André',
            'project_short_name': 'PSFU-05-pub-act',
            'user_first_name': 'Clive'
        }
        researcher_custom_properties = {
            **common_custom_properties,
            'anon_project_specific_user_id': '64cdc867-e53d-40c9-adda-f0271bcf1063',
            'appointment_type_name': 'Test appointment',
            "interviewer_url": "https://meet.myinterview.com/5f64ccbd-b2e3-44e9-aed2-53c55cca4ef5",
            'user_email': 'clive@email.co.uk',
            'user_last_name': 'Cresswell'
        }
        fred_notification = {
            'details': {
                'template_name': 'NA_interview_rescheduled_researcher',
                'to_recipient_email': 'fred@email.co.uk',
                'custom_properties': researcher_custom_properties
            },
            'label': 'NA_interview_rescheduled_researcher_fred@email.co.uk',
            'type': 'transactional-email',
        }
        tester_notification = {
            'details': {
                'template_name': 'NA_interview_rescheduled_researcher',
                'to_recipient_email': TESTER_EMAIL_MAP[self.env_name],
                'custom_properties': researcher_custom_properties
            },
            'label': f'NA_interview_rescheduled_researcher_{TESTER_EMAIL_MAP[self.env_name]}',
            'type': 'transactional-email',
        }
        participant_notification = {
            'details': {
                'custom_properties': {
                    **common_custom_properties,
                    'appointment_reschedule_url': 'https://app.acuityscheduling.com/schedule.php?owner=19499339&action=appt&id%5B%5D=9d20ba8fc7801ff9bc599861c72937ca',
                    "interview_url": "<a href=\"https://meet.myinterview.com/3c52b95f-4a31-454b-8e0a-69061f424ce5\" style=\"color:#dd0031\" rel=\"noopener\">https://meet.myinterview.com/3c52b95f-4a31-454b-8e0a-69061f424ce5</a>",
                },
                'template_name': 'NA_interview_rescheduled_web_participant',
                'to_recipient_email': 'clive@email.co.uk'
            },
            'label': 'NA_interview_rescheduled_web_participant_clive@email.co.uk',
            'type': 'transactional-email'
        }
        expected_notifications = [
            fred_notification,
            tester_notification,
            participant_notification,
        ]
        self.common_routine_with_notifications(
            appointment_id=td['test_appointment_id'],
            calendar_id=td['calendar_id'],
            appointment_type_id=td['test_appointment_type_id'],
            expected_notifications=expected_notifications,
            event_type='rescheduled',
        )

    def test_08_process_rescheduling_same_calendar_with_link_not_generated_yet(self):
        # put original booking info in ddb
        original_booking_ddb_item = {
            "acuity_info": {
                "addonIDs": [],
                "amountPaid": "0.00",
                "appointmentTypeID": 14792299,
                "calendar": "André",
                "calendarID": 4038206,
                "calendarTimezone": "Europe/London",
                "canceled": False,
                "canClientCancel": True,
                "canClientReschedule": True,
                "category": "_Tech development",
                "certificate": None,
                "classID": None,
                "confirmationPage": "https://app.acuityscheduling.com/schedule.php?owner=19499339&action=appt&id%5B%5D=9d20ba8fc7801ff9bc599861c72937ca",
                "date": "June 30, 2025",
                "dateCreated": "June 29, 2020",
                "datetime": "2025-06-30T10:15:00+0100",
                "datetimeCreated": "2020-06-29T16:45:48-0500",
                "duration": "30",
                "email": "clive@email.co.uk",
                "endTime": "10:45",
                "firstName": "Clive",
                "forms": [],
                "formsText": "Name: Clive Cresswell\nPhone: \nEmail: clive@email.co.uk\n",
                "id": 399682887,
                "isVerified": False,
                "labels": None,
                "lastName": "Cresswell",
                "location": "",
                "notes": "DO NOT DELETE. Appointment used for automated testing.",
                "paid": "no",
                "phone": "",
                "price": "0.00",
                "priceSold": "0.00",
                "scheduledBy": "REDACTED",
                "time": "10:15",
                "timezone": "Europe/London",
                "type": "Test appointment"
            },
            "appointment_date": "2025-06-30",
            "appointment_id": "399682887",
            "appointment_type": {
                "category": "Tech development",
                "details": None,
                "has_link": True,
                "id": "14792299",
                "name": "Test appointment",
                "project_task_id": "273b420e-09cb-419c-8b57-b393595dba78",
                "send_notifications": True,
                "templates": None,
                "type": "acuity-appointment-type",
                "type_id": "14792299"
            },
            "calendar_id": "4038206",
            "calendar_name": "André",
            "created": "2020-11-25 23:21:23.862092+00:00",
            # "details": None,
            # "id": "399682887",
            "latest_participant_notification": "2020-11-25 23:23:39.899191+00:00",
            "link": None,
            "modified": "2020-11-25 23:23:39.901344+00:00",
            "participant_email": "clive@email.co.uk",
            "participant_user_id": None,
            # "type": "acuity-appointment"
        }
        self.ddb_client.put_item(
            table_name=app.APPOINTMENTS_TABLE,
            key="399682887",
            item_type="acuity-appointment",
            item_details=None,
            item=original_booking_ddb_item
        )

        self.common_routine_with_notifications(
            appointment_id=td['test_appointment_id'],
            calendar_id=td['calendar_id'],
            appointment_type_id=td['test_appointment_type_id'],
            expected_notifications=list(),
            event_type='rescheduled',
        )

    def test_quick(self):
        a = {'label': 'NA_interview_rescheduled_researcher_fred@email.co.uk',
             'details': {'template_name': 'NA_interview_rescheduled_researcher', 'to_recipient_email': 'fred@email.co.uk',
                         'custom_properties': {'appointment_time': '10:15',
                                               'interviewer_url': 'https://meet.myinterview.com/5f64ccbd-b2e3-44e9-aed2-53c55cca4ef5',
                                               'user_first_name': 'Clive', 'user_email': 'clive@email.co.uk', 'appointment_duration': '30 minutes',
                                               'user_last_name': 'Cresswell', 'appointment_date': 'Monday 30 June 2025',
                                               'anon_project_specific_user_id': '64cdc867-e53d-40c9-adda-f0271bcf1063', 'project_short_name': 'PSFU-05-pub-act',
                                               'appointment_type_name': 'Test appointment', 'interviewer_first_name': 'André'}}, 'type': 'transactional-email'}
        e = {'details': {'template_name': 'interview_rescheduled_researcher', 'to_recipient_email': 'fred@email.co.uk', 'custom_properties': {'appointment_date': 'Monday 30 June 2025', 'appointment_duration': '30 minutes', 'appointment_time': '10:15', 'interviewer_first_name': 'André', 'project_short_name': 'PSFU-05-pub-act', 'user_first_name': 'Clive', 'anon_project_specific_user_id': '64cdc867-e53d-40c9-adda-f0271bcf1063', 'appointment_type_name': 'Test appointment', 'interviewer_url': 'https://meet.myinterview.com/5f64ccbd-b2e3-44e9-aed2-53c55cca4ef5', 'user_email': 'clive@email.co.uk', 'user_last_name': 'Cresswell'}}, 'label': 'interview_rescheduled_researcher_fred@email.co.uk', 'type': 'transactional-email'}
        self.assertDictEqual(e, a)

        a = {'label': 'NA_interview_rescheduled_researcher_andre.sartori@thisinstitute.cam.ac.uk', 'details': {'template_name': 'NA_interview_rescheduled_researcher', 'to_recipient_email': 'andre.sartori@thisinstitute.cam.ac.uk', 'custom_properties': {'appointment_time': '10:15', 'interviewer_url': 'https://meet.myinterview.com/5f64ccbd-b2e3-44e9-aed2-53c55cca4ef5', 'user_first_name': 'Clive', 'user_email': 'clive@email.co.uk', 'appointment_duration': '30 minutes', 'user_last_name': 'Cresswell', 'appointment_date': 'Monday 30 June 2025', 'anon_project_specific_user_id': '64cdc867-e53d-40c9-adda-f0271bcf1063', 'project_short_name': 'PSFU-05-pub-act', 'appointment_type_name': 'Test appointment', 'interviewer_first_name': 'André'}}, 'type': 'transactional-email'}
        e = {'details': {'template_name': 'interview_rescheduled_researcher', 'to_recipient_email': 'andre.sartori@thisinstitute.cam.ac.uk', 'custom_properties': {'appointment_date': 'Monday 30 June 2025', 'appointment_duration': '30 minutes', 'appointment_time': '10:15', 'interviewer_first_name': 'André', 'project_short_name': 'PSFU-05-pub-act', 'user_first_name': 'Clive', 'anon_project_specific_user_id': '64cdc867-e53d-40c9-adda-f0271bcf1063', 'appointment_type_name': 'Test appointment', 'interviewer_url': 'https://meet.myinterview.com/5f64ccbd-b2e3-44e9-aed2-53c55cca4ef5', 'user_email': 'clive@email.co.uk', 'user_last_name': 'Cresswell'}}, 'label': 'interview_rescheduled_researcher_andre.sartori@thisinstitute.cam.ac.uk', 'type': 'transactional-email'}
        self.assertDictEqual(e, a)

        a = {'label': 'NA_interview_rescheduled_web_participant_clive@email.co.uk', 'details': {'template_name': 'NA_interview_rescheduled_web_participant', 'to_recipient_email': 'clive@email.co.uk', 'custom_properties': {'user_first_name': 'Clive', 'appointment_time': '10:15', 'interview_url': '<a href="https://meet.myinterview.com/3c52b95f-4a31-454b-8e0a-69061f424ce5" style="color:#dd0031" rel="noopener">https://meet.myinterview.com/3c52b95f-4a31-454b-8e0a-69061f424ce5</a>', 'appointment_duration': '30 minutes', 'appointment_reschedule_url': 'https://app.acuityscheduling.com/schedule.php?owner=19499339&action=appt&id%5B%5D=9d20ba8fc7801ff9bc599861c72937ca', 'appointment_date': 'Monday 30 June 2025', 'project_short_name': 'PSFU-05-pub-act', 'interviewer_first_name': 'André'}}, 'type': 'transactional-email'}
        e = {'details': {'custom_properties': {'appointment_date': 'Monday 30 June 2025', 'appointment_duration': '30 minutes', 'appointment_time': '10:15', 'interviewer_first_name': 'André', 'project_short_name': 'PSFU-05-pub-act', 'user_first_name': 'Clive', 'appointment_reschedule_url': 'https://app.acuityscheduling.com/schedule.php?owner=19499339&action=appt&id%5B%5D=9d20ba8fc7801ff9bc599861c72937ca', 'interview_url': '<a href="https://meet.myinterview.com/3c52b95f-4a31-454b-8e0a-69061f424ce5" style="color:#dd0031" rel="noopener">https://meet.myinterview.com/3c52b95f-4a31-454b-8e0a-69061f424ce5</a>'}, 'template_name': 'interview_rescheduled_web_participant', 'to_recipient_email': 'clive@email.co.uk'}, 'label': 'interview_rescheduled_web_participant_clive@email.co.uk', 'type': 'transactional-email'}
        self.assertDictEqual(e, a)