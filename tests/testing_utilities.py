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
import local.dev_config  # set env variables
import local.secrets  # set env variables
import copy
import thiscovery_lib.utilities as utils
import thiscovery_dev_tools.testing_tools as test_utils

import src.appointments as app
import tests.test_data as test_data
from thiscovery_lib.dynamodb_utilities import Dynamodb
from local.dev_config import TEST_ON_AWS
from src.common.constants import STACK_NAME

from local.secrets import TESTER_EMAIL_MAP


class DdbMixin:
    @classmethod
    def set_notifications_table(cls):
        try:
            cls.notifications_table = f"thiscovery-core-{cls.env_name}-notifications"
        except AttributeError:
            cls.env_name = utils.get_environment_name()
            cls.notifications_table = f"thiscovery-core-{cls.env_name}-notifications"

    @classmethod
    def clear_notifications_table(cls):
        cls.set_notifications_table()
        try:
            cls.ddb_client.delete_all(table_name=cls.notifications_table, table_name_verbatim=True)
        except AttributeError:
            cls.ddb_client = Dynamodb()
            cls.ddb_client.delete_all(table_name=cls.notifications_table, table_name_verbatim=True)

    @classmethod
    def clear_appointments_table(cls):
        try:
            cls.ddb_client.delete_all(table_name=app.APPOINTMENTS_TABLE)
        except AttributeError:
            cls.ddb_client = Dynamodb(stack_name=STACK_NAME)
            cls.ddb_client.delete_all(table_name=app.APPOINTMENTS_TABLE)

    @classmethod
    def populate_appointments_table(cls, fast_mode=True):
        """
        Args:
            fast_mode: if True, uses ddb batch_writer to quickly populate the appointments table but items
                will not contain created, modified and type fields added by Dynamodb.put_item
        """
        if fast_mode:
            ddb_client = Dynamodb(stack_name=STACK_NAME)
            app_table = ddb_client.get_table(table_name=app.APPOINTMENTS_TABLE)
            with app_table.batch_writer() as batch:
                for appointment in test_data.appointments.values():
                    appointment['id'] = appointment['appointment_id']
                    batch.put_item(appointment)
        else:
            for appointment_dict in test_data.appointments.values():
                appointment = app.AcuityAppointment(appointment_dict["appointment_id"])
                appointment.from_dict(appointment_dict)
                at = app.AppointmentType()
                at.from_dict(appointment.appointment_type)
                appointment.appointment_type = at
                try:
                    appointment.ddb_dump()
                except utils.DetailedValueError:
                    cls.logger.debug('PutItem failed, which probably '
                                     'means Appointment table already contains '
                                     'the required test data; aborting this methid', extra={})
                    break


class AppointmentsTestCase(test_utils.BaseTestCase):
    """
    Base class with data and methods for testing appointments.py
    """
    test_data = test_data.td

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.aa1 = app.AcuityAppointment(
            appointment_id=cls.test_data['test_appointment_id'],
            logger=cls.logger,
        )

        # test appointments default to have links and require notifications
        cls.at1 = app.AppointmentType(
            ddb_client=cls.aa1._ddb_client,
            acuity_client=cls.aa1._acuity_client,
            logger=cls.logger,
        )
        cls.at1.from_dict({
            'type_id': cls.test_data['test_appointment_type_id'],
            'has_link': True,
            'send_notifications': True,
            'project_task_id': cls.test_data['project_task_id'],
        })
        cls.at1.get_appointment_type_info_from_acuity()
        cls.at1.ddb_dump(update_allowed=True)

        # dev appointments default to not have links and not require notifications
        cls.at2 = app.AppointmentType(
            ddb_client=cls.aa1._ddb_client,
            acuity_client=cls.aa1._acuity_client,
            logger=cls.logger,
        )
        cls.at2.from_dict({
            'type_id': cls.test_data['dev_appointment_type_id'],
            'has_link': False,
            'send_notifications': False,
            'project_task_id': cls.test_data['project_task_id'],
        })
        cls.at2.get_appointment_type_info_from_acuity()
        cls.at2.ddb_dump(update_allowed=True)

        cls.clear_appointments_table()

    @classmethod
    def clear_appointments_table(cls):
        cls.aa1._ddb_client.delete_all(
            table_name=app.APPOINTMENTS_TABLE,
        )

    @classmethod
    def populate_calendars_table(cls):
        calendar1 = {
            "block_monday_morning": True,
            "details": {
                "description": "",
                "email": "",
                "id": 4038206,
                "image": False,
                "location": "",
                "name": "André",
                "thumbnail": False,
                "timezone": "Europe/London"
            },
            "emails_to_notify": [
                TESTER_EMAIL_MAP[utils.get_environment_name()],
                "fred@email.co.uk"
            ],
            "id": "4038206",
            "label": "André",
        }
        calendar2 = copy.deepcopy(calendar1)
        calendar2['id'] = "3887437"
        calendar2['details']['id'] = 3887437
        for calendar in [calendar1, calendar2]:
            calendar_details = calendar['details']
            del calendar['details']
            try:
                cls.aa1._ddb_client.put_item(
                    table_name=app.AppointmentNotifier.calendar_table,
                    key=calendar['id'],
                    item_type="acuity-calendar",
                    item_details=calendar_details,
                    item=calendar
                )
            except utils.DetailedValueError:
                pass