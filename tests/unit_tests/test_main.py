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

import src.main as m
import src.common.utilities as utils
import tests.testing_utilities as test_utils
from src.common.acuity_utilities import AcuityClient


class TestMain(test_utils.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_next_weekday(self):
        test_date = datetime.datetime(2020, 12, 25)
        expected_wednesday_after_xmas = datetime.datetime(2020, 12, 30)
        wednesday_after_xmas = m.next_weekday(2, d=test_date)
        self.assertEqual(expected_wednesday_after_xmas, wednesday_after_xmas)
        expected_saturday_after_xmas = datetime.datetime(2020, 12, 26)
        saturday_after_xmas = m.next_weekday(5, d=test_date)
        self.assertEqual(expected_saturday_after_xmas, saturday_after_xmas)


class TestCalendarBlocker(test_utils.BaseTestCase):
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
        cls.calendar_blocker = m.CalendarBlocker(cls.logger, correlation_id=None)

    def test_get_target_calendar_ids(self):
        result = self.calendar_blocker.get_target_calendar_ids()
        self.assertIn(str(self.test_calendar['id']), result)

    def
