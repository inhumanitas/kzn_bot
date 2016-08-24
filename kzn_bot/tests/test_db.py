# coding: utf-8

import unittest

from kzn_bot.bot import Kzn
from kzn_bot.storages import prepare_db, con, KznData


class TestKzn(unittest.TestCase):
    def setUp(self):
        prepare_db()

    def tearDown(self):
        super(TestKzn, self).tearDown()
        con.cursor().execute('DROP TABLE {0}'.format(KznData.table_name))

    def test_document_append(self):
        user_id = 1
        key = 1001
        title = (u"Распоряжение Мэра г.Казани от 02.08.2016 №577р "
                 u"«О поощрении Благодарностями Мэра Казани»    02.08.2016 "
                 u"№ 577р")

        Kzn.append_data_by_user(user_id, key, title)
        # TODO assert get_one

    def test_document_sent(self):
        user_id = 1
        key = 1001
        title = (u"Распоряжение Мэра г.Казани от 02.08.2016 №577р "
                 u"«О поощрении Благодарностями Мэра Казани»    02.08.2016 "
                 u"№ 577р")

        Kzn.append_data_by_user(user_id, key, title)

        self.assertTrue(Kzn.document_sent(user_id, key))

    def test_document_not_sent(self):
        user_id = 1
        key = 666

        self.assertFalse(Kzn.document_sent(user_id, key))

    def test_document_append_uniqueness(self):
        user_id = 1
        key = 1001
        title = (u"Распоряжение Мэра г.Казани от 02.08.2016 №577р "
                 u"«О поощрении Благодарностями Мэра Казани»    02.08.2016 "
                 u"№ 577р")

        Kzn.append_data_by_user(user_id, key, title)
        self.assertFalse(Kzn.append_data_by_user(user_id, key, title))
