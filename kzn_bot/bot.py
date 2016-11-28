# coding=utf-8
import json
import logging
import logging.config
import os
import threading

from time import sleep

import requests
import telebot
from telebot import types

from lxml import html


try:
    from kzn_bot import storages
except ImportError:
    import storages

logger = logging.getLogger(__name__)

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,  # this fixes the problem
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(levelname)s - File: %(filename)s - '
                      '%(funcName)s() - Line: %(lineno)d - %(message)s',
            'fmt': '%m/%d/%Y %H:%M:%S',
            'datefmt': '%m/%d/%Y %H:%M:%S'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'bot.log',
            'formatter': 'standard',
        },
    },
    'loggers': {
        __name__: {
            'handlers': ['default', 'file'],
            'level': 'DEBUG',
        }
    }
})

BOT = GOD = None

GET_DATA_INTERVAL = 7
filters_file_name = 'filters.json'


def initialize_bot(token_path):
    if not os.path.exists(token_path):
        raise ValueError('No token file found! get token from bot father')

    with open(token_path) as fh:
        bot_father_token = fh.readline().strip()
        god = fh.readline().strip()

    if BOT:
        try:
            BOT.stop_polling()
        except:
            pass

    bot = telebot.TeleBot(bot_father_token, threaded=False)

    @bot.message_handler(commands=Filters.keys)
    def number_command(message):
        @user_filters_cache.filter_saver(filters_file_name)
        def handler(message, key):
            user_id = message.chat.id
            value = message.text[:Filters.max_value_len]
            log_msg = u'New key filter for user {u}: {k}={v}'.format(
                k=key, v=value, u=message.chat.first_name)
            logger.info(log_msg)

            filters = user_filters_cache[user_id]
            if filters:
                cached_user_filter = user_filters_cache.get_last(user_id)
                cached_user_filter.update(**{key: value})
            else:
                user_filters_cache.add(user_id, **{key: value})

            if GOD:
                BOT.send_message(GOD, log_msg)
                BOT.send_message(GOD, '; '.join(
                    [str(k) for k in user_filters_cache._data.keys()]))

        key = message.text.strip(u'/')
        BOT.send_message(message.chat.id,
                         Filters.description.get(key,
                                                 u'Не распознанная команда'))

        callback_fn = lambda msg: handler(msg, key)
        BOT.register_next_step_handler(message, callback_fn)

    @bot.message_handler(commands=['start'])
    @user_filters_cache.filter_saver(filters_file_name)
    def start_command(message):
        user_filters_cache.clear(message.chat.id)
        logger.debug(
            'New user %d : %s' % (message.chat.id, message.chat.first_name))
        BOT.send_message(message.chat.id,
                         u'Сейчас пришлю последние 10 документов')
        if GOD:
            BOT.send_message(GOD,
                             u'New user {0}, {1}'.format(message.chat.first_name, unicode(message.chat.id)))

    @bot.message_handler(commands=['clear'])
    @user_filters_cache.filter_saver(filters_file_name)
    def clear_command(message):
        e = "Нет фильтрации"
        user_filters_cache.clear(message.chat.id)
        logger.debug('User cleared filters: %d' % message.chat.id)
        BOT.send_message(message.chat.id,
                         str(user_filters_cache[message.chat.id]) or e)

    @bot.message_handler(commands=['list'])
    def list_command(message):
        e = "Нет фильтрации"
        BOT.send_message(message.chat.id,
                         str(user_filters_cache[message.chat.id]) or e)
        logger.debug(str(message.chat.id) + ': ' +
                     str(user_filters_cache[message.chat.id]))

    @bot.message_handler(commands=['add'])
    @user_filters_cache.filter_saver(filters_file_name)
    def add_command(message):
        if len(user_filters_cache[message.chat.id]) >= UserSearchData.max_filters:
            msg = (u'Достигнуто максимально допустимое количество '
                   u'фильтров: %d' % UserSearchData.max_filters)
        else:
            user_filters_cache.add(message.chat.id)
            msg = str(user_filters_cache[message.chat.id])
        logger.debug(msg)
        BOT.send_message(message.chat.id, msg)

    @bot.message_handler(commands=['presets'])
    def presets_command(message):
        @user_filters_cache.filter_saver(filters_file_name)
        def callback(msg):
            filter_name = msg.text
            if filter_name in presets:
                user_id = msg.chat.id
                user_filters_cache.add(user_id, **presets[filter_name])

                user_msg = u'Фильтр добавлен: {0}'.format(filter_name)
            else:
                user_msg = u'Неверно задан фильтр: {0}'.format(filter_name)

            markup = types.ReplyKeyboardHide()
            BOT.send_message(message.chat.id, user_msg, reply_markup=markup)
            logger.debug(user_msg + u' ' + msg.chat.first_name)
            if GOD:
                BOT.send_message(GOD, user_msg + u' ' + msg.chat.first_name)

        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True,
                                           selective=True)
        markup.row(*presets.keys())

        msg = BOT.send_message(message.chat.id, u"Выберите фильтр",
                               reply_markup=markup)

        BOT.register_next_step_handler(msg, callback)

    return bot, god


