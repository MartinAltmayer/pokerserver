
class ServerConfig:
    config = {}

    @classmethod
    def set(cls, **config):
        cls.config = config

    @classmethod
    def get(cls, key):
        return cls.config.get(key)

    @classmethod
    def clear(cls):
        cls.config = {}
