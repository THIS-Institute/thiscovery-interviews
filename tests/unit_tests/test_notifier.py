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

import appointments as app
from common.constants import DEFAULT_TEMPLATES, INTERVIEWER_BOOKING_RESCHEDULING
from testing_utilities import AppointmentsTestCase
from thiscovery_lib import utilities as utils


class TestAppointmentNotifier(AppointmentsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        super().populate_calendars_table()
        cls.an = app.AppointmentNotifier(
            appointment=cls.aa1,
            logger=cls.logger,
            ddb_client=cls.aa1._ddb_client,
        )
        cls.an.appointment.appointment_type.ddb_load()
        cls.cancelled_aa = None
        cls.cancelled_an = None
        cls.past_aa = None
        cls.past_an = None


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

    @classmethod
    def load_past_appointment(cls):
        if cls.past_aa is None:
            cls.past_aa = app.AcuityAppointment(
                appointment_id=cls.test_data['past_test_appointment_id'],
                logger=cls.logger,
            )
        if cls.past_an is None:
            cls.past_an = app.AppointmentNotifier(
                appointment=cls.past_aa,
                logger=cls.logger,
            )


    def test_01_get_project_short_name_ok(self):
        self.an.appointment.appointment_type.project_task_id = self.test_data['project_task_id']
        result = self.an._get_project_short_name()
        self.assertEqual('PSFU-05-pub-act', result)

    def test_02_get_project_short_name_non_existent_project_task_id(self):
        self.an.appointment.appointment_type.project_task_id = '598699f3-7aef-4804-88d9-7f9cc68d87c1'
        with self.assertRaises(utils.ObjectDoesNotExistError):
            self.an._get_project_short_name()

    def test_03_get_email_template_ok(self):
        an = copy.copy(self.an)
        an.appointment.appointment_type.templates = DEFAULT_TEMPLATES
        an.appointment.appointment_type.has_link = True
        templates = [
            ('participant', 'booking', self.test_data['email'], "interview_booked_web_participant"),
            ('participant', 'booking', 'doctor@nhs.org', "interview_booked_web_nhs_participant"),
            ('participant', 'rescheduling', self.test_data['email'], "interview_rescheduled_web_participant"),
            ('participant', 'rescheduling', 'doctor@nhs.org', "interview_rescheduled_web_nhs_participant"),
            ('participant', 'cancellation', self.test_data['email'], "interview_cancelled_participant"),
            ('participant', 'cancellation', 'doctor@nhs.org', "interview_cancelled_participant"),
            ('researcher', 'booking', self.test_data['email'], "interview_booked_researcher"),
            ('researcher', 'rescheduling', self.test_data['email'], "interview_rescheduled_researcher"),
            ('researcher', 'cancellation', self.test_data['email'], "interview_cancelled_researcher"),
        ]
        for recipient, event, email, template_name in templates:
            an.participant_email = email
            self.logger.debug('Calling _get_email_template', extra={
                'recipient': recipient,
                'event': event,
                'email': email,
                'template_name': template_name,
            })
            result = an._get_email_template(
                recipient_email=email,
                recipient_type=recipient,
                event_type=event,
            )
            self.assertEqual(template_name, result['name'])

    def test_04_get_researcher_email_address_ok(self):
        result = self.an._get_researcher_email_address()
        self.assertEqual(2, len(result))
        self.assertIn("fred@email.co.uk", result)

    def test_05_check_appointment_cancelled_not_cancelled(self):
        self.assertFalse(self.an._check_appointment_cancelled())

    def test_06_check_appointment_cancelled_appointment_cancelled(self):
        self.load_cancelled_appointment()
        self.assertTrue(self.cancelled_an._check_appointment_cancelled())

    def test_07_send_notifications_aborted_if_appointment_cancelled(self):
        self.load_cancelled_appointment()
        result = self.cancelled_an.send_notifications(event_type='booking')
        expected_result = {'participant': 'aborted', 'researchers': ['aborted', 'aborted']}
        self.assertEqual(expected_result, result)

    def test_08_send_notifications_aborted_if_appointment_in_the_past(self):
        self.load_past_appointment()
        result = self.past_an.send_notifications(event_type='booking')
        expected_result = {'participant': 'aborted', 'researchers': ['aborted', 'aborted']}
        self.assertEqual(expected_result, result)

    def test_09_get_calendar_ddb_item_non_existent(self):
        an = copy.copy(self.an)
        an.appointment.calendar_id = '123456789'
        with self.assertRaises(utils.ObjectDoesNotExistError):
            an._get_calendar_ddb_item()

    def test_10_get_interviewer_myinterview_link_ok(self):
        result = self.an._get_interviewer_myinterview_link()
        self.assertEqual('https://meet.myinterview.com/5f64ccbd-b2e3-44e9-aed2-53c55cca4ef5', result)

    def test_11_get_anon_project_specific_user_id_ok(self):
        result = self.an._get_anon_project_specific_user_id()
        self.assertEqual('64cdc867-e53d-40c9-adda-f0271bcf1063', result)

    def test_12_get_anon_project_specific_user_id_user_not_found(self):
        ap = app.AcuityAppointment(
            appointment_id=self.test_data['test_appointment_id'],
        )
        an = app.AppointmentNotifier(
            appointment=ap
        )
        an.appointment.participant_email = 'bob@email.com'
        result = an._get_anon_project_specific_user_id()
        self.assertIsNone(result)

    def test_13_get_custom_properties_researcher_booking_ok(self):
        result = self.an._get_custom_properties(
            properties_list=INTERVIEWER_BOOKING_RESCHEDULING,
            template_type='researcher',
        )
        self.assertDictEqual(
            {
                'anon_project_specific_user_id': '64cdc867-e53d-40c9-adda-f0271bcf1063',
                'appointment_date': 'Monday 30 June 2025',
                'appointment_duration': '30 minutes',
                'appointment_time': '10:15',
                'appointment_type_name': 'Test appointment',
                'interviewer_first_name': 'André',
                'interviewer_url': 'https://meet.myinterview.com/5f64ccbd-b2e3-44e9-aed2-53c55cca4ef5',
                'project_short_name': 'PSFU-05-pub-act',
                'user_email': 'clive@email.co.uk',
                'user_first_name': 'Clive',
                'user_last_name': 'Cresswell'
            },
            result
        )