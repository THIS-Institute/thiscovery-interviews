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

import thiscovery_lib.utilities as utils


class EmailsApiClient:

    def __init__(self, correlation_id=None):
        self.correlation_id = correlation_id
        self.base_url = 'https://email-api.thiscovery.org/'

    def send_email(self, email_dict):
        """
        Args:
            email_dict: must contain "to", "subject", "body_text" and "body_html"

        Returns:
        """
        body_json = json.dumps(email_dict)
        result = utils.aws_post('v1/send', self.base_url, request_body=body_json)
        assert result['statusCode'] == HTTPStatus.OK, f'Call to email API returned error: {result}'
        return result
