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

import os
import unittest

import src.appointments as app
import src.common.utilities as utils
import tests.test_data as test_data
from src.common.dynamodb_utilities import Dynamodb
from local.dev_config import TEST_ON_AWS


def tests_running_on_aws():
    """
    Checks if tests are calling AWS API endpoints
    """
    test_on_aws = os.environ.get('TEST_ON_AWS')
    if test_on_aws is None:
        test_on_aws = TEST_ON_AWS
    elif test_on_aws.lower() == 'false':
        test_on_aws = False
    return test_on_aws


class DdbMixin:
    @classmethod
    def set_notifications_table(cls):
        try:
            cls.notifications_table = f"thiscovery-core-{cls.env_name}-notifications"
        except AttributeError:
            cls.env_name = utils.get_environment_name()
            cls.notifications_table = f"thiscovery-core-{cls.env_name}-notifications"

    @classmethod
    def clear_notifications_table(cls):
        cls.set_notifications_table()
        try:
            cls.ddb_client.delete_all(table_name=cls.notifications_table, table_name_verbatim=True)
        except AttributeError:
            cls.ddb_client = Dynamodb()
            cls.ddb_client.delete_all(table_name=cls.notifications_table, table_name_verbatim=True)

    @classmethod
    def clear_appointments_table(cls):
        try:
            cls.ddb_client.delete_all(table_name=app.APPOINTMENTS_TABLE)
        except AttributeError:
            cls.ddb_client = Dynamodb()
            cls.ddb_client.delete_all(table_name=app.APPOINTMENTS_TABLE)

    @classmethod
    def populate_appointments_table(cls, fast_mode=True):
        """
        Args:
            fast_mode: if True, uses ddb batch_writer to quickly populate the appointments table but items
                will not contain created, modified and type fields added by Dynamodb.put_item
        """
        if fast_mode:
            ddb_client = Dynamodb()
            app_table = ddb_client.get_table(table_name=app.APPOINTMENTS_TABLE)
            with app_table.batch_writer() as batch:
                for appointment in test_data.appointments.values():
                    appointment['id'] = appointment['appointment_id']
                    batch.put_item(appointment)
        else:
            for appointment_dict in test_data.appointments.values():
                appointment = app.AcuityAppointment(appointment_dict["appointment_id"])
                appointment.from_dict(appointment_dict)
                at = app.AppointmentType()
                at.from_dict(appointment.appointment_type)
                appointment.appointment_type = at
                try:
                    appointment.ddb_dump()
                except utils.DetailedValueError:
                    cls.logger.debug('PutItem failed, which probably '
                                     'means Appointment table already contains '
                                     'the required test data; aborting this methid', extra={})
                    break


class BaseTestCase(unittest.TestCase):
    """
    Subclass of unittest.TestCase with methods frequently used in Thiscovery testing.
    """
    maxDiff = None
    secrets_client = None

    @classmethod
    def setUpClass(cls):
        utils.set_running_unit_tests(True)
        if cls.secrets_client is None:  # initialise a new secrets_client only if another class instance has not done so yet
            cls.secrets_client = utils.SecretsManager()
        cls.secrets_client.create_or_update_secret('runtime-parameters', {'running-tests': 'true'})
        cls.logger = utils.get_logger()

    @classmethod
    def tearDownClass(cls):
        if cls.secrets_client is None:
            cls.secrets_client = utils.SecretsManager()
        cls.secrets_client.create_or_update_secret('runtime-parameters', {'running-tests': 'false'})
        utils.set_running_unit_tests(False)


@unittest.skipIf(not tests_running_on_aws(), "Testing are using local methods and this test only makes sense if calling an AWS API endpoint")
class AlwaysOnAwsTestCase(BaseTestCase):
    """
    Skips tests if tests are running locally
    """
    pass


def _aws_request(method, url, params=None, data=None, aws_api_key=None):
    return utils.aws_request(method, url, AWS_TEST_API, params=params, data=data, aws_api_key=aws_api_key)


# def aws_get(url, params):
#     return _aws_request(method='GET', url=url, params=params)
#
#
# def aws_post(url, request_body):
#     return _aws_request(method='POST', url=url, data=request_body)
#
#
# def aws_patch(url, request_body):
#     return _aws_request(method='PATCH', url=url, data=request_body)
#
#
def _test_request(request_method, local_method, aws_url, path_parameters=None, querystring_parameters=None, request_body=None, aws_api_key=None,
                  correlation_id=None):
    logger = utils.get_logger()

    if tests_running_on_aws():
        if path_parameters is not None:
            url = aws_url + '/' + path_parameters['id']
        else:
            url = aws_url
        logger.info(f'Url passed to _aws_request: {url}', extra={'path_parameters': path_parameters, 'querystring_parameters': querystring_parameters})
        return _aws_request(method=request_method, url=url, params=querystring_parameters, data=request_body, aws_api_key=aws_api_key)
    else:
        event = {}
        if path_parameters is not None:
            event['pathParameters'] = path_parameters
        if querystring_parameters is not None:
            event['queryStringParameters'] = querystring_parameters
        if request_body is not None:
            event['body'] = request_body
        return local_method(event, correlation_id)


# def test_get(local_method, aws_url, path_parameters=None, querystring_parameters=None, aws_api_key=None, correlation_id=None):
#     return _test_request('GET', local_method, aws_url, path_parameters=path_parameters,
#                          querystring_parameters=querystring_parameters, aws_api_key=aws_api_key, correlation_id=correlation_id)
#
#
def test_post(local_method, aws_url, path_parameters=None, request_body=None, correlation_id=None):
    return _test_request('POST', local_method, aws_url, path_parameters=path_parameters, request_body=request_body, correlation_id=correlation_id)


# def test_patch(local_method, aws_url, path_parameters=None, request_body=None, correlation_id=None):
#     return _test_request('PATCH', local_method, aws_url, path_parameters=path_parameters, request_body=request_body, correlation_id=correlation_id)
#
#
def test_put(local_method, aws_url, path_parameters=None, querystring_parameters=None, request_body=None, correlation_id=None):
    return _test_request('PUT', local_method, aws_url, path_parameters=path_parameters,
                         querystring_parameters=querystring_parameters, request_body=request_body, correlation_id=correlation_id)