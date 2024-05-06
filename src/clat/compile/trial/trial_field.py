from __future__ import annotations

from collections import OrderedDict

import pandas as pd

from clat.util.connection import Connection
from clat.util.time_util import When

"""
Handles compilation of data while using the timestamps of trialStart and trialStop
as the primary keys for the data.
"""
class Field:
    def __init__(self, name: str = None):
        if name is None:
            self.name = type(self).__name__
        else:
            self.name = name

    def get(self, when: When):
        raise NotImplementedError("Not Implemented")


class FieldList(list[Field]):
    """List of Field types"""

    def get_df(self):
        df = pd.DataFrame(columns=self.get_names())
        return df

    def get_names(self):
        return [field.name for field in self]

    def get_data(self, trial_tstamps: list[When]) -> pd.DataFrame:
        return self._get_data_from_trials(self, trial_tstamps)

    def _get_data_from_trials(self, fields: FieldList, trial_tstamps: list[When]) -> pd.DataFrame:
        data = []
        for i, when in enumerate(trial_tstamps):
            if i % 100 == 0:
                print("working on " + str(i) + " out of " + str(len(trial_tstamps)))
            field_values = [field.get(when) for field in fields]
            names = fields.get_names()
            new_row = OrderedDict(zip(names, field_values))
            data.append(new_row)

        return pd.DataFrame(data)


def get_data_from_trials(fields: FieldList, trial_tstamps: list[When]) -> pd.DataFrame:
    data = []
    for i, when in enumerate(trial_tstamps):
        if i % 100 == 0:
            print("working on " + str(i) + " out of " + str(len(trial_tstamps)))
        field_values = [field.get(when) for field in fields]
        names = fields.get_names()
        new_row = OrderedDict(zip(names, field_values))
        data.append(new_row)

    return pd.DataFrame(data)

class DatabaseField(Field):
    def __init__(self, conn: Connection, name: str = None):
        super().__init__(name)
        self.conn = conn

    def get(self, when: When):
        raise NotImplementedError("Not Implemented")



