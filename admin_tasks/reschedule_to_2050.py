"""
This script reschedules test appointments to 2050, to prevent them from becoming past appointments
and invalidating test results
"""
import datetime
from dateutil import parser
from dateutil.relativedelta import relativedelta
from pprint import pprint

from src.common.acuity_utilities import AcuityClient
import tests.test_data as td


def main():
    acuity_client = AcuityClient()
    for _, v in td.appointments.items():
        appointment_id = v['appointment_id']
        booked_time_string = v['acuity_info']['datetime']
        booked_time = parser.parse(booked_time_string)
        new_time = booked_time + relativedelta(years=30)
        print(appointment_id)
        print(booked_time)
        print(new_time)
        print('\n')
        # acuity_client.reschedule_appointment(
        #     appointment_id=appointment_id,
        #     new_datetime=new_time,
        # )


if __name__ == '__main__':
    main()
    # populate_with_test_data()
