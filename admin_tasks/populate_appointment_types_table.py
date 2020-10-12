"""
This script populates the Dynamodb AppointmentTypes table with data from Acuity.
It is intended to be run as an one-off process to facilitate initial setup
of this stack.
"""

from pprint import pprint
from src.appointments import AppointmentType
from src.common.acuity_utilities import AcuityClient
from common.utilities import ObjectDoesNotExistError


def main():
    ac = AcuityClient()
    app_types = ac.get_appointment_types()
    pprint(app_types)
    for at in app_types:
        appointment_type = AppointmentType()
        appointment_type.type_id = at['id']
        try:
            appointment_type.ddb_load()
        except ObjectDoesNotExistError:  # appointment type not found in ddb
            appointment_type.name = at['name']
            appointment_type.category = at['category']
            appointment_type.has_link = False
            appointment_type.send_notifications = False
            appointment_type.project_task_id = None
            appointment_type.ddb_dump()
            print(f"Added appointment type {appointment_type.type_id} ({appointment_type.name}) to Dynamodb.")
        else:
            print(f"Skipped appointment type {appointment_type.type_id} ({appointment_type.name}); already exists in Dynamodb.")


if __name__ == '__main__':
    main()
