# This file is part of the TEMAimaging project.
# Copyright (c) 2020, ETH Zurich
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

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
