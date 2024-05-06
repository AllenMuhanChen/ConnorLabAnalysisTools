from __future__ import annotations

import ast
from collections import OrderedDict

import pandas as pd

from clat.compile.trial.trial_field import DatabaseField, FieldList
from clat.util.connection import Connection
from clat.util.time_util import When


class CachedDatabaseField(DatabaseField):
    """
    A DatabaseField that caches its value in the database so it can be used for analysis without need to refetch data or store in
    serialized intermediate format.

    Override get_cached_value and cache_value to change the caching logic.

    A subclass of a subclass of this class will still need to use super().get rather than
    super().get_and_cache() because the subclass will not have proper self.name (it is overriden).
    """

    def __init__(self, conn: Connection,
                 ):
        self.conn = conn
        super().__init__(conn, self.get_name())

    def get_cached_super(self, when: When, super_type: CachedDatabaseField, *args, **kwargs):
        # Dynamically get the superclass instance based on super_type
        # Dynamically create an instance of the specified superclass
        super_field = super_type(self.conn, *args, **kwargs)

        # Attempt to retrieve cached value
        cached_value = self._get_cached_value(super_field.get_name(), when)
        if cached_value is not None:
            return self.convert_from_string(cached_value)

        # Fetch data using the superclass's get method and cache it
        data = super_field.get(when)
        self._cache_value(super_field.get_name(), when, data)
        converted_value = self.convert_from_string(self._get_cached_value(super_field.get_name(), when))
        return converted_value

    def get_and_cache(self, name: str, when: When):
        cached_value = self._get_cached_value(name, when)
        if cached_value is not None:
            return self.convert_from_string(cached_value)

        data = self.get(when)
        self._cache_value(name, when, data)
        # return the cached value rather than raw value to ensure same data-types are returned for all calls
        cached_value = self._get_cached_value(name, when)
        return self.convert_from_string(cached_value)

    def convert_from_string(self, cached_value):
        try:
            return ast.literal_eval(cached_value)
        except ValueError:
            return cached_value

    def _get_cached_value(self, name: str, when: When):
        # Implement the logic to query the TrialFieldCache table
        # to retrieve the cached value, if it exists and is still valid.
        query = "SELECT value FROM TrialFieldCache WHERE name = %s AND start = %s AND stop = %s;"
        self.conn.execute(query, params=(name, int(when.start), int(when.stop)))
        result = self.conn.fetch_all()
        return result[0][0] if result else None

    def _cache_value(self, name: str, when: When, value):
        value = str(value)
        # Implement the logic to insert or update the cached value
        # in the TrialFieldCache table.
        query = """
        INSERT INTO TrialFieldCache (name, start, stop, value) 
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE value = %s;
        """
        self.conn.execute(query, params=(name, int(when.start), int(when.stop), value, value))

    def get_name(self):
        raise NotImplementedError("Subclasses must implement get_name")

class CachedFieldList(list[CachedDatabaseField]):
    def get_df(self):
        df = pd.DataFrame(columns=self.get_names())
        return df

    def get_names(self):
        return [field.get_name() for field in self]

    def to_data(self, trial_tstamps: list[When]) -> pd.DataFrame:
        return self._get_data_from_trials(trial_tstamps)

    def _get_data_from_trials(self, trial_tstamps: list[When]) -> pd.DataFrame:
        data = []
        for i, when in enumerate(trial_tstamps):
            print("working on " + str(i) + " out of " + str(len(trial_tstamps)))
            field_values = []
            for field in self:
                try:
                    field_values.append(field.get_and_cache(field.name, when))
                except Exception as e:
                    print(f"Error fetching {field.name} at {when} for trial {i}: {e}")
                    field_values.append(None)
            field_values.insert(0, when)
            names = self.get_names()
            names.insert(0, "TrialStartStop")
            new_row = OrderedDict(zip(names, field_values))
            data.append(new_row)

        return pd.DataFrame(data)


"""
CREATE TABLE `TrialFieldCache` (
  `name` varchar(255) NOT NULL,
  `start` bigint(20) NOT NULL,
  `stop` bigint(20) NOT NULL,
  `value` longtext,
  PRIMARY KEY (`name`,`start`,`stop`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1
"""
