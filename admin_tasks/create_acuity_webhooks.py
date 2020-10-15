import thiscovery_lib.utilities as utils
from src.common.acuity_utilities import AcuityClient


EVENTS = [
    'appointment.scheduled',
    'appointment.rescheduled',
    'appointment.canceled',
    # 'appointment.changed',
]


def main():
    logger = utils.get_logger()
    ac = AcuityClient()
    for e in EVENTS:
        try:
            response = ac.post_webhooks(e)
            logger.info('Created webhook', extra={'response': response})
        except utils.DetailedValueError:
            pass


if __name__ == '__main__':
    main()
