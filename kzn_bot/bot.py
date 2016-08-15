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

bot = telebot.AsyncTeleBot(bot_father_token)


class Filters(object):
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
        params = u';'.join(
            unicode(k)+u'='+unicode(getattr(self, k, u'')) for k in self.keys)
        return u'Filters('+params+u')'

    def to_dict(self):
        return {k: getattr(self, k) for k in self.keys}

    def update(self, **kwargs):
        for key in kwargs:
            if key in self.keys:
                setattr(self, key, kwargs[key])


class UserSearchData(object):
    _data = {
        # user_id : Filters object
    }

    def __getitem__(self, item):
        return self._data.get(item, Filters())

    def __setitem__(self, key, value):
        self._data[key] = value

    def clear(self, user_id):
        self._data[user_id] = Filters()

    def get_all(self):
        return self._data


class Kzn(object):
    index = 'http://docs.kzn.ru'
    search_str = '/ru/documents?utf8=%E2%9C%93'
    filter_template = '&search_document_type%5B{param}%5D={value}'
    signed_after_date_fmt = 'd.m.Y'  # 16.08.2016

    xpath = '//div[@class="search-result-item"]/a'
    _data = {}

    @classmethod
    def get_url(cls, **kwargs):
        search_str = cls.search_str
        for param in Filters.keys:
            value = kwargs.get(param, '')
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
            url = cls.index + doc.get('href')
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
        cached_user_filter = user_filters_cache[message.chat.id]
        cached_user_filter.update(**{key: message.text})

    key = message.text.strip('/')
    bot.send_message(message.chat.id,
                     Filters.description.get(key, u'Не распознанная команда'))

    callback_fn = lambda msg: handler(msg, key)
    bot.register_next_step_handler(message, callback_fn)


@bot.message_handler(commands=['clear_filters'])
def number_command(message):
    user_filters_cache.clear(message.chat.id)


@bot.message_handler(commands=['please'])
def number_command(message):
    user_filters_cache[message.chat.id] = Filters()


def main():
    print 'Starting bot'

    polling = threading.Thread(target=bot.polling)
    polling.start()

    while True:
        print 'user_filters_cache', user_filters_cache.get_all()
        # send data to all subscribers
        for user_id in user_filters_cache.get_all():
            user_filter = user_filters_cache[user_id]
            data = Kzn.get_new_doc(**user_filter.to_dict())
            for url, title in data:
                bot.send_message(user_id, title)
        sleep(10)


if __name__ == '__main__':
    main()
