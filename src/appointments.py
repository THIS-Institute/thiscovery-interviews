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
import re

import common.utilities as utils
from common.acuity_utilities import AcuityClient


class AcuityAppointmentEvent:
    def __init__(self, acuity_event, logger, correlation_id=None):
        self.logger = logger
        self.acuity_client = AcuityClient(correlation_id=correlation_id)
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

    def get_appointment_email(self):
        return self.acuity_client.get_appointment_by_id(self.appointment_id)['email']

    def main(self):
        self.logger.info('Parsed Acuity event', extra={'action': self.action, 'appointment_id': self.appointment_id, 'type_id': self.type_id})
        email = self.get_appointment_email()


@utils.lambda_wrapper
def interview_appointment_api(event, context):
    logger = event['logger']
    correlation_id = event['correlation_id']
    acuity_event = event['body']
    appointment_event = AcuityAppointmentEvent(acuity_event, logger, correlation_id=correlation_id)
    return appointment_event.main()

