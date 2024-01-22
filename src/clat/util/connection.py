import datetime
import threading
from time import sleep

import mysql.connector
import pandas as pd
from clat.util.time_util import When, to_unix


class Connection:

    def __init__(self, database, user="xper_rw", password="up2nite", host="172.30.6.80"):
        self.database = database
        self.user=user
        self.password = password
        self.host = host
        self._connect()
        self.lock = threading.Lock()

    def _connect(self):
        self.my_cursor = None
        self.mydb = mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database,
            autocommit=True
        )

    def execute(self, statement, params=()):
        with self.lock:
            try:
                try:
                    self.my_cursor.fetchall()
                    self.my_cursor.close()
                except:
                    pass
                self.my_cursor = self.mydb.cursor()
            except mysql.connector.errors.OperationalError as e:
                sleep(1)
                self._connect()
                self.my_cursor = self.mydb.cursor()
            self.my_cursor.execute(statement, params)

            has_results = self.my_cursor.description is not None
            if not has_results:
                self.mydb.commit()
                self.my_cursor.close()

    def truncate(self, table_name):
        self.execute(f"TRUNCATE TABLE {table_name}")

    def fetch_one(self):
        with self.lock:
            result = None
            try:
                result = self.my_cursor.fetchone()
            except mysql.connector.errors.InternalError as e:
                if "Unread result found" in str(e):
                    self.my_cursor.fetchall()
                    result = self.my_cursor.fetchone()
            if result:
                return result[0]
            else:
                return None

    def fetch_all(self):
        with self.lock:
            result = self.my_cursor.fetchall()
            # self.my_cursor.fetchall()
            self.my_cursor.close()
            return result

    def get_beh_msg(self, when: When) -> pd.DataFrame:
        try:
            self.execute("SELECT * FROM BehMsg WHERE tstamp>= %s && tstamp<=%s", (when.start, when.stop))
            df = pd.DataFrame(self.fetch_all())
            df.columns = ['tstamp', 'type', 'msg']
        except ValueError as e:
            print("Error: BehMsg empty for time: " + str(when))
            raise ValueError
        return df

    def get_stim_spec(self, when: When) -> pd.DataFrame:
        self.execute("SELECT * FROM StimSpec WHERE id>= %s & id<=%s", (when.start, when.stop))
        df = pd.DataFrame(self.fetch_all())
        df.columns = ['id', 'spec', 'util']
        return df

    def get_stim_obj_data(self, when: When) -> pd.DataFrame:
        try:
            self.execute("SELECT * FROM StimObjData WHERE id>= %s & id<=%s", (when.start, when.stop))
            df = pd.DataFrame(self.fetch_all())
            df.columns = ['id', 'spec', 'util']
            return df
        except:
            return None

    def get_beh_msg_eye(self, when: When) -> pd.DataFrame:
        self.execute("SELECT * FROM BehMsgEye WHERE tstamp>= %s & tstamp<=%s", (when.start, when.stop))
        df = pd.DataFrame(self.fetch_all())
        df.columns = ['tstamp', 'type', 'msg']
        return df


def since_nth_most_recent_experiment(conn: Connection, n=1):
    """
    Get the start timestamp of the nth most recent experiment.

    Parameters:
    - conn: Connection object.
    - n: Specifies the nth most recent experiment. Defaults to 1 (most recent).

    Returns:
    - A When object representing the time range of the nth most recent experiment.
    """
    query = f"""
            SELECT tstamp 
            FROM BehMsg 
            WHERE type = 'ExperimentStart'
            ORDER BY tstamp DESC
            LIMIT 1 OFFSET {n - 1}
        """
    conn.execute(query)
    result = conn.fetch_all()

    if result:
        start = result[0][0]
    else:
        # Handle the case where there are less than n experiments
        raise ValueError(f"No data available for the {n}th most recent experiment.")

    # Assuming 'to_unix' is a function to convert datetime to Unix timestamp
    end = to_unix(datetime.date.fromisoformat('3022-01-01'))
    return When(start, end)

