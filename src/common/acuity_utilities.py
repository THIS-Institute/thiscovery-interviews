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


class AcuityClient:
    def __init__(self):
        acuity_credentials = utils.get_secret('acuity-connection')
        self.session = requests.Session()
        self.session.auth = (
            acuity_credentials['user-id'],
            acuity_credentials['api-key'],
        )

    def get_appointments(self):
        response = self.session.get("https://acuityscheduling.com/api/v1/appointments")
        if response.ok:
            pprint(response.json())


if __name__ == '__main__':
    acuity_client = AcuityClient()
    acuity_client.get_appointments()