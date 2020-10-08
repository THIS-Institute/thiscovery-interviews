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
import datetime
import json
import re
import sys
from dateutil import parser
from http import HTTPStatus

import common.utilities as utils
from appointments import AcuityAppointment, AppointmentNotifier
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

    def __init__(self, logger=None, correlation_id=None):
        self.ddb_client = Dynamodb()
        self.correlation_id = correlation_id
        self.target_appointment_ids = self.get_appointments_to_be_reminded()
        self.logger = logger
        if logger is None:
            self.logger = utils.get_logger()

    def get_appointments_to_be_reminded(self):
        date_format = '%Y-%m-%d'
        now = utils.now_with_tz()
        tomorrow = now + datetime.timedelta(days=1)
        today_string = now.strftime(date_format)
        tomorrow_string = tomorrow(date_format)
        return self.ddb_client.query(
            table_name=APPOINTMENTS_TABLE,
            IndexName="reminders-index",
            KeyConditionExpression='appointment_date = :date '
                                   'AND latest_participant_notification '
                                   'BETWEEN :t1 AND :t2',
            ExpressionAttributeValues={
                ':date': tomorrow_string,
                ':t1': '0000-00-00',
                ':t2': today_string,
            }
        )

    def send_reminders(self):
        results = list()
        for app_id in self.target_appointment_ids:
            appointment = AcuityAppointment(
                appointment_id=app_id,
                logger=self.logger,
                correlation_id=self.correlation_id
            )
            notifier = AppointmentNotifier(
                appointment=appointment,
                logger=self.logger,
                correlation_id=self.correlation_id
            )
            try:
                reminder_result = notifier.send_reminder()
            except Exception:
                self.logger.error('AppointmentNotifier.send_reminder raised an exception', details={
                    'appointment': appointment.as_dict(),
                    'exc_info': f'{sys.exc_info()}',
                    'correlation_id': self.correlation_id,
                })
                reminder_result = None
            results.append(reminder_result)
        return results


@utils.lambda_wrapper
def interview_reminder_handler(event, context):
    handler = RemindersHandler(
        logger=event['logger'],
        correlation_id=event['correlation_id'],
    )
    handler.send_reminders()