class Filters(object):
    # filter value maximum length
    max_value_len = 100
    number = 'number'
    title = 'title'
    signed_after = 'signed_after'
    category_id = 'category_id'
    organization_id = 'organization_id'

    keys = [
        number,
        title,
        signed_after,
        category_id,
        organization_id,
    ]

    description = {
        number: u"Номер документа",
        title: u"Название документа",
        signed_after: u"Дата подписания документа(в формате 16.08.2016)",
        category_id: u"Вид документа",
        organization_id: u"Принявший орган",
    }

    def __init__(self, **kwargs):
        super(Filters, self).__init__()
        for key in self.keys:
            setattr(self, key, '')
        self.update(**kwargs)

    def __repr__(self):
        params = u'; '.join(
            unicode(k)+u'='+unicode(getattr(self, k, u''))
            for k in self.keys if getattr(self, k, None))
        return (u'Filters('+params+u')').encode('utf-8')

    def to_dict(self):
        return {k: getattr(self, k) for k in self.keys}

    def update(self, **kwargs):
        for key in kwargs:
            if key in self.keys:
                setattr(self, key, kwargs[key])


class UserSearchData(object):
    # max filters count per user
    max_filters = 5

    _data = {
        # user_id : Filter objects
    }

    def __init__(self, file_name=None):
        super(UserSearchData, self).__init__()
        if file_name:
            self.load_from_file(file_name)

    def __getitem__(self, item):
        return self._data.get(item, [])

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, item):
        return item in self._data

    def filter_saver(self, file_name):
        def wrapper(fn):
            def inner(*args, **kwargs):
                result = fn(*args, **kwargs)
                self.save_to_file(file_name)
                return result
            return inner
        return wrapper

    def clear(self, user_id):
        self._data[user_id] = []

    def add(self, user_id, **kwargs):
        try:
            self._data[user_id].append(Filters(**kwargs))
        except KeyError:
            self._data[user_id] = [Filters(**kwargs)]

    def get_all(self):
        return self._data

    def get_last(self, user_id):
        return self._data[user_id][-1]

    def save_to_file(self, file_name):
        raw_data = {
            k: map(Filters.to_dict, v) for k, v in self._data.items()
        }
        json_encoded = json.dumps(raw_data)
        with open(file_name, 'w') as fh:
            fh.write(json_encoded)

    def load_from_file(self, file_name):
        if os.path.exists(file_name):
            try:
                raw_data = json.load(open(file_name))
            except ValueError as e:
                logger.error(e)
            else:
                self._data = {
                    int(k): [Filters(**kw) for kw in v]
                    for k, v in raw_data.items()
                }


