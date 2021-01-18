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
import local.dev_config  # sets environment variables
import local.secrets  # sets environment variables
import json
import thiscovery_dev_tools.testing_tools as test_utils
from http import HTTPStatus
from pprint import pprint

import app_by_type as abt
from local.dev_config import DELETE_TEST_DATA
from test_data import td
from testing_utilities import DdbMixin


class TestAppByType(test_utils.BaseTestCase, DdbMixin):
    endpoint_url = 'v1/appointments-by-type'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        super().populate_appointments_table()

    @classmethod
    def tearDownClass(cls):
        if DELETE_TEST_DATA is True:
            super().clear_appointments_table()
        super().tearDownClass()

    def test_01_get_appointment_by_type_api_ok(self):
        body = json.dumps({
            'type_ids': [
                str(td['dev_appointment_no_link_type_id'])
            ]
        })

        result = test_utils.test_get(
            local_method=abt.get_appointments_by_type_api,
            aws_url=self.endpoint_url,
            request_body=body
        )
        self.assertEqual(HTTPStatus.OK, result['statusCode'])
        appointments = json.loads(result['body'])['appointments']
        self.assertEqual(3, len(appointments))
