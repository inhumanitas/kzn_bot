# coding: utf-8

import sqlite3

con = sqlite3.connect('bot.db')

kzn_data = None


def prepare_db():
    global kzn_data
    kzn_data = KznData()


class KznData(object):
    table_name = 'KznData'

    def __init__(self):
        super(KznData, self).__init__()
        cur = con.cursor()
        # create the table
        cur.execute('''
        CREATE TABLE IF NOT EXISTS {table_name}(
            user_id INT, key INT, title TEXT,
            UNIQUE (user_id, key)
        );
        '''.format(
            table_name=self.table_name,
        ))
        con.commit()

    def exists(self, user_id, key):
        cur = con.cursor()
        sql = "SELECT count(*) FROM {table} WHERE user_id=? AND key=?".format(
            table=self.table_name)

        cur.execute(sql, (user_id, key))
        (number_of_rows,) = cur.fetchone()
        return bool(number_of_rows)

    def insert_one(self, user_id, key, title):
        cur = con.cursor()
        insert_sql = '''INSERT INTO {table_name}
            (user_id, key, title)
            VALUES
            (?, ?, ?)'''.format(table_name=self.table_name)
        try:
            cur.execute(insert_sql, (user_id, key, title))
            con.commit()
        except sqlite3.IntegrityError:
            return False
        return True
