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
from http import HTTPStatus

import common.utilities as utils


class CoreApiClient:

    def __init__(self, correlation_id=None):
        self.correlation_id = correlation_id
        env_name = utils.get_environment_name()
        if env_name == 'prod':
            self.base_url = 'https://api.thiscovery.org/'
        else:
            self.base_url = f'https://{env_name}-api.thiscovery.org/'

    def get_user_id_by_email(self, email):
        # todo: similar code is used in stack s3-to-sdhs; adapt that stack to use this client
        result = utils.aws_get('v1/user', self.base_url, params={'email': email})
        assert result['statusCode'] == HTTPStatus.OK, f'Call to core API returned error: {result}'
        return json.loads(result['body'])['id']

    def get_user_task_id_for_project(self, user_id, project_task_id):
        result = utils.aws_get('v1/usertask', self.base_url, params={'user_id': user_id})
        assert result['statusCode'] == HTTPStatus.OK, f'Call to core API returned error: {result}'
        for user_task in json.loads(result['body']):
            if user_task['project_task_id'] == project_task_id:
                return user_task['user_task_id']

    def set_user_task_completed(self, user_task_id):
        result = utils.aws_request('PUT', 'v1/user-task-completed', self.base_url, params={'user_task_id': user_task_id})
        assert result['statusCode'] == HTTPStatus.NO_CONTENT, f'Call to core API returned error: {result}'
        return result