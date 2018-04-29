from ruamel.yaml import YAML


class SettingsManager:
    def __init__(self):
        self.configuration_data = dict()

        self.yaml = YAML()

        self.load()

    def load(self):
        with open('settings.yml', 'r') as file:
            self.configuration_data = self.yaml.load(file)

    def save(self):
        with open('settings.yml', 'w') as file:
            self.yaml.dump(self.configuration_data, file)

    def __getitem__(self, item):
        return self.configuration_data.__getitem__(item)

    def __setitem__(self, key, value):
        self.configuration_data.__setitem__(key, value)

    def get(self, key):
        curr = self.configuration_data

        for chunk in key.split('.'):
            try:
                curr = curr[chunk]
            except KeyError:
                raise KeyError('Config entry with key "{}" not found'.format(key))

        return curr

    def set(self, key, value):
        curr = self.configuration_data
        chunks = key.split('.')

        for chunk in chunks[:-1]:
            try:
                curr = curr[chunk]
            except KeyError:
                raise KeyError('Config entry with key "{}" not found'.format(key))

        try:
            curr[chunks[-1]] = value
        except KeyError:
            raise KeyError('Config entry with key "{}" not found'.format(key))


Settings = SettingsManager()
