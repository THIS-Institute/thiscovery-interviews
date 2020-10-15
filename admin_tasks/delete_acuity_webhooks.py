import thiscovery_lib.utilities as utils
from src.common.acuity_utilities import AcuityClient


def main():
    logger = utils.get_logger()
    ac = AcuityClient()
    webhooks = ac.get_webhooks()
    env_name = utils.get_environment_name()
    for wh in webhooks:
        if env_name in wh['target']:
            ac.delete_webhooks(wh['id'])
            logger.info('Deleted Acuity webhook', extra={'webhook': wh})


if __name__ == '__main__':
    main()
