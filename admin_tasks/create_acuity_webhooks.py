import common.utilities as utils
from src.common.acuity_utilities import AcuityClient


EVENTS = [
    'appointment.scheduled',
    'appointment.rescheduled',
    'appointment.canceled',
    'appointment.changed',
]


def main():
    ac = AcuityClient()
    for e in EVENTS:
        try:
            ac.post_webhooks(e)
        except utils.DetailedValueError:
            pass


if __name__ == '__main__':
    main()
