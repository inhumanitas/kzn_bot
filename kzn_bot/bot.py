# coding=utf-8

import os
import threading
from time import sleep

import requests
import telebot

from lxml import html


token_path = 'token'
if not os.path.exists(token_path):
    raise ValueError('No token file found! get token from bot father')

bot_father_token = open('token').readline().strip()

bot = telebot.TeleBot(bot_father_token)

GET_DATA_INTERVAL = 10


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

    def __getitem__(self, item):
        return self._data.get(item, [])

    def __setitem__(self, key, value):
        self._data[key] = value

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


class Kzn(object):
    index = u'http://docs.kzn.ru'
    search_str = u'/ru/documents?utf8=%E2%9C%93'
    filter_template = u'&search_document_type%5B{param}%5D={value}'
    # signed_after_date_fmt = 'd.m.Y'  # 16.08.2016

    xpath = u'//div[@class="search-result-item"]/a'
    _data = {}

    @classmethod
    def get_url(cls, **kwargs):
        search_str = cls.search_str
        for param in Filters.keys:
            value = kwargs.get(param, u'')
            search_str += cls.filter_template.format(param=param, value=value)

        return cls.index + search_str

    @classmethod
    def get_documents(cls, **kwargs):
        page = requests.get(cls.get_url(**kwargs))
        documents = []
        if page.status_code == 200:
            index_html = html.fromstring(page.text)
            documents = index_html.xpath(cls.xpath)

        for doc in documents:
            url = cls.index + doc.get(u'href')
            title = doc.text_content()
            yield url, title

    @classmethod
    def get_new_doc(cls, **kwargs):
        for url, title in cls.get_documents(**kwargs):
            if url in cls._data:
                continue

            cls._data[url] = title
            yield url, title


user_filters_cache = UserSearchData()


@bot.message_handler(commands=Filters.keys)
def number_command(message):
    def handler(message, key):
        user_id = message.chat.id
        value = message.text[:Filters.max_value_len]
        print(u'New key filter for user {u}: {k}={v}'.format(
            k=key, v=value, u=message.chat.first_name))

        filters = user_filters_cache[user_id]
        if filters:
            cached_user_filter = user_filters_cache.get_last(user_id)
            cached_user_filter.update(**{key: value})
        else:
            user_filters_cache.add(user_id, **{key: value})

    key = message.text.strip(u'/')
    bot.send_message(message.chat.id,
                     Filters.description.get(key, u'Не распознанная команда'))

    callback_fn = lambda msg: handler(msg, key)
    bot.register_next_step_handler(message, callback_fn)


@bot.message_handler(commands=['start'])
def start_command(message):
    user_filters_cache.clear(message.chat.id)
    bot.send_message(message.chat.id, u'Сейчас пришлю последние 10 документов')


@bot.message_handler(commands=['clear'])
def clear_command(message):
    e = "Нет фильтрации"
    user_filters_cache.clear(message.chat.id)
    bot.send_message(message.chat.id,
                     str(user_filters_cache[message.chat.id]) or e)


@bot.message_handler(commands=['list'])
def list_command(message):
    e = "Нет фильтрации"
    bot.send_message(message.chat.id,
                     str(user_filters_cache[message.chat.id]) or e)


@bot.message_handler(commands=['add'])
def add_command(message):
    if len(user_filters_cache[message.chat.id]) >= UserSearchData.max_filters:
        bot.send_message(
            message.chat.id,
            u'Достигнуто максимально допустимое количество '
            u'фильтров: %d' % UserSearchData.max_filters)
    else:
        user_filters_cache.add(message.chat.id)
        bot.send_message(message.chat.id,
                         str(user_filters_cache[message.chat.id]))


def send_data(user_id, **kwargs):
    data = Kzn.get_new_doc(**kwargs)
    for url, title in data:
        msg = title.replace(u'\n', u' ').strip() + u'\n' + url
        bot.send_message(user_id, msg)


def main():
    print(u'Starting bot')

    polling = threading.Thread(target=bot.polling)
    polling.start()

    while True:
        print('user_filters_cache', user_filters_cache.get_all())
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
    main()
