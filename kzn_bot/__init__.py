# coding=utf-8

import logging.config

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
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
        '': {
            'handlers': ['default', 'file'],
            'level': 'DEBUG',
        },
    }
})
