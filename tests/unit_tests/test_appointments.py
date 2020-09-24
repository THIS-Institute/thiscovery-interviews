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
import json

from http import HTTPStatus
from pprint import pprint

import src.appointments as app
import src.common.utilities as utils
import tests.testing_utilities as test_utils
from local.secrets import TESTER_THISCOVERY_USER_ID_MAP


class AppointmentsTestCase(test_utils.BaseTestCase):
    """
    Base class with data and methods for testing appointments.py
    """
    test_data = {
        'appointment_id': 399682887,
        'appointment_type_id': 14792299,  # test appointment
        'dev_appointment_type_id': 14649911,  # development appointment
        'calendar_name': 'André',
        'email': 'clive@email.co.uk',
        'project_task_id': '07af2fbe-5cd1-447f-bae1-3a2f8de82829',
        'status': 'active',
        'participant_user_id': '8518c7ed-1df4-45e9-8dc4-d49b57ae0663',
        'event_body': "action=appointment.scheduled&id=399682887&calendarID=4038206&appointmentTypeID=14792299",
        'cancelled_appointment_id': 446315771,
        'interview_url': "https://meet.myinterview.com/1b879c51-2e29-46ae-bd36-3199860e65f2"
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.aa = app.AcuityAppointment(
            appointment_id=cls.test_data['appointment_id'],
            logger=cls.logger,
            type_id=cls.test_data['appointment_type_id'],
        )
        cls.aa._ddb_client.put_item(
            table_name=cls.aa.appointment_type_table,
            key=str(cls.test_data['appointment_type_id']),
            item_type='acuity_appointment_type',
            item_details=None,
            item={
                'project_task_id': cls.test_data['project_task_id'],
                'status': cls.test_data['status'],
                'user_specific_interview_link': True,
                'send_notifications': True,
            },
            update_allowed=True,
        )
        cls.aa._ddb_client.put_item(
            table_name=cls.aa.appointment_type_table,
            key=str(cls.test_data['dev_appointment_type_id']),
            item_type='acuity_appointment_type',
            item_details=None,
            item={
                'project_task_id': cls.test_data['project_task_id'],
                'status': cls.test_data['status'],
                'user_specific_interview_link': False,
                'send_notifications': False,
            },
            update_allowed=True,
        )
        cls.clear_appointments_table()

    @classmethod
    def clear_appointments_table(cls):
        cls.aa._ddb_client.delete_all(
            table_name=app.APPOINTMENTS_TABLE,
        )


class SetInterviewUrlTestCase(AppointmentsTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.aa.ddb_dump()
        cls.aa._ddb_client.update_item(
            table_name=app.APPOINTMENTS_TABLE,
            key=cls.aa.appointment_id,
            name_value_pairs={
                'participant_user_id': TESTER_THISCOVERY_USER_ID_MAP[utils.get_environment_name()]  # so that participant notification go to tester
            }
        )

    def test_00_set_interview_url_api_ok(self):
        body = {
            "appointment_id": self.test_data['appointment_id'],
            "interview_url": self.test_data['interview_url'],
            "event_type": "booking",
        }
        result = test_utils.test_put(
            local_method=app.set_interview_url_api,
            aws_url='v1/set-interview-url',
            request_body=json.dumps(body),
        )
        self.assertEqual(HTTPStatus.OK, result['statusCode'])


class TestAcuityAppointment(AppointmentsTestCase):

    def test_01_get_appointment_type_id_to_name_map_ok(self):
        result = self.aa.get_appointment_type_id_to_name_map()
        self.assertEqual('Development appointment', result['14649911'])
        self.assertEqual('Test appointment', result['14792299'])

    def test_02_get_appointment_name_ok(self):
        result = self.aa.get_appointment_name()
        self.assertEqual('Test appointment', result)

    def test_03_get_appointment_details_ok(self):
        email, type_id = self.aa.get_appointment_info_from_acuity()
        self.assertEqual(self.test_data['email'], email)
        self.assertEqual(self.aa.type_id, type_id)
        self.assertEqual(self.test_data['calendar_name'], self.aa.calendar_name)

    def test_04_store_in_dynamodb_ok(self):
        result = self.aa.ddb_dump()
        self.assertEqual(HTTPStatus.OK, result['ResponseMetadata']['HTTPStatusCode'])
        self.clear_appointments_table()

    def test_05_update_link_ok(self):
        self.aa.ddb_dump()
        result = self.aa.update_link('www.thiscovery.org')
        self.assertEqual(HTTPStatus.OK, result['ResponseMetadata']['HTTPStatusCode'])
        self.clear_appointments_table()

    def test_06_get_appointment_item_from_ddb_ok(self):
        self.aa.ddb_dump()
        result = self.aa.get_appointment_item_from_ddb()
        self.assertEqual('acuity-appointment', result['type'])
        self.clear_appointments_table()

    def test_07_get_appointment_type_info_from_ddb_ok(self):
        project_task_id, type_status = self.aa.get_appointment_type_info_from_ddb()
        self.assertEqual(self.test_data['project_task_id'], project_task_id)
        self.assertEqual(self.test_data['status'], type_status)

    def test_08_get_participant_user_id_ok(self):
        result = self.aa.get_participant_user_id()
        self.assertEqual(self.test_data['participant_user_id'], result)


class TestAcuityEvent(AppointmentsTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ae = app.AcuityEvent(
            acuity_event=cls.test_data['event_body'],
            logger=cls.logger,
        )

    def test_08_init_ok(self):
        self.assertEqual('scheduled', self.ae.event_type)
        self.assertEqual('399682887', self.ae.appointment_id)
        self.assertEqual('4038206', self.ae.calendar_id)
        self.assertEqual('14792299', self.ae.type_id)
        self.assertEqual('active', self.ae.appointment.type_status)

    def test_09_notify_thiscovery_team_ok(self):
        result = self.ae.notify_thiscovery_team()
        self.assertEqual(HTTPStatus.OK, result['statusCode'])

    def test_10_process_ok(self):
        result = self.ae.process()
        pprint(result)


class TestAppointmentNotifier(AppointmentsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.an = app.AppointmentNotifier(
            appointment=cls.aa,
            logger=cls.logger,
            ddb_client=cls.aa._ddb_client,
        )
        cls.cancelled_aa = None
        cls.cancelled_an = None

    @classmethod
    def load_cancelled_appointment(cls):
        if cls.cancelled_aa is None:
            cls.cancelled_aa = app.AcuityAppointment(
                appointment_id=cls.test_data['cancelled_appointment_id'],
                logger=cls.logger,
            )
        if cls.cancelled_an is None:
            cls.cancelled_an = app.AppointmentNotifier(
                appointment=cls.cancelled_aa,
                logger=cls.logger,
            )

    def test_10_get_email_template_ok(self):
        templates = [
            ('participant', 'booking', self.test_data['email'], "interview_booked_participant"),
            ('participant', 'booking', 'doctor@nhs.org', "interview_booked_nhs_participant"),
            ('participant', 'rescheduling', self.test_data['email'], "interview_rescheduled_participant"),
            ('participant', 'rescheduling', 'doctor@nhs.org', "interview_rescheduled_nhs_participant"),
            ('participant', 'cancellation', self.test_data['email'], "interview_cancelled_participant"),
            ('participant', 'cancellation', 'doctor@nhs.org', "interview_cancelled_nhs_participant"),
            ('researcher', 'booking', self.test_data['email'], "interview_booked_researcher"),
            ('researcher', 'rescheduling', self.test_data['email'], "interview_rescheduled_researcher"),
            ('researcher', 'cancellation', self.test_data['email'], "interview_cancelled_researcher"),
        ]
        for recipient, event, email, template_name in templates:
            self.an.participant_email = email
            self.logger.debug('Calling _get_email_template', extra={
                'recipient': recipient,
                'event': event,
                'email': email,
                'template_name': template_name,
            })
            result = self.an._get_email_template(
                recipient_type=recipient,
                event_type=event,
            )
            self.assertEqual(template_name, result)

    def test_11_get_researcher_email_address_ok(self):
        result = self.an._get_researcher_email_address()
        self.assertEqual(2, len(result))
        self.assertIn("fred@email.co.uk", result)

    def test_12_check_appointment_cancelled_not_cancelled(self):
        self.assertFalse(self.an._check_appointment_cancelled())

    def test_13_check_appointment_cancelled_appointment_cancelled(self):
        self.load_cancelled_appointment()
        self.assertTrue(self.cancelled_an._check_appointment_cancelled())

    def test_14_send_researcher_booking_info_aborted_if_appointment_cancelled(self):
        self.load_cancelled_appointment()
        result = self.cancelled_an.send_researcher_booking_info()
        self.assertEqual('aborted', result)


