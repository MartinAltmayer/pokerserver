import logging

LOGGING = {
    'version': 1,
    'formatters': {
        'simple': {
            'format': '%(asctime)s %(name)s (%(levelname)s): %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': logging.DEBUG,
            'formatter': 'simple'
        }
    },
    'loggers': {
    },
    'root': {
        'level': logging.DEBUG,
        'handlers': ['console']
    },
    'disable_existing_loggers': False
}
