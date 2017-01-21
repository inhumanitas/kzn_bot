# coding=utf-8
import logging

import os
import telebot

from kzn_bot.sites import (
    Kzn, presets, UserSearchData, Filters, user_filters_cache)

logger = logging.getLogger(__name__)

BOT = GOD = None

MARKUP_HIDE = telebot.types.ReplyKeyboardRemove()


def initialize_bot(token_path):
    if not os.path.exists(token_path):
        raise ValueError('No token file found! get token from bot father')

    with open(token_path) as fh:
        bot_father_token = fh.readline().strip()
        god = fh.readline().strip()

    if BOT:
        try:
            BOT.stop_polling()
        except Exception as e:
            logger.exception(e)

    bot = telebot.TeleBot(bot_father_token, threaded=False)

    @bot.message_handler(commands=Filters.keys)
    def number_command(message):
        @user_filters_cache.filter_saver
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
    @user_filters_cache.filter_saver
    def start_command(message):
        user_filters_cache.clear(message.chat.id)
        logger.debug(
            'New user %d : %s' % (message.chat.id, message.chat.first_name))
        BOT.send_message(message.chat.id,
                         u'Сейчас пришлю последние 10 документов')
        if GOD:
            BOT.send_message(
                GOD,
                u'New user {0}, {1}'.format(message.chat.first_name,
                                            unicode(message.chat.id)))

    @bot.message_handler(commands=['clear'])
    @user_filters_cache.filter_saver
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
    @user_filters_cache.filter_saver
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
        @user_filters_cache.filter_saver
        def callback(msg):
            filter_name = msg.text
            if filter_name in presets:
                user_id = msg.chat.id
                user_filters_cache.add(user_id, **presets[filter_name])

                user_msg = u'Фильтр добавлен: {0}'.format(filter_name)
            else:
                user_msg = u'Неверно задан фильтр: {0}'.format(filter_name)

            markup_hide = MARKUP_HIDE
            BOT.send_message(message.chat.id, user_msg,
                             reply_markup=markup_hide)
            logger.debug(user_msg + u' ' + msg.chat.first_name)
            if GOD:
                BOT.send_message(GOD, user_msg + u' ' + msg.chat.first_name)

        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True,
                                                   selective=True)
        markup.row(*presets.keys())

        msg = BOT.send_message(message.chat.id, u"Выберите фильтр",
                               reply_markup=markup)

        BOT.register_next_step_handler(msg, callback)

    return bot, god


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
            emergency_message(unicode(user_id)+u' '+unicode(e),
                              'unrecognized error')

        else:
            logger.debug('user "%s" got message: %s' % (user_id, msg))
