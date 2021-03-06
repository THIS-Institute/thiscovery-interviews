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
import os
import time
import unittest

from dateutil import parser
from http import HTTPStatus
from pprint import pprint

import src.appointments as app
import src.clean as clean
import src.reminders as rem

import thiscovery_lib.utilities as utils
import tests.test_data as test_data
import tests.testing_utilities as test_utils
import thiscovery_dev_tools.testing_tools as test_tools
from src.common.constants import STACK_NAME
from thiscovery_lib.dynamodb_utilities import Dynamodb
from thiscovery_lib.lambda_utilities import Lambda


TEST_DATETIME_1 = datetime.datetime(
    year=2020,
    month=11,
    day=27,
    hour=13,
    minute=40,
    second=45,
)


class AppointmentsCleanerTestCase(test_tools.BaseTestCase, test_utils.DdbMixin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ac = clean.AppointmentsCleaner(
            logger=cls.logger,
        )
        cls.ddb_client = Dynamodb(stack_name=app.STACK_NAME)
        cls.populate_appointments_table()

    def test_01_get_appointments_to_be_deleted_ok(self):
        result = self.ac.get_appointments_to_be_deleted(now=TEST_DATETIME_1)
        expected_result = ['448161419', '448161724']
        self.assertEqual(expected_result, result)

    def test_02_delete_old_appointments_ok(self):
        ac = copy.copy(self.ac)
        ac.target_appointment_ids = ['448161419', '448161724']
        ac.delete_old_appointments()
        appointment_item_keys = [x['id'] for x in self.ddb_client.scan(table_name=app.APPOINTMENTS_TABLE)]
        self.assertEqual(4, len(appointment_item_keys))
        for i in ac.target_appointment_ids:
            self.assertNotIn(i, appointment_item_keys)

    @unittest.skipUnless(os.environ['TEST_ON_AWS'] == 'True', 'Invokes lambda on AWS')
    def test_03_delete_old_appointments_lambda_working_on_aws(self):
        self.clear_appointments_table()
        lambda_client = Lambda(stack_name=STACK_NAME)
        response = lambda_client.invoke(
            function_name='DeleteOldAppointments'
        )
        self.assertNotIn('FunctionError', response.keys())
        self.assertEqual(list(), response['Payload'])