class Kzn(object):
    index = u'http://docs.kzn.ru'
    search_str = u'/ru/documents?utf8=%E2%9C%93'
    filter_template = u'&search_document_type%5B{param}%5D={value}'
    # signed_after_date_fmt = 'd.m.Y'  # 16.08.2016

    xpath = u'//div[@class="search-result-item"]/a'

    @classmethod
    def get_url(cls, **kwargs):
        search_str = cls.search_str
        for param in Filters.keys:
            value = kwargs.get(param, u'')
            search_str += cls.filter_template.format(param=param, value=value)

        return cls.index + search_str

    @classmethod
    def get_documents(cls, **kwargs):
        try:
            page = requests.get(cls.get_url(**kwargs))
        except Exception as e:
            logger.error(e)
            page = None

        documents = []
        if page and page.status_code == 200:
            index_html = html.fromstring(page.text)
            documents = index_html.xpath(cls.xpath)

        for doc in documents:
            url = cls.index + doc.get(u'href') + u'/print_file'
            title = doc.text_content()
            yield url, title

    @classmethod
    def get_new_doc(cls, user_id, **kwargs):
        for url, title in cls.get_documents(**kwargs):
            if cls.document_sent(user_id, url):
                continue

            cls.append_data_by_user(user_id, url, title)
            yield url, title

    @classmethod
    def append_data_by_user(cls, user_id, key, value):
        return storages.kzn_data.insert_one(user_id, key, value)

    @classmethod
    def document_sent(cls, user_id, key):
        """
        Cheks if document is already read by user
        :param user_id: user identifier
        :param key: uniq key for document
        :return: True if document present in storage
        """

        return storages.kzn_data.exists(user_id, key)


user_filters_cache = UserSearchData(filters_file_name)

presets = {
    # Name: Filter params
    u'Дорожные знаки': {
        'title': u'движения',
        'signed_after': '01.08.2016'},
    u'Градострой': {
        'title': u'градостроительных',
        'signed_after': '01.08.2016'},
}


def emergency_message(message, default=None):
    if not os.path.exists('token'):
        raise ValueError('No token file found! get token from bot father')

    with open('token') as fh:
        bot_father_token = fh.readline().strip()
        god = fh.readline().strip()

    if god:
        msg = message or default or 'Error occurred! Save the bot'
        try:
            bot = telebot.TeleBot(bot_father_token, threaded=False)
            bot.send_message(god, msg)

        except Exception as e:
            logger.critical(e)
    else:
        logger.critical('No god persists')


def send_data(user_id, **kwargs):
    for url, title in Kzn.get_new_doc(user_id, **kwargs):
        msg = title.replace(u'\n', u' ').strip() + u'\n' + url
        try:
            BOT.send_message(user_id, msg)
        except Exception as e:
            logger.critical(e)
            emergency_message(unicode(user_id)+u' '+unicode(e), 'unrecognized error')

        else:
            logger.debug('user "%s" got message: %s' % (user_id, msg))


def main():
    global BOT, GOD

    def run_telegram_bot():
        global BOT, GOD
        BOT, GOD = initialize_bot(token_path)

        polling = threading.Thread(target=BOT.polling,
                                   kwargs={'none_stop': True})
        polling.daemon = True
        polling.start()
        return polling

    storages.prepare_db()

    logger.info(u'Starting bot')
    token_path = 'token'

    bot_daemon = run_telegram_bot()

    if GOD:
        BOT.send_message(GOD, 'Started, users: ' + '; '.join(
            [str(k) for k in user_filters_cache._data.keys()]) or 'No users')

    while True:

        if not bot_daemon.is_alive():
            logger.error('Bot down')
            emergency_message('Bot down')
            bot_daemon = run_telegram_bot()

        # send data to all subscribers
        for user_id in user_filters_cache.get_all().copy():
            user_filters = user_filters_cache[user_id]
            if user_filters:
                for user_filter in user_filters:
                    send_data(user_id, **user_filter.to_dict())
            else:
                send_data(user_id)

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
            import traceback, sys
            etype, value, tb = sys.exc_info()
            lines = traceback.format_exception_only(etype, value)
            logger.critical('\n'.join(lines))
            emergency_message('\n'.join(lines))

        sleep(30)

    logger.info('exiting now')
