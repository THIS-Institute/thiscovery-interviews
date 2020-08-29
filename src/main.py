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

import thiscovery_lib.utilities as utils
from common.acuity_utilities import AcuityClient
from common.dynamodb_utilities import Dynamodb
from common.sns_utilities import SnsClient


class CalendarBlocker:
    def __init__(self, logger, correlation_id):
        self.logger = logger
        self.correlation_id = correlation_id
        self.calendars_table = 'Calendars'
        self.blocks_table = 'CalendarBlocks'
        self.ddb_client = Dynamodb()
        self.acuity_client = AcuityClient()
        self.sns_client = SnsClient()

    def notify_sns_topic(self, message, subject):
        topic_arn = utils.get_secret('sns-topics')['interview-notifications-arn']
        self.sns_client.publish(
            message=message,
            topic_arn=topic_arn,
            Subject=subject,
        )

    def get_target_calendar_ids(self):
        calendars = self.ddb_client.scan(
            self.calendars_table,
            'block_monday_morning',
            [True],
        )
        return [(x['id'], x['label']) for x in calendars]

    def block_upcoming_weekend(self, calendar_id):
        next_saturday_date = next_weekday(5)
        block_start = datetime.datetime.combine(
            next_saturday_date,
            datetime.time(hour=0, minute=0)
        )
        next_monday_date = next_weekday(0)
        block_end = datetime.datetime.combine(
            next_monday_date,
            datetime.time(hour=12, minute=0)
        )
        return self.acuity_client.post_block(calendar_id, block_start, block_end)

    def create_blocks(self):
        calendars = self.get_target_calendar_ids()
        self.logger.debug('Calendars to block', extra={'calendars': calendars})
        created_blocks_ids = list()
        affected_calendar_names = list()
        for i, name in calendars:
            try:
                block_dict = self.block_upcoming_weekend(i)
                created_blocks_ids.append(block_dict['id'])
                affected_calendar_names.append(name)
                response = self.ddb_client.put_item(
                    self.blocks_table,
                    block_dict['id'],
                    item_type='calendar-block',
                    item_details=block_dict,
                    item={
                        'status': 'new',
                        'error_message': None,
                    },
                    correlation_id=self.correlation_id
                )
                assert response['ResponseMetadata']['HTTPStatusCode'] == HTTPStatus.OK, \
                    f'Call to Dynamodb client put_item method failed with response: {response}. '
            except Exception as err:
                self.logger.error(
                    f'{repr(err)} {len(created_blocks_ids)} blocks were created before this error occurred. '
                    f'Created blocks ids: {created_blocks_ids}'
                )
                raise

        return created_blocks_ids, affected_calendar_names

    def mark_failed_block_deletion(self, item_key, exception):
        error_message = f'This error happened when trying to delete Acuity calendar block {item_key}: {repr(exception)}'
        self.logger.error(error_message)
        self.ddb_client.update_item(
            self.blocks_table,
            item_key,
            name_value_pairs={
                'status': 'error',
                'error_message': error_message
            }
        )

    def delete_blocks(self):
        blocks = self.ddb_client.scan(
            self.blocks_table,
            filter_attr_name='status',
            filter_attr_values=['new'],
            correlation_id=self.correlation_id
        )
        deleted_blocks_ids = list()
        affected_calendar_names = list()
        for b in blocks:
            item_key = b.get('id')
            try:
                delete_response = self.acuity_client.delete_block(item_key)
                assert delete_response == HTTPStatus.NO_CONTENT, f'Call to Acuity client delete_block method failed with response: {delete_response}. ' \
                    f'{len(deleted_blocks_ids)} blocks were deleted before this error occurred. Deleted blocks ids: {deleted_blocks_ids}'
                deleted_blocks_ids.append(item_key)
                affected_calendar_names.append(self.acuity_client.get_calendar_by_id(b['details']['calendarID'])['name'])
                response = self.ddb_client.delete_item(
                    self.blocks_table,
                    item_key,
                    correlation_id=self.correlation_id
                )
                assert response['ResponseMetadata']['HTTPStatusCode'] == HTTPStatus.OK, \
                    f'Call to Dynamodb client delete_item method failed with response: {response}. ' \
                    f'{len(deleted_blocks_ids)} blocks were deleted before this error occurred. Deleted blocks ids: {deleted_blocks_ids}'
            except Exception as err:
                self.mark_failed_block_deletion(item_key, err)
                continue

        return deleted_blocks_ids, affected_calendar_names


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
    try:
        blocks_created_ids, affected_calendars = calendar_blocker.create_blocks()
        logger.info(f'Blocked {len(blocks_created_ids)} calendars for next Monday morning',
                    extra={'blocks_created_ids': blocks_created_ids, 'affected_calendars': affected_calendars})
        calendar_blocker.notify_sns_topic(
            message=f"Monday morning (00:00 to 12:00) was just blocked on the following Acuity calendars: {', '.join(affected_calendars)}.",
            subject=f"[thiscovery-interviews notification] SUCCESS: Monday morning blocked in {len(affected_calendars)} Acuity calendars"
        )
    except Exception as err:
        calendar_blocker.notify_sns_topic(
            message=f"Failed to block Monday morning (00:00 to 12:00) in Acuity calendars. Error message:\n "
                    f"{repr(err)}\n\n"
                    f"Please refer to CloudWatch logs for more details.",
            subject=f"[thiscovery-interviews notification] ERROR: Failed to create Monday morning blocks in calendars"
        )


@utils.lambda_wrapper
def clear_blocks(event, context):
    logger = event['logger']
    correlation_id = event['correlation_id']
    calendar_blocker = CalendarBlocker(logger, correlation_id)
    try:
        blocks_deleted, affected_calendars = calendar_blocker.delete_blocks()
        logger.info(f'Deleted {len(blocks_deleted)} calendar blocks from Acuity and Dynamodb',
                    extra={'blocks_deleted': blocks_deleted, 'affected_calendars': affected_calendars})
        calendar_blocker.notify_sns_topic(
            message=f"Deleted Monday morning (00:00 to 12:00) blocks on the following Acuity calendars: {', '.join(affected_calendars)}.",
            subject=f"[thiscovery-interviews notification] SUCCESS: Monday morning block removed from calendars"
        )
    except Exception as err:
        calendar_blocker.notify_sns_topic(
            message=f"Failed to remove Monday morning (00:00 to 12:00) block in Acuity calendars. Error message:\n "
                    f"{repr(err)}\n\n"
                    f"Please refer to CloudWatch logs for more details.",
            subject=f"[thiscovery-interviews notification] ERROR: Failed to delete Monday morning blocks in calendars"
        )
