from pprint import pprint

from src.common.acuity_utilities import AcuityClient


def main(appointment_id):
    acuity_client = AcuityClient()
    return acuity_client.get_appointment_by_id(appointment_id=appointment_id)


if __name__ == '__main__':
    pprint(main(457107790))
