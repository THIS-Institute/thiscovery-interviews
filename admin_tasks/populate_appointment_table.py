"""
This script adds an appointment to the Dynamodb Appointment table using data from Acuity.
It can be used to manually fix errors due to rescheduling/cancellation of appointments
predating the deployment of this stack
"""

from pprint import pprint

from src.appointments import AcuityAppointment
from tests.test_data import td


def add_appointment_to_table(appointment_id, interview_link=None, interactive=False):
    appointment = AcuityAppointment(appointment_id=appointment_id)
    if interview_link:
        appointment.link = interview_link
    appointment.get_appointment_info_from_acuity()
    appointment.appointment_type.ddb_load()
    if interactive:
        print("The following appointment item will be added to Dynamodb:\n")
        pprint(appointment.as_dict())

        confirmation = input("\nWould you like to proceed? (y/n)")
        if confirmation in ['y', 'Y']:
            appointment.ddb_dump()
        else:
            print("Aborted")
    else:
        appointment.ddb_dump()


def populate_with_test_data():
    for app_key in [
        'test_appointment_id',
        'dev_appointment_id',
        'dev_appointment_no_link_id',
        'dev_appointment_no_link_participant_not_in_thiscovery_database_id',
        'dev_appointment_no_link_participant_does_not_have_user_project',
        'test_appointment_no_notif_id',
    ]:
        add_appointment_to_table(
            appointment_id=td[app_key]
        )


def main():
    appointment_id = input("Please enter the Acuity appointment id:")
    interview_link = input("Please enter the interview link (if any):")
    add_appointment_to_table(appointment_id=appointment_id, interview_link=interview_link, interactive=True)


if __name__ == '__main__':
    main()
    # populate_with_test_data()