import argparse
import json
import logging
import shutil
from logging.handlers import RotatingFileHandler
import os

from telegram import Bot

from eazebot.auxiliary_methods import TelegramHandler

log_file_name = 'telegramEazeBot'


def check_dir_arg(folder):
    if not os.path.isdir(folder):
        raise NotADirectoryError(f"Argument '{folder}' is no known directory.")
    return os.path.abspath(folder)


# execute main if running as script
def main(sysargv = None):
    log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    logger = logging.getLogger('eazebot')
    logger.handlers = []  # delete old handlers in case bot is restarted but not python kernel
    logger.setLevel('INFO')  # DEBUG
    file_handler = RotatingFileHandler("{0}/{1}.log".format(os.getcwd(), log_file_name),
                                       maxBytes=1000000,
                                       backupCount=5)
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)

    # execute main if running as script
    parser = argparse.ArgumentParser(description='Processes input to eazebot main function.')
    parser.add_argument('-i', '--init', dest='init', action='store_true', required=False,
                        help='copies the necessary user config files to the current directory')
    parser.add_argument('-c', '--config', dest='config', action='store_true', required=False,
                        help='calls a dialog to fill out the configs interactively')
    parser.add_argument('-n', '--no-warning', dest='warning', action='store_false', required=False,
                        help='does not warn for preexisting config files when running the --init flag')
    parser.add_argument('-d', '--user-dir', dest='user_dir', default=None, type=check_dir_arg, required=False,
                        help="Absolute or relative path to the user folder")

    parser.parse_args('-ic'.split())

    args = parser.parse_args(sysargv)

    # change current path to user directory if argument exists
    if args.user_dir is not None:
        os.chdir(args.user_dir)

    if args.init:
        from eazebot.auxiliary_methods import copy_init_files
        copy_init_files(warning=args.warning)
    elif args.config:
        from eazebot.auxiliary_methods import start_config_dialog
        start_config_dialog()
    else:
        from eazebot.bot import EazeBot

        # load bot configuration
        if not os.path.isfile(os.path.join('user_data', "botConfig.json")):
            if os.path.isfile("botConfig.json"):
                # backward compatibility movement of files to user folder
                logger.info('Found user files in main folder. Moving them to new "user_data" folder')
                if not os.path.isdir('user_data'):
                    os.mkdir('user_data')
                for file in ["botConfig.json", "APIs.json", 'data.pickle', 'data.bkp', 'backup']:
                    if os.path.isfile(file) or os.path.isdir(file):
                        shutil.move(file, 'user_data')
            else:
                raise FileNotFoundError(
                    f"Json files not found in path {os.getcwd()}! Probably you did not initalize the config"
                    f"files with command 'python -m eazebot --init'")
        with open(os.path.join('user_data', "botConfig.json"), "r") as fin:
            config = json.load(fin)
        if isinstance(config['telegramUserId'], str) or isinstance(config['telegramUserId'], int):
            if config['telegramUserId'] == 'PLACEHOLDER':
                raise ValueError('Json files are not configured yet, please configurate them with '
                                 '"python -m eazebot --config"')
            config['telegramUserId'] = [int(config['telegramUserId'])]
        elif isinstance(config['telegramUserId'], list):
            config['telegramUserId'] = [int(val) for val in config['telegramUserId']]
        if isinstance(config['updateInterval'], str):
            config['updateInterval'] = int(config['updateInterval'])
        if 'minBalanceInBTC' not in config:
            config['minBalanceInBTC'] = 0.001
        if isinstance(config['minBalanceInBTC'], str):
            config['minBalanceInBTC'] = float(config['minBalanceInBTC'])
        if 'debug' not in config:
            config['debug'] = False
        if isinstance(config['debug'], str):
            config['debug'] = bool(int(config['debug']))
        if 'extraBackupInterval' not in config:
            config['extraBackupInterval'] = 7
        if 'maxBackupFileCount' not in config:
            config['maxBackupFileCount'] = 12

        telegram_handler = TelegramHandler(Bot(token=config['telegramAPI']), level='INFO')
        telegram_handler.setFormatter(logging.Formatter("%(levelname)s:  %(message)s"))
        logger.addHandler(telegram_handler)

        EazeBot(config=config).start_bot()


if __name__ == '__main__':
    main()
