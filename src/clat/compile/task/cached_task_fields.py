import ast
from collections import OrderedDict
from typing import List

import pandas as pd

from clat.compile.task.task_field import TaskField, TaskFieldList, Task
from clat.util.connection import Connection


class CachedTaskField(TaskField):
    """
    A TaskField that caches its value to avoid refetching data for the same task_id.
    """

    def __init__(self, conn: Connection):
        super().__init__(self.get_name())
        self.conn = conn

    def get_and_cache(self, task_id: int):
        # Check for cached value
        cached_value = self._get_cached_value(task_id)
        if cached_value is not None:
            return self.convert_from_string(cached_value)

        # If no cached value, fetch the data and cache it
        data = self.get(task_id)
        self._cache_value(task_id, data)

        # Return the newly cached value to ensure consistency
        return self.convert_from_string(self._get_cached_value(task_id))

    def _get_cached_value(self, task_id: int):
        # Implement logic to query your caching mechanism for a cached value
        query = "SELECT value FROM TaskFieldCache WHERE task_id = %s;"
        self.conn.execute(query, params=(task_id,))
        result = self.conn.fetch_all()
        return result[0][0] if result else None

    def _cache_value(self, task_id: int, value):
        # Implement logic to insert or update a value in your caching mechanism
        value_str = str(value)
        query = """
        INSERT INTO TaskFieldCache (task_id, value) 
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE value = %s;
        """
        self.conn.execute(query, params=(task_id, value_str, value_str))

    def convert_from_string(self, cached_value):
        # Convert the string representation back to the original data type
        try:
            return ast.literal_eval(cached_value)
        except ValueError:
            return cached_value

    def get_name(self):
        raise NotImplementedError("Subclasses must implement get_name")


class CachedTaskFieldList(List[CachedTaskField]):
    def get_names(self):
        # This remains unchanged, leveraging the parent class's implementation
        return [field.get_name() for field in self]

    def to_data(self, task_ids: list[int]) -> pd.DataFrame:
        """
        Fetches and caches data for a list of task IDs, then constructs a DataFrame from the results.
        """
        data = []
        for task_id in task_ids:
            task_data = []
            for field in self:
                # Each field is responsible for its own caching logic
                field_data = field.get_and_cache(task_id)
                task_data.append(field_data)
            # Construct an OrderedDict to preserve column order
            row = OrderedDict(zip(self.get_names(), task_data))
            data.append(row)

        # Convert the list of OrderedDicts to a DataFrame
        return pd.DataFrame(data)


