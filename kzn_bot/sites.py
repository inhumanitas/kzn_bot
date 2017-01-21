# coding: utf-8

import json
import logging
import os
import requests
from lxml import html

from kzn_bot import storages

logger = logging.getLogger(__name__)


GET_DATA_INTERVAL = 7

presets = {
    # Name: Filter params
    u'Дорожные знаки': {
        'title': u'движения',
        'signed_after': '01.08.2016'},
    u'Градострой': {
        'title': u'градостроительных',
        'signed_after': '01.08.2016'},
}


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

    def __init__(self, file_name):
        super(UserSearchData, self).__init__()
        self._file_name = file_name

    def __getitem__(self, item):
        return self._data.get(item, [])

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, item):
        return item in self._data

    def filter_saver(self, fn):
        def inner(instance, *args, **kwargs):
            self.save_to_file()
            return fn(instance, *args, **kwargs)
        return inner

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

    def save_to_file(self):
        raw_data = {
            k: map(Filters.to_dict, v) for k, v in self._data.items()
        }
        json_encoded = json.dumps(raw_data)
        with open(self._file_name, 'w') as fh:
            fh.write(json_encoded)

    def load_from_file(self):
        if os.path.exists(self._file_name):
            try:
                raw_data = json.load(open(self._file_name))
            except (ValueError, IOError)as e:
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


filters_file_name = 'filters.json'
user_filters_cache = UserSearchData(filters_file_name)
