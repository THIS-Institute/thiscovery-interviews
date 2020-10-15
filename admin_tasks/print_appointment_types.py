from pprint import pprint

from src.common.acuity_utilities import AcuityClient


def main():
    acuity_client = AcuityClient()
    return acuity_client.get_appointment_types()


if __name__ == '__main__':
    pprint(main())
