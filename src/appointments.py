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
import re
from http import HTTPStatus

import common.utilities as utils
from common.acuity_utilities import AcuityClient
from common.core_api_utilities import CoreApiClient
from common.dynamodb_utilities import Dynamodb


class AcuityAppointmentEvent:
    appointment_type_table = 'AppointmentTypes'

    def __init__(self, acuity_event, logger, correlation_id=None):
        self.logger = logger
        self.correlation_id = correlation_id
        self.acuity_client = AcuityClient(correlation_id=self.correlation_id)
        self.ddb_client = Dynamodb()
        self.core_api_client = CoreApiClient(correlation_id=self.correlation_id)

        event_pattern = re.compile(
            r"action=appointment\.(?P<action>scheduled|rescheduled|canceled|changed)"
            r"&id=(?P<appointment_id>\d+)"
            r"&calendarID=\d+"
            r"&appointmentTypeID=(?P<type_id>\d+)"
        )
        m = event_pattern.match(acuity_event)
        try:
            self.action = m.group('action')
            self.appointment_id = m.group('appointment_id')
            self.type_id = m.group('type_id')
        except AttributeError as err:
            self.logger.error('event_pattern does not match acuity_event', extra={'acuity_event': acuity_event})
            raise

    def get_appointment_details(self):
        r = self.acuity_client.get_appointment_by_id(self.appointment_id)
        return r['email'], r['appointmentTypeID']

    def get_project_task_id_and_status(self):
        item = self.ddb_client.get_item(self.appointment_type_table, self.type_id, correlation_id=self.correlation_id)
        return item['project_task_id'], item['status']

    def main(self):
        self.logger.info('Parsed Acuity event', extra={'action': self.action, 'appointment_id': self.appointment_id, 'type_id': self.type_id})
        email, appointment_type_id = self.get_appointment_details()
        assert str(appointment_type_id) == self.type_id, f'Unexpected appointment type id ({appointment_type_id}) in get_appointment_by_id response. ' \
                                                         f'Expected: {self.type_id}.'
        try:
            user_id = self.core_api_client.get_user_id_by_email(email)
        except Exception as err:
            self.logger.error(f'Failed to retrieve user_id for {email}', extra={'exception': repr(err)})
            raise err

        try:
            project_task_id, appointment_type_status = self.get_project_task_id_and_status()
        except Exception as err:
            self.logger.error(f'Failed to retrieve project_task_id for appointment_type_id {self.type_id}', extra={'exception': repr(err)})
            raise err

        if appointment_type_status in ['active']:
            user_task_id = self.core_api_client.get_user_task_id_for_project(user_id, project_task_id)
            self.logger.debug('user_task_id', extra={'user_task_id': user_task_id})
            result = self.core_api_client.set_user_task_completed(user_task_id)
            self.logger.info(f'Updated user task {user_task_id} status to complete')
            return result


@utils.lambda_wrapper
def interview_appointment_api(event, context):
    logger = event['logger']
    correlation_id = event['correlation_id']
    acuity_event = event['body']
    appointment_event = AcuityAppointmentEvent(acuity_event, logger, correlation_id=correlation_id)
    return appointment_event.main()

