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
import requests
from pprint import pprint

import common.utilities as utils
from common.acuity_utilities import AcuityClient
from common.dynamodb_utilities import Dynamodb, STACK_NAME


class CalendarBlocker:
    def __init__(self, logger, correlation_id):
        env_name = utils.get_environment_name()
        self.logger = logger
        self.correlation_id = correlation_id
        self.calendars_table = f'{STACK_NAME}-{env_name}-Calendars'
        self.blocks_table = f'{STACK_NAME}-{env_name}-CalendarBlocks'
        self.ddb_client = Dynamodb()
        self.acuity_client = AcuityClient()

    def get_target_calendar_ids(self):
        calendar_ids = self.ddb_client.scan(
            self.calendars_table,
            'block_monday_morning',
            [True],
        )
        return [x['id'] for x in calendar_ids]

    def block_next_monday_morning(self, calendar_id):
        next_monday_date = next_weekday(0)
        morning_start = datetime.datetime.combine(
            next_monday_date,
            datetime.time(hour=0, minute=0)
        )
        morning_end = datetime.datetime.combine(
            next_monday_date,
            datetime.time(hour=12, minute=0)
        )
        return self.acuity_client.post_block(calendar_id, morning_start, morning_end)

    def main(self):
        calendar_ids = self.get_target_calendar_ids()
        created_blocks_counter = 0
        for i in calendar_ids:
            block_dict = self.block_next_monday_morning(i)
            response = self.ddb_client.put_item(
                self.blocks_table,
                block_dict['id'],
                item_type='calendar-block',
                item_details=block_dict,
                correlation_id=self.correlation_id
            )
            pprint(response)
            created_blocks_counter += 1
        return created_blocks_counter


def next_weekday(weekday, d=datetime.date.today()):
    """
    From https://stackoverflow.com/a/6558571

    Args:
        weekday (int): 0 = Monday, 1=Tuesday, 2=Wednesday...
        d (datetime.date): Base date for next weekday calculation

    Returns:

    """
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return d + datetime.timedelta(days_ahead)


@utils.lambda_wrapper
def block_calendars(event, context):
    logger = event['logger']
    correlation_id = event['correlation_id']
    calendar_blocker = CalendarBlocker(logger, correlation_id)
    print(calendar_blocker.main())


if __name__ == '__main__':
    calendar_blocker = CalendarBlocker(utils.get_logger(), utils.get_correlation_id())
    print(calendar_blocker.main())
