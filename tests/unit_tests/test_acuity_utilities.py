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

from http import HTTPStatus

import src.common.utilities as utils
import tests.testing_utilities as test_utils
from src.common.acuity_utilities import AcuityClient


class TestAcuityClient(test_utils.BaseTestCase):
    test_calendar = {
        'description': '',
        'email': '',
        'id': 4038206,
        'image': False,
        'location': '',
        'name': 'André',
        'thumbnail': False,
        'timezone': 'Europe/London'
    }

    test_block = {
        'calendarID': 4038206,
        'calendarTimezone': 'Europe/London',
        'description': 'Wednesday, December 25, 2030 09:00 - 17:00',
        'end': '2030-12-25T17:00:00+0000',
        'managed': False,
        'notes': 'Xmas break',
        'recurring': None,
        'serviceGroupID': 4038206,
        'start': '2030-12-25T09:00:00+0000',
        'until': None
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.acuity_client = AcuityClient()

    def post_test_block(self):
        block_start = datetime.datetime(2030, 12, 25, 9, 0)
        block_end = datetime.datetime(2030, 12, 25, 17, 0)
        block_notes = "Xmas break"
        return self.acuity_client.post_block(self.test_calendar['id'], block_start, block_end, notes=block_notes)

    def test_get_calendars(self):
        response = self.acuity_client.get_calendars()
        for c in response:
            del c['replyTo']
        self.assertIn(self.test_calendar, response)

    def test_post_get_and_delete_block_ok(self):
        # post test
        response = self.post_test_block()
        block_id = response['id']
        expected_block_in_get_response = response.copy()
        del response['id']
        self.assertEqual(self.test_block, response)
        # get test
        response = self.acuity_client.get_blocks(calendar_id=self.test_calendar['id'])
        self.assertIn(expected_block_in_get_response, response)
        # delete test
        delete_response = self.acuity_client.delete_block(block_id)
        self.assertEqual(HTTPStatus.NO_CONTENT, delete_response)
