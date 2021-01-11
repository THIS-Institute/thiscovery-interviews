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
import json
import thiscovery_lib.utilities as utils

from http import HTTPStatus
from thiscovery_lib.dynamodb_utilities import Dynamodb

from common.constants import APPOINTMENTS_TABLE, STACK_NAME


def get_appointments_by_type(type_ids, correlation_id=None):
    """
    Args:
        type_ids (list): Appointment type ids to query ddb
        correlation_id:
    Returns:
        List of appointments matching any of the input type ids
    """
    ddb_client = Dynamodb(stack_name=STACK_NAME, correlation_id=correlation_id)
    items = list()
    for i in type_ids:
        result = ddb_client.query(
            table_name=APPOINTMENTS_TABLE,
            IndexName="project-appointments-index",
            KeyConditionExpression='appointment_type_id = :type_id',
            ExpressionAttributeValues={
                ':type_id': i,
            }
        )
        items += result
    return items


@utils.lambda_wrapper
@utils.api_error_handler
def get_appointments_by_type_api(event, context):
    logger = event['logger']
    correlation_id = event['correlation_id']
    body = json.loads(event['body'])
    logger.debug('API call', extra={
        'body': body,
        'correlation_id': correlation_id
    })
    result = get_appointments_by_type(
        type_ids=body['type_ids'],
        correlation_id=correlation_id,
    )
    response_body = {
        'appointments': result,
        'correlation_id': correlation_id,
    }
    return {"statusCode": HTTPStatus.OK, 'body': json.dumps(response_body)}
