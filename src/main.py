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
import requests
from pprint import pprint

import common.utilities as utils
from common.acuity_utilities import AcuityClient
from common.dynamodb_utilities import Dynamodb


CALENDAR_IDS_TABLE = None


class CalendarBlocker:
    def __init__(self, logger, correlation_id):
        self.logger = logger
        self.correlation_id = correlation_id
        self.ddb_client = Dynamodb()
        self.acuity_client = AcuityClient()

    def get_target_calendar_ids(self):
        calendar_ids = self.ddb_client.scan(
            CALENDAR_IDS_TABLE,
            'block_monday_morning',
            [True],
        )
        return [x['id'] for x in calendar_ids]

    def main:
        raise NotImplementedError

@utils.lambda_wrapper
def block_calendars_handler(event, context):
    logger = event['logger']
    correlation_id = event['correlation_id']
    calendar_blocker = CalendarBlocker(logger, correlation_id)
    calendar_blocker.main()
