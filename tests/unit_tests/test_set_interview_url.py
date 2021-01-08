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
from http import HTTPStatus

import appointments as app
from testing_utilities import AppointmentsTestCase
from thiscovery_dev_tools import testing_tools as test_utils
from thiscovery_lib import utilities as utils

from local.secrets import TESTER_EMAIL_MAP


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
            'project_task_id': cls.test_data['project_task_id'],
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