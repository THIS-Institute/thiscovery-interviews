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
from src.common.constants import TEST_TEMPLATES
from local.secrets import TESTER_EMAIL_MAP


class AppointmentsTestCase(test_utils.BaseTestCase):
    """
    Base class with data and methods for testing appointments.py
    """
    test_data = {
        'test_appointment_id': 399682887,
        'dev_appointment_id': 448161724,
        'test_appointment_no_notif_id': 448161419,

        'test_appointment_type_id': 14792299,
        'dev_appointment_type_id': 14649911,
        'test_appointment_no_notif_type_id': 17268193,
        'dev_appointment_no_link_type_id': 17271544,

        'calendar_name': 'André',
        'email': 'clive@email.co.uk',
        'participant_user_id': '8518c7ed-1df4-45e9-8dc4-d49b57ae0663',
        'event_body': "action=appointment.scheduled&id=399682887&calendarID=4038206&appointmentTypeID=14792299",
        'cancelled_appointment_id': 446315771,
        'interview_url': "https://meet.myinterview.com/1b879c51-2e29-46ae-bd36-3199860e65f2",
        'project_task_id': '273b420e-09cb-419c-8b57-b393595dba78',
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.aa1 = app.AcuityAppointment(
            appointment_id=cls.test_data['test_appointment_id'],
            logger=cls.logger,
        )

        # test appointments default to have links and require notifications
        cls.at1 = app.AppointmentType(
            ddb_client=cls.aa1._ddb_client,
            acuity_client=cls.aa1._acuity_client,
            logger=cls.logger,
        )
        cls.at1.from_dict({
            'type_id': cls.test_data['test_appointment_type_id'],
            'has_link': True,
            'send_notifications': True,
            'templates': TEST_TEMPLATES,
            'project_task_id': cls.test_data['project_task_id'],
        })
        cls.at1.get_appointment_type_info_from_acuity()
        cls.at1.ddb_dump(update_allowed=True)

        # dev appointments default to not have links and not require notifications
        cls.at2 = app.AppointmentType(
            ddb_client=cls.aa1._ddb_client,
            acuity_client=cls.aa1._acuity_client,
            logger=cls.logger,
        )
        cls.at2.from_dict({
            'type_id': cls.test_data['dev_appointment_type_id'],
            'has_link': False,
            'send_notifications': False,
            'templates': TEST_TEMPLATES,
        })
        cls.at2.get_appointment_type_info_from_acuity()
        cls.at2.ddb_dump(update_allowed=True)

        cls.clear_appointments_table()

    @classmethod
    def clear_appointments_table(cls):
        cls.aa1._ddb_client.delete_all(
            table_name=app.APPOINTMENTS_TABLE,
        )

    @classmethod
    def populate_calendars_table(cls):
        calendar1 = {
            "block_monday_morning": True,
            "details": {
                "description": "",
                "email": "",
                "id": 4038206,
                "image": False,
                "location": "",
                "name": "André",
                "thumbnail": False,
                "timezone": "Europe/London"
            },
            "emails_to_notify": [
                TESTER_EMAIL_MAP[utils.get_environment_name()],
                "fred@email.co.uk"
            ],
            "id": "4038206",
            "label": "André",
        }
        calendar2 = copy.deepcopy(calendar1)
        calendar2['id'] = "3887437"
        calendar2['details']['id'] = 3887437
        for calendar in [calendar1, calendar2]:
            calendar_details = calendar['details']
            del calendar['details']
            try:
                cls.aa1._ddb_client.put_item(
                    table_name=app.AppointmentNotifier.calendar_table,
                    key=calendar['id'],
                    item_type="acuity-calendar",
                    item_details=calendar_details,
                    item=calendar
                )
            except utils.DetailedValueError:
                pass


class SetInterviewUrlTestCase(AppointmentsTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # test appointments - no notifications default to have links and not require notifications
        cls.at3 = app.AppointmentType(
            ddb_client=cls.aa1._ddb_client,
            acuity_client=cls.aa1._acuity_client,
            logger=cls.logger,
        )
        cls.at3.from_dict({
            'type_id': cls.test_data['test_appointment_no_notif_id'],
            'has_link': True,
            'send_notifications': False,
            'templates': TEST_TEMPLATES,
        })
        cls.at3.ddb_dump(update_allowed=True)

        # create test appointments
        cls.aa1.ddb_dump()
        cls.aa1._ddb_client.update_item(
            table_name=app.APPOINTMENTS_TABLE,
            key=cls.aa1.appointment_id,
            name_value_pairs={
                'participant_email': TESTER_EMAIL_MAP[utils.get_environment_name()]  # so that participant notification go to tester
            }
        )

        cls.aa2 = app.AcuityAppointment(
            appointment_id=cls.test_data['test_appointment_no_notif_id'],
            logger=cls.logger,
        )
        cls.aa2.ddb_dump()
        cls.aa2._ddb_client.update_item(
            table_name=app.APPOINTMENTS_TABLE,
            key=cls.aa2.appointment_id,
            name_value_pairs={
                'participant_email': TESTER_EMAIL_MAP[utils.get_environment_name()]  # so that participant notification go to tester
            }
        )

    def _common_routine(self, body):
        result = test_utils.test_put(
            local_method=app.set_interview_url_api,
            aws_url='v1/set-interview-url',
            request_body=json.dumps(body),
        )
        self.assertEqual(HTTPStatus.OK, result['statusCode'])
        result_body = json.loads(result['body'])
        self.assertEqual(HTTPStatus.OK, result_body['update_result'])

        # check link updated in Dynamodb
        updated_appointment = app.AcuityAppointment(appointment_id=body['appointment_id'])
        updated_appointment.ddb_load()
        return result, result_body

    def test_01_set_interview_url_api_ok_appointment_type_requires_notifications(self):
        body = {
            "appointment_id": self.test_data['test_appointment_id'],
            "interview_url": self.test_data['interview_url'],
            "event_type": "booking",
        }
        result, result_body = self._common_routine(body=body)
        notification_results = result_body['notification_results']
        self.assertEqual(HTTPStatus.NO_CONTENT, notification_results['participant'])
        self.assertEqual([HTTPStatus.NO_CONTENT] * 2, notification_results['researchers'])

    def test_02_set_interview_url_api_ok_appointment_type_does_not_require_notifications(self):
        body = {
            "appointment_id": self.test_data['test_appointment_no_notif_id'],
            "interview_url": self.test_data['interview_url'],
            "event_type": "booking",
        }
        result, result_body = self._common_routine(body=body)
        notification_results = result_body['notification_results']
        self.assertIsNone(notification_results['participant'])
        self.assertEqual(list(), notification_results['researchers'])


class TestAppointmentType(AppointmentsTestCase):

    @classmethod
    def setUpClass(cls):
        cls.at = app.AppointmentType()
        cls.at.type_id = str(cls.test_data['dev_appointment_type_id'])
        cls.at.templates = TEST_TEMPLATES

    def test_03_get_appointment_type_id_to_info_map_ok(self):
        result = self.at.get_appointment_type_id_to_info_map()
        app_type = result[self.at.type_id]
        expected_type = {
            'active': True,
            'addonIDs': [],
            'calendarIDs': [4038206, 3887437],
            'category': 'Tech development',
            'classSize': None,
            'color': '#AC53B4',
            'description': '',
            'duration': 30,
            'formIDs': [],
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

    def test_04_get_appointment_type_info_from_acuity_ok(self):
        at = copy.copy(self.at)
        at.get_appointment_type_info_from_acuity()
        self.assertEqual('Development appointment', at.name)
        self.assertEqual('Tech development', at.category)

    def test_05_ddb_dump_and_load_ok(self):
        at = copy.copy(self.at)
        at.get_appointment_type_info_from_acuity()
        dump_result = at.ddb_dump(update_allowed=True)
        self.assertEqual(HTTPStatus.OK, dump_result['ResponseMetadata']['HTTPStatusCode'])
        with self.assertRaises(AttributeError):
            at.type
        at.ddb_load()
        self.assertEqual('acuity-appointment-type', at.type)

    def test_06_as_dict_ok(self):
        at = copy.copy(self.at)
        at.get_appointment_type_info_from_acuity()
        expected_result = {
            'category': 'Tech development',
            'has_link': None,
            'name': 'Development appointment',
            'send_notifications': None,
            'templates': app.DEFAULT_TEMPLATES,
            'type_id': '14649911',
        }
        self.assertEqual(expected_result, at.as_dict())

    def test_07_from_dict_ok(self):
        at = copy.copy(self.at)
        at.get_appointment_type_info_from_acuity()
        at.from_dict(
            {
                'has_link': True,
                'templates': 'test_template'
            }
        )
        expected_result = {
            'category': 'Tech development',
            'has_link': True,
            'name': 'Development appointment',
            'send_notifications': None,
            'templates': 'test_template',
            'type_id': '14649911',
        }
        self.assertEqual(expected_result, at.as_dict())


class TestAcuityAppointment(AppointmentsTestCase):

    def test_08_get_appointment_details_ok(self):
        aa1 = copy.copy(self.aa1)
        result = aa1.get_appointment_info_from_acuity()
        self.assertEqual(self.test_data['email'], result['email'])
        self.assertEqual(self.test_data['email'], aa1.participant_email)
        self.assertEqual(self.test_data['calendar_name'], result['calendar'])

    def test_09_ddb_dump_and_load_ok(self):
        aa1 = copy.copy(self.aa1)
        dump_result = aa1.ddb_dump()
        self.assertEqual(HTTPStatus.OK, dump_result['ResponseMetadata']['HTTPStatusCode'])
        with self.assertRaises(AttributeError):
            aa1.type
        aa1.ddb_load()
        self.assertEqual('acuity-appointment', aa1.type)
        self.clear_appointments_table()

    def test_10_get_appointment_item_from_ddb_ok(self):
        aa1 = copy.copy(self.aa1)
        aa1.ddb_dump()
        result = aa1.get_appointment_item_from_ddb()
        self.assertEqual('acuity-appointment', result['type'])
        self.clear_appointments_table()

    def test_11_update_link_ok(self):
        aa1 = copy.copy(self.aa1)
        aa1.ddb_dump()
        test_link = 'www.thiscovery.org'
        result = aa1.update_link(test_link)
        self.assertEqual(HTTPStatus.OK, result)
        self.assertEqual(test_link, aa1.link)
        self.clear_appointments_table()

    def test_12_get_participant_user_id_ok(self):
        result = self.aa1.get_participant_user_id()
        self.assertEqual(self.test_data['participant_user_id'], result)

    def test_13_ddb_load_non_existent_appointment_id(self):
        non_existent_id = 'this-is-not-a-real-id'
        aa = app.AcuityAppointment(appointment_id=non_existent_id)
        with self.assertRaises(utils.ObjectDoesNotExistError) as context:
            aa.ddb_load()
        err = context.exception
        err_msg = err.args[0]
        self.assertEqual(f'Appointment {non_existent_id} could not be found in Dynamodb', err_msg)


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
            'templates': TEST_TEMPLATES,
        })
        cls.at4.get_appointment_type_info_from_acuity()
        cls.at4.ddb_dump(update_allowed=True)

        cls.ae = app.AcuityEvent(
            acuity_event=cls.test_data['event_body'],
            logger=cls.logger,
        )

    def test_14_init_ok(self):
        self.assertEqual('scheduled', self.ae.event_type)
        self.assertEqual('Test appointment', self.ae.appointment.appointment_type.name)

    def test_15_init_fail_non_existent_appointment_type_id(self):
        non_existent_id = '123456789'
        event_body = f"action=appointment.scheduled" \
                     f"&id=399682887&calendarID=4038206" \
                     f"&appointmentTypeID={non_existent_id}"
        with self.assertRaises(utils.ObjectDoesNotExistError):
            app.AcuityEvent(
                acuity_event=event_body,
                logger=self.logger,
            )

    def test_16_init_fail_invalid_appointment_type_id(self):
        invalid_id = 'invalid_id'
        event_body = f"action=appointment.scheduled" \
                     f"&id=399682887&calendarID=4038206" \
                     f"&appointmentTypeID={invalid_id}"
        with self.assertRaises(AttributeError):
            app.AcuityEvent(
                acuity_event=event_body,
                logger=self.logger,
            )

    def test_17_notify_thiscovery_team_ok(self):
        result = self.ae.notify_thiscovery_team()
        self.assertEqual(HTTPStatus.OK, result)

    def test_18_process_booking_has_link_ok(self):
        (
            storing_result,
            thiscovery_team_notification_result,
            participant_and_researchers_notification_results
        ) = self.ae.process()
        self.assertEqual(HTTPStatus.OK, storing_result['ResponseMetadata']['HTTPStatusCode'])
        self.assertEqual(HTTPStatus.OK, thiscovery_team_notification_result)
        self.assertIsNone(participant_and_researchers_notification_results)
        self.clear_appointments_table()

    def test_19_process_booking_no_link_no_notifications_ok(self):
        event_body = f"action=appointment.scheduled" \
                     f"&id=399682887&calendarID=4038206" \
                     f"&appointmentTypeID={self.test_data['dev_appointment_type_id']}"
        ae = app.AcuityEvent(acuity_event=event_body, logger=self.logger)
        (
            storing_result,
            thiscovery_team_notification_result,
            participant_and_researchers_notification_results
        ) = ae.process()
        self.assertEqual(HTTPStatus.OK, storing_result['ResponseMetadata']['HTTPStatusCode'])
        self.assertIsNone(thiscovery_team_notification_result)
        self.assertIsNone(participant_and_researchers_notification_results)
        self.clear_appointments_table()

    def test_20_process_booking_no_link_with_notifications_ok(self):
        event_body = f"action=appointment.scheduled" \
                     f"&id=399682887&calendarID=4038206" \
                     f"&appointmentTypeID={self.test_data['dev_appointment_no_link_type_id']}"
        ae = app.AcuityEvent(acuity_event=event_body, logger=self.logger)
        (
            storing_result,
            thiscovery_team_notification_result,
            participant_and_researchers_notification_results
        ) = ae.process()
        self.assertEqual(HTTPStatus.OK, storing_result['ResponseMetadata']['HTTPStatusCode'])
        self.assertIsNone(thiscovery_team_notification_result)
        participant_result = participant_and_researchers_notification_results.get('participant')
        self.assertEqual(HTTPStatus.NO_CONTENT, participant_result)
        researchers_result = participant_and_researchers_notification_results.get('researchers')
        self.assertEqual([HTTPStatus.NO_CONTENT]*2, researchers_result)
        self.clear_appointments_table()

    def test_21_process_cancellation_ok(self):
        event_body = f"action=appointment.canceled" \
                     f"&id=399682887&calendarID=4038206" \
                     f"&appointmentTypeID={self.test_data['test_appointment_type_id']}"
        ae = app.AcuityEvent(acuity_event=event_body, logger=self.logger)
        (
            storing_result,
            thiscovery_team_notification_result,
            participant_and_researchers_notification_results
        ) = ae.process()
        self.assertEqual(HTTPStatus.OK, storing_result['ResponseMetadata']['HTTPStatusCode'])
        self.assertIsNone(thiscovery_team_notification_result)
        participant_result = participant_and_researchers_notification_results.get('participant')
        self.assertEqual(HTTPStatus.NO_CONTENT, participant_result)
        researchers_result = participant_and_researchers_notification_results.get('researchers')
        self.assertEqual([HTTPStatus.NO_CONTENT] * 2, researchers_result)

    def test_22_process_rescheduling_same_calendar_ok(self):
        self.aa1.ddb_dump(update_allowed=True)  # store original appointment in ddb
        event_body = f"action=appointment.rescheduled" \
                     f"&id=399682887&calendarID=4038206" \
                     f"&appointmentTypeID={self.test_data['test_appointment_type_id']}"
        ae = app.AcuityEvent(acuity_event=event_body, logger=self.logger)
        (
            storing_result,
            thiscovery_team_notification_result,
            participant_and_researchers_notification_results
        ) = ae.process()
        self.assertEqual(HTTPStatus.OK, storing_result['ResponseMetadata']['HTTPStatusCode'])
        self.assertIsNone(thiscovery_team_notification_result)
        participant_result = participant_and_researchers_notification_results.get('participant')
        self.assertEqual(HTTPStatus.NO_CONTENT, participant_result)
        researchers_result = participant_and_researchers_notification_results.get('researchers')
        self.assertEqual([HTTPStatus.NO_CONTENT] * 2, researchers_result)

    @unittest.skip
    def test_23_process_rescheduling_different_calendar_ok(self):
        """
        Can't test this because process fetches latest info from Acuity rather than
        relying on the calendarID in event_body.
        """
        self.aa1.ddb_dump(update_allowed=True)  # store original appointment in ddb
        other_calendar = '3887437'
        event_body = f"action=appointment.rescheduled" \
                     f"&id=399682887&calendarID={other_calendar}" \
                     f"&appointmentTypeID={self.test_data['test_appointment_type_id']}"


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

    def test_24_get_project_short_name_ok(self):
        self.an.appointment.appointment_type.project_task_id = self.test_data['project_task_id']
        result = self.an._get_project_short_name()
        self.assertEqual('PSFU-05-pub-act', result)

    def test_25_get_project_short_name_non_existent_project_task_id(self):
        self.an.appointment.appointment_type.project_task_id = '598699f3-7aef-4804-88d9-7f9cc68d87c1'
        with self.assertRaises(utils.ObjectDoesNotExistError):
            self.an._get_project_short_name()

    def test_26_get_email_template_ok(self):
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
                recipient_email=email,
                recipient_type=recipient,
                event_type=event,
            )
            self.assertEqual(template_name, result['name'])

    def test_27_get_researcher_email_address_ok(self):
        result = self.an._get_researcher_email_address()
        self.assertEqual(2, len(result))
        self.assertIn("fred@email.co.uk", result)

    def test_28_check_appointment_cancelled_not_cancelled(self):
        self.assertFalse(self.an._check_appointment_cancelled())

    def test_29_check_appointment_cancelled_appointment_cancelled(self):
        self.load_cancelled_appointment()
        self.assertTrue(self.cancelled_an._check_appointment_cancelled())

    def test_30_send_notifications_aborted_if_appointment_cancelled(self):
        self.load_cancelled_appointment()
        result = self.cancelled_an.send_notifications(event_type='booking')
        expected_result = {'participant': 'aborted', 'researchers': ['aborted', 'aborted']}
        self.assertEqual(expected_result, result)
