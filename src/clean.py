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

import thiscovery_lib.utilities as utils
from common.constants import APPOINTMENTS_TABLE, STACK_NAME
from thiscovery_lib.dynamodb_utilities import Dynamodb


class AppointmentsCleaner:

    def __init__(self, logger=None, correlation_id=None):
        self.ddb_client = Dynamodb(stack_name=STACK_NAME)
        self.correlation_id = correlation_id
        self.target_appointment_ids = self.get_appointments_to_be_deleted()
        self.logger = logger
        if logger is None:
            self.logger = utils.get_logger()

    def get_appointments_to_be_deleted(self, now=None):
        """
        Queries ddb for appointments booked for 60 days ago
        """
        if now is None:
            now = utils.now_with_tz()
        date_format = '%Y-%m-%d'
        sixty_days_ago = now - datetime.timedelta(days=60)
        sixty_days_ago_string = sixty_days_ago.strftime(date_format)
        result = self.ddb_client.query(
            table_name=APPOINTMENTS_TABLE,
            IndexName="reminders-index",
            KeyConditionExpression='appointment_date = :date',
            ExpressionAttributeValues={
                ':date': sixty_days_ago_string,
            }
        )
        return [x['id'] for x in result]

    def delete_old_appointments(self):
        results = list()
        for app_id in self.target_appointment_ids:
            result = self.ddb_client.delete_item(
                table_name=APPOINTMENTS_TABLE,
                key=app_id,
            )
            results.append(result['ResponseMetadata']['HTTPStatusCode'])
        return results

        # this is more efficient than the for loop used above but doesn't return anything, so worse for testing
        # return self.ddb_client.batch_delete_items(
        #     table_name=APPOINTMENTS_TABLE,
        #     keys=self.target_appointment_ids,
        # )


@utils.lambda_wrapper
def delete_old_appointments(event, context):
    cleaner = AppointmentsCleaner(
        logger=event['logger'],
        correlation_id=event['correlation_id'],
    )
    return cleaner.delete_old_appointments()
