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
import testing_utilities as test_utils  # this should be the first import; it sets env variables
import json
import os
from thiscovery_dev_tools.testing_tools import TestApiEndpoints, TestSecurityOfEndpointsDefinedInTemplateYaml

from test_data import td

class TestInterviewApiEndpoints(TestApiEndpoints):

    def test_01_get_appointments_by_type_requires_valid_key(self):
        body = json.dumps({'type_ids': [td['test_appointment_type_id']]})
        self.check_api_is_restricted(
            request_verb='GET',
            aws_url='/v1/appointments-by-type',
            request_body=body,
        )

    def test_02_set_interview_url_requires_valid_key(self):
        body = json.dumps({
            "appointment_id": td['test_appointment_id'],
            "interview_url": td['interview_url'],
            "event_type": "booking",
        })
        self.check_api_is_restricted(
            request_verb='PUT',
            aws_url='/v1/set-interview-url',
            request_body=body,
        )

    def test_03_interview_appointment_endpoint_is_public(self):
        body = f"action=appointment.scheduled" \
               f"&id=399682887&calendarID=4038206" \
               f"&appointmentTypeID=invalid_id"
        self.check_api_is_public(
            request_verb='POST',
            aws_url='/v1/interview-appointment',
            expected_status=HTTPStatus.INTERNAL_SERVER_ERROR,
            request_body=body,
        )


class TestTemplate(TestSecurityOfEndpointsDefinedInTemplateYaml):
    public_endpoints = [
        ('/v1/interview-appointment', 'post'),
    ]

    @classmethod
    def setUpClass(cls):
        super().setUpClass(
            template_file_path=os.path.join(test_utils.BASE_FOLDER, 'template.yaml'),
            api_resource_name='InterviewsApi',
        )

    def test_04_defined_endpoints_are_secure(self):
        self.check_defined_endpoints_are_secure()
