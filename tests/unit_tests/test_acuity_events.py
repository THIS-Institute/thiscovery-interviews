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
import unittest
from http import HTTPStatus

import appointments as app
from test_data import td
from testing_utilities import AppointmentsTestCase
from thiscovery_lib import utilities as utils


class TestAcuityEvent(AppointmentsTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # dev appointments - no link default to not have links and require notifications (e.g. phone appointment)
        cls.at4 = app.AppointmentType(
            ddb_client=cls.aa1._ddb_client,
            acuity_client=cls.aa1._acuity_client,
            logger=cls.logger,
        )
        cls.at4.from_dict({
            'type_id': cls.test_data['dev_appointment_no_link_type_id'],
            'has_link': False,
            'send_notifications': True,
            'project_task_id': cls.test_data['project_task_id'],
        })
        cls.at4.get_appointment_type_info_from_acuity()
        cls.at4.ddb_dump(update_allowed=True)

        cls.ae = app.AcuityEvent(
            acuity_event=cls.test_data['event_body'],
            logger=cls.logger,
        )

    def test_01_init_ok(self):
        self.assertEqual('scheduled', self.ae.event_type)
        self.assertEqual('Test appointment', self.ae.appointment.appointment_type.name)

    def test_02_init_fail_non_existent_appointment_type_id(self):
        non_existent_id = '123456789'
        event_body = f"action=appointment.scheduled" \
                     f"&id=399682887&calendarID=4038206" \
                     f"&appointmentTypeID={non_existent_id}"
        with self.assertRaises(utils.ObjectDoesNotExistError):
            app.AcuityEvent(
                acuity_event=event_body,
                logger=self.logger,
            )

    def test_03_init_fail_invalid_appointment_type_id(self):
        invalid_id = 'invalid_id'
        event_body = f"action=appointment.scheduled" \
                     f"&id=399682887&calendarID=4038206" \
                     f"&appointmentTypeID={invalid_id}"
        with self.assertRaises(AttributeError):
            app.AcuityEvent(
                acuity_event=event_body,
                logger=self.logger,
            )

    def test_04_notify_thiscovery_team_ok(self):
        result = self.ae.notify_thiscovery_team()
        self.assertEqual(HTTPStatus.OK, result)

    def test_05_notify_thiscovery_team_aborted_past_appointment(self):
        ae = app.AcuityEvent(
            acuity_event=self.test_data['past_appointment_event_body'],
            logger=self.logger,
        )
        result = ae.notify_thiscovery_team()
        self.assertEqual('aborted', result)

    def test_06_process_booking_has_link_ok(self):
        (
            storing_result,
            task_completion_result,
            thiscovery_team_notification_result,
            participant_and_researchers_notification_results
        ) = self.ae.process()
        self.assertEqual(HTTPStatus.OK, storing_result['ResponseMetadata']['HTTPStatusCode'])
        self.assertIsNone(task_completion_result)
        self.assertEqual(HTTPStatus.OK, thiscovery_team_notification_result)
        self.assertIsNone(participant_and_researchers_notification_results)
        self.clear_appointments_table()

    def test_07_process_booking_no_link_no_notifications_ok(self):
        event_body = f"action=appointment.scheduled" \
                     f"&id=399682887&calendarID=4038206" \
                     f"&appointmentTypeID={self.test_data['dev_appointment_type_id']}"
        ae = app.AcuityEvent(acuity_event=event_body, logger=self.logger)
        (
            storing_result,
            task_completion_result,
            thiscovery_team_notification_result,
            participant_and_researchers_notification_results
        ) = ae.process()
        self.assertEqual(HTTPStatus.OK, storing_result['ResponseMetadata']['HTTPStatusCode'])
        self.assertIsNone(task_completion_result)
        self.assertIsNone(thiscovery_team_notification_result)
        self.assertIsNone(participant_and_researchers_notification_results)
        self.clear_appointments_table()

    def test_08_process_booking_no_link_with_notifications_ok(self):
        event_body = f"action=appointment.scheduled" \
                     f"&id=399682887&calendarID=4038206" \
                     f"&appointmentTypeID={self.test_data['dev_appointment_no_link_type_id']}"
        ae = app.AcuityEvent(acuity_event=event_body, logger=self.logger)
        (
            storing_result,
            task_completion_result,
            thiscovery_team_notification_result,
            participant_and_researchers_notification_results
        ) = ae.process()
        self.assertEqual(HTTPStatus.OK, storing_result['ResponseMetadata']['HTTPStatusCode'])
        self.assertIsNone(task_completion_result)
        self.assertIsNone(thiscovery_team_notification_result)
        participant_result = participant_and_researchers_notification_results.get('participant')
        self.assertEqual(HTTPStatus.NO_CONTENT, participant_result)
        researchers_result = participant_and_researchers_notification_results.get('researchers')
        self.assertEqual([HTTPStatus.NO_CONTENT]*2, researchers_result)
        self.clear_appointments_table()

    def test_09_process_cancellation_ok(self):
        self.aa1.ddb_dump()  # simulates original booking
        event_body = f"action=appointment.canceled" \
                     f"&id={self.test_data['test_appointment_id']}&calendarID=4038206" \
                     f"&appointmentTypeID={self.test_data['test_appointment_type_id']}"
        ae = app.AcuityEvent(acuity_event=event_body, logger=self.logger)
        (
            storing_result,
            task_completion_result,
            thiscovery_team_notification_result,
            participant_and_researchers_notification_results
        ) = ae.process()
        self.assertEqual(HTTPStatus.OK, storing_result['ResponseMetadata']['HTTPStatusCode'])
        self.assertIsNone(task_completion_result)
        self.assertIsNone(thiscovery_team_notification_result)
        participant_result = participant_and_researchers_notification_results.get('participant')
        self.assertEqual(HTTPStatus.NO_CONTENT, participant_result)
        researchers_result = participant_and_researchers_notification_results.get('researchers')
        self.assertEqual([HTTPStatus.NO_CONTENT] * 2, researchers_result)
        self.clear_appointments_table()

    def test_10_process_rescheduling_same_calendar_ok_link_already_generated(self):
        original_appointment = copy.copy(self.aa1)
        original_appointment.link = td['interview_url']
        original_appointment.ddb_dump(update_allowed=True)  # store original appointment in ddb
        event_body = f"action=appointment.rescheduled" \
                     f"&id=399682887&calendarID=4038206" \
                     f"&appointmentTypeID={self.test_data['test_appointment_type_id']}"
        ae = app.AcuityEvent(acuity_event=event_body, logger=self.logger)
        (
            storing_result,
            task_completion_result,
            thiscovery_team_notification_result,
            participant_and_researchers_notification_results
        ) = ae.process()
        self.assertEqual(HTTPStatus.OK, storing_result['ResponseMetadata']['HTTPStatusCode'])
        self.assertIsNone(task_completion_result)
        self.assertIsNone(thiscovery_team_notification_result)
        participant_result = participant_and_researchers_notification_results.get('participant')
        self.assertEqual(HTTPStatus.NO_CONTENT, participant_result)
        researchers_result = participant_and_researchers_notification_results.get('researchers')
        self.assertEqual([HTTPStatus.NO_CONTENT] * 2, researchers_result)

    def test_11_process_rescheduling_same_calendar_ok_link_not_generated_yet(self):
        self.aa1.ddb_dump(update_allowed=True)  # store original appointment in ddb
        event_body = f"action=appointment.rescheduled" \
                     f"&id=399682887&calendarID=4038206" \
                     f"&appointmentTypeID={self.test_data['test_appointment_type_id']}"
        ae = app.AcuityEvent(acuity_event=event_body, logger=self.logger)
        (
            storing_result,
            task_completion_result,
            thiscovery_team_notification_result,
            participant_and_researchers_notification_results
        ) = ae.process()
        self.assertEqual(HTTPStatus.OK, storing_result['ResponseMetadata']['HTTPStatusCode'])
        self.assertIsNone(task_completion_result)
        self.assertIsNone(thiscovery_team_notification_result)
        self.assertIsNone(participant_and_researchers_notification_results)

    @unittest.skip
    def test_12_process_rescheduling_different_calendar_ok(self):
        """
        Can't test this because process fetches latest info from Acuity rather than
        relying on the calendarID in event_body.
        """
        self.aa1.ddb_dump(update_allowed=True)  # store original appointment in ddb
        other_calendar = '3887437'
        event_body = f"action=appointment.rescheduled" \
                     f"&id=399682887&calendarID={other_calendar}" \
                     f"&appointmentTypeID={self.test_data['test_appointment_type_id']}"