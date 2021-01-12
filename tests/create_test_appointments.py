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
import local.dev_config
import local.secrets
from datetime import datetime
from common.acuity_utilities import AcuityClient


def main():
    client = AcuityClient()
    client.post_appointment(
        date_and_time=datetime(2026, 1, 8, 10, 15),
        type_id=14792299,
        firstname='Eddie',
        lastname='Eagleton',
        email='eddie@email.co.uk',
        calendarID=4038206,
        fields=[
            {
                'id': 8861964,  # anon_user_task_id
                'value': '4a7a29e8-2869-469f-a922-5e9ff5af4583',
            },
            {
                'id': 8941105,  # anon_project_specific_user_id
                'value': 'a7a8e630-cb7e-4421-a9b2-b8bad0298267',
            },
        ],
    )


if __name__ == '__main__':
    confirmation = input('Are you sure you want to create a new test appointment in Acuity? (y/N)')
    if confirmation in ['y', 'Y']:
        main()
    else:
        print('Aborted')
