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
import src.appointments as app
import thiscovery_lib.utilities as utils
import tests.test_data as test_data
from thiscovery_lib.dynamodb_utilities import Dynamodb
from local.dev_config import TEST_ON_AWS


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
            cls.ddb_client = Dynamodb()
            cls.ddb_client.delete_all(table_name=app.APPOINTMENTS_TABLE)

    @classmethod
    def populate_appointments_table(cls, fast_mode=True):
        """
        Args:
            fast_mode: if True, uses ddb batch_writer to quickly populate the appointments table but items
                will not contain created, modified and type fields added by Dynamodb.put_item
        """
        if fast_mode:
            ddb_client = Dynamodb()
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
