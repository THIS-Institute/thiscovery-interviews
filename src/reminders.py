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
from dateutil import parser
from http import HTTPStatus

import common.utilities as utils
from common.acuity_utilities import AcuityClient
from common.constants import APPOINTMENTS_TABLE, APPOINTMENT_TYPES_TABLE, COMMON_PROPERTIES, \
    WEB_PROPERTIES, BOOKING_RESCHEDULING_PROPERTIES, DEFAULT_TEMPLATES
from common.core_api_utilities import CoreApiClient
from common.dynamodb_utilities import Dynamodb
from common.emails_api_utilities import EmailsApiClient


class RemindersHandler:
    """
    Send a reminder:
        - One day before an appointment (appointment_datetime)
        - Unless an email (notification or reminder) was already sent today (latest_email_datetime)
    """

    def __init__(self):
        self.ddb_client = Dynamodb()


    def get_appointments_to_be_reminded(self):
        self.ddb_client.query(
            table_name=APPOINTMENTS_TABLE,
            filter_attr_name='reminder',
            filter_attr_values=[None]
        )




def send_reminder():
    pass


@utils.lambda_wrapper
def interview_reminder_handler(event, context):
    """
    To be implemented
    """
    raise NotImplementedError
