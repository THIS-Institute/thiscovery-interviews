import sys

from http import HTTPStatus
from pprint import pprint

import src.common.utilities as utils
from src.common.acuity_utilities import AcuityClient
from src.common.dynamodb_utilities import Dynamodb
from src.main import CalendarBlocker


def main():
    calendar_name = input("Please input the name of the calendar you want to add to Dynamodb, as shown in Acuity's UI:")
    if not calendar_name:
        sys.exit()
    acuity_client = AcuityClient()
    ddb_client = Dynamodb()
    blocker = CalendarBlocker(ddb_client.logger, None)
    acuity_calendars = acuity_client.get_calendars()
    target_calendar = None
    for c in acuity_calendars:
        if c['name'] == calendar_name:
            target_calendar = c
            continue
    if target_calendar:
        response = ddb_client.put_item(
            'Calendars',
            target_calendar['id'],
            item_type='acuity-calendar',
            item_details=target_calendar,
            item={
                'label': target_calendar['name'],
                'block_monday_morning': True,
                'emails_to_notify': list(),
                'myinterview_link': None,
            },
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == HTTPStatus.OK, f'Dynamodb client put_item operation failed with response: {response}'
        print(f'Calendar "{calendar_name}" successfully added to Dynamodb table')
    else:
        raise utils.ObjectDoesNotExistError(f'Calendar "{calendar_name}" not found in Acuity')


if __name__ == '__main__':
    main()
