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
import requests
from pprint import pprint

import common.utilities as utils


class AcuityClient:
    base_url = 'https://acuityscheduling.com/api/v1/'
    strftime_format_str = '%Y-%m-%d %I:%M%p'

    def __init__(self):
        acuity_credentials = utils.get_secret('acuity-connection')
        self.session = requests.Session()
        self.session.auth = (
            acuity_credentials['user-id'],
            acuity_credentials['api-key'],
        )

    def get_calendars(self):
        response = self.session.get(f"{self.base_url}calendars")
        if response.ok:
            return response.json()
        else:
            raise utils.DetailedValueError(f'Acuity get calendars call failed with response: {response}')

    def get_appointments(self):
        response = self.session.get(f"{self.base_url}appointments")
        if response.ok:
            pprint(response.json())
        return response

    def post_block(self, calendar_id, start, end, notes="automated block"):
        """

        Args:
            calendar_id (int): acuity calendar id
            start (datetime.datetime): start time of block
            end (datetime.datetime): end time of block
            notes (str): any notes to include for the blocked off time

        Returns:

        """
        body_params = {
            "calendarID": calendar_id,
            "start": start.strftime(self.strftime_format_str),
            "end": end.strftime(self.strftime_format_str),
            "notes": notes,
        }
        body_json = json.dumps(body_params)
        response = self.session.post(f"{self.base_url}blocks", data=body_json)
        if response.ok:
            pprint(response.json())
        return response


if __name__ == '__main__':
    acuity_client = AcuityClient()
    start = datetime.datetime.now() + datetime.timedelta(days=2)
    end = start + datetime.timedelta(hours=1)
    response = acuity_client.post_block(4038206, start, end)
    pprint(response.json())
