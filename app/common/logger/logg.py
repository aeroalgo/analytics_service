import os
import yaml
import logging.config
import logging
import coloredlogs


def setup_logging(default_path=f'{os.environ["PYTHONPATH"]}/app/common/logger/config.yml',
                  default_level=logging.INFO, env_key='LOG_CFG'):
    DEFAULT_FIELD_STYLES = dict(
        asctime=dict(color='green'),
        hostname=dict(color='magenta'),
        levelname=dict(bold=True),
        name=dict(color='blue'),
        programname=dict(color='cyan'),
        username=dict(color='yellow'),
        lineno=dict(color='yellow'),
    )
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path) as f:
            try:
                config = yaml.load(f, Loader=yaml.FullLoader)
                logging.config.dictConfig(config)
                coloredlogs.DEFAULT_FIELD_STYLES = DEFAULT_FIELD_STYLES
                coloredlogs.install(fmt="[%(asctime)s] %(levelname)-10s  %(message)-70s %(filename)s "
                                        "[LINE:%(lineno)d]")
            except Exception as e:
                print(e)
                print('Error in Logging Configuration. Using default configs')
                logging.basicConfig(level=default_level)
                coloredlogs.install(level=default_level)
    else:
        logging.basicConfig(level=default_level)
        coloredlogs.install(level=default_level)
        print('Failed to load configuration file. Using default configs')
    return logging.getLogger()


logger = setup_logging()
