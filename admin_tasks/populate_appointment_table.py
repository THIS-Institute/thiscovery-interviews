"""
This script adds an appointment to the Dynamodb Appointment table using data from Acuity.
It can be used to manually fix errors due to rescheduling/cancellation of appointments
predating the deployment of this stack
"""

from pprint import pprint


from src.appointments import AcuityAppointment


def main():
    appointment_id = input("Please enter the Acuity appointment id:")
    interview_link = input("Please enter the interview link (if any):")
    appointment = AcuityAppointment(appointment_id=appointment_id)
    if interview_link:
        appointment.link = interview_link
    appointment.get_appointment_info_from_acuity()
    appointment.appointment_type.ddb_load()
    print("The following appointment item will be added to Dynamodb:\n")
    pprint(appointment.as_dict())

    confirmation = input("\nWould you like to proceed? (y/n)")
    if confirmation in ['y', 'Y']:
        appointment.ddb_dump()
    else:
        print("Aborted")


if __name__ == '__main__':
    main()
