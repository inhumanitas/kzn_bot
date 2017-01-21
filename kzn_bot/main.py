# coding: utf-8

import logging
import threading
from time import sleep

from kzn_bot import storages, bot
from kzn_bot.sites import GET_DATA_INTERVAL, user_filters_cache

logger = logging.getLogger(__name__)


def main():

    def run_telegram_bot():
        bot.BOT, bot.GOD = bot.initialize_bot(token_path)

        polling = threading.Thread(target=bot.BOT.polling,
                                   kwargs={'none_stop': True})
        polling.daemon = True
        polling.start()
        return polling

    storages.prepare_db()
    user_filters_cache.load_from_file()

    logger.info(u'Starting bot')
    token_path = 'token'

    bot_daemon = run_telegram_bot()

    if bot.GOD:
        bot.BOT.send_message(
            bot.GOD,
            'Started, users: ' + '; '.join(
                [str(k) for k in user_filters_cache.get_all().keys()]
            ) or 'No users'
        )

    while True:

        if not bot_daemon.is_alive():
            logger.error('Bot down')
            bot.emergency_message('Bot down')
            bot_daemon = run_telegram_bot()

        # send data to all subscribers
        for user_id in user_filters_cache.get_all().copy():
            user_filters = user_filters_cache[user_id]
            if user_filters:
                for user_filter in user_filters:
                    bot.send_data(user_id, **user_filter.to_dict())
            else:
                bot.send_data(user_id)

        sleep(GET_DATA_INTERVAL)


if __name__ == '__main__':
    # serve forever
    while True:
        try:
            main()
        except KeyboardInterrupt as e:
            logger.critical(e)
            break

        except Exception as e:
            import traceback
            import sys
            etype, value, tb = sys.exc_info()
            lines = traceback.format_exception_only(etype, value)
            logger.critical('\n'.join(lines))
            bot.emergency_message('\n'.join(lines))

        sleep(30)

    logger.info('exiting now')
