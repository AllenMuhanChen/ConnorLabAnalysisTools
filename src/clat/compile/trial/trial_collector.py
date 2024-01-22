import numpy
import numpy as np
from clat.util import table_util
from clat.util import time_util
from clat.util.connection import Connection
from clat.util.time_util import When


class TrialCollector:
    """Class for collecting trials from the database based on trialStart and trialStop tstamps in BehMsg,
       and filtering types of trials (i.e. from different kinds of experiments)
       based on the msgs between trialStart and trialStop in BehMsg"""
    def __init__(self, conn: Connection, when: When = time_util.today()):
        self.conn = conn
        self.when = when
        # self.beh_msg = conn.get_beh_msg(when)
        # self.stim_spec = conn.get_stim_spec(when)
        # self.stim_obj_data = conn.get_stim_obj_data(when)

    def collect_trials(self):
        print("Collecting all trials")

        # SQL query to get all trial start timestamps
        query_trial_starts = """
        SELECT tstamp 
        FROM BehMsg 
        WHERE type = 'TrialStart'
        AND tstamp BETWEEN %s AND %s
        ORDER BY tstamp;
        """
        self.conn.execute(query_trial_starts, (self.when.start, self.when.stop))
        trial_starts = self.conn.fetch_all()
        trial_starts = [trial_start_tuple[0] for trial_start_tuple in trial_starts]

        # SQL query to get all trial stop timestamps
        query_trial_stops = """
        SELECT tstamp 
        FROM BehMsg 
        WHERE type = 'TrialStop'
        AND tstamp BETWEEN %s AND %s
        ORDER BY tstamp;
        """
        self.conn.execute(query_trial_stops, (self.when.start, self.when.stop))
        trial_stops = self.conn.fetch_all()
        trial_stops = [trial_stop_tuple[0] for trial_stop_tuple in trial_stops]

        trial_starts, trial_stops = self.sort_fix_bad_trials(trial_starts, trial_stops)
        return [time_util.When(trial_starts[i], trial_stops[i]) for i in
                range(min(len(trial_starts), len(trial_stops)))]

    def collect_choice_trials(self):
        all_trial_whens = self.collect_trials()
        print("Collecting choice trials")
        choice_trial_whens = []


        query = """
                SELECT tstamp
                FROM BehMsg 
                WHERE type = 'ChoiceSelectionSuccess' 
                AND tstamp BETWEEN %s AND %s;
                """
        self.conn.execute(query, (int(self.when.start), int(self.when.stop)))
        result = self.conn.fetch_all()
        choice_tstamps = [result_tuple[0] for result_tuple in result]

        # Check if any of the choice_tstamps are sandwiched between the trial start and stop times
        for when in all_trial_whens:
            for choice_tstamp in choice_tstamps:
                if when.start <= choice_tstamp <= when.stop:
                    choice_trial_whens.append(when)
                    break  # Once a choice_tstamp is found in a trial period, no need to check other choice_tstamps

        return choice_trial_whens

    def sort_fix_bad_trials(self, trial_starts, trial_stops):
        """Finds bad trials by sorting the trial start and stops by their time stamps
        in the same array. We should have start, stop, start, stop, ..., and so on.
        If there's a duplicate start (i.e start, start, stop): then we delete the earlier trial_start
        If there's a duplicate stop (i.e, start, stop, stop):  then we delete the later trial_stop
        """
        self.__ensure_ends_are_aligned(trial_starts, trial_stops)

        trial_starts_ids = ["trial_start" for trial_start in trial_starts]
        trial_stops_ids = ["trial_stop" for trial_stop in trial_stops]
        combined_ids = trial_starts_ids + trial_stops_ids
        combined_tstamps = numpy.append(trial_starts, trial_stops)
        combined = zip(combined_ids, combined_tstamps)
        combined_sorted = sorted(combined, key=lambda x: x[1])

        previous = 'trial_stop'
        to_remove = []
        for i, item in enumerate(combined_sorted):
            if item[0] == previous:
                if item[0] == 'trial_start':
                    to_remove.append(i - 1)  # remove earlier trial_start, since it's missing a trial_stop
                    print("removing duplicate trial_start")
                else:
                    print("Somehow we have two repeating stops!: " + str(i))
                    to_remove.append(i)
            previous = item[0]
        combined_sorted_removed = [item for i, item in enumerate(combined_sorted) if i in to_remove]
        combined_sorted = [item for i, item in enumerate(combined_sorted) if i not in to_remove]
        trial_starts = [item[1] for item in combined_sorted if item[0] == 'trial_start']
        trial_stops = [item[1] for item in combined_sorted if item[0] == 'trial_stop']
        return trial_starts, trial_stops

    def collect_calibration_trials(self):
        all_trial_times = self.collect_trials()
        calibration_trial_times = []

        for when in all_trial_times:
            # SQL query to check if there are any 'CalibrationPointSetup' messages during the trial
            query = """
                    SELECT COUNT(*) 
                    FROM BehMsg 
                    WHERE type = 'CalibrationPointSetup' 
                    AND tstamp BETWEEN %s AND %s;
                    """
            self.conn.execute(query, (int(when.start), int(when.stop)))
            result = self.conn.fetch_all()

            # If there are any 'CalibrationPointSetup' messages, add this trial to the list
            if result[0][0] > 0:
                when.start = int(when.start)
                when.stop = int(when.stop)
                calibration_trial_times.append(when)

        return calibration_trial_times

    def __ensure_ends_are_aligned(self, trial_starts, trial_stops):
        while trial_stops[0] < trial_starts[0]:
            trial_stops = trial_stops[1:]
        while trial_starts[-1] > trial_stops[-1]:
            trial_starts = trial_starts[:-1]
        return trial_starts, trial_stops

    def __ensure_balanced_trial_nums(self, trial_starts, trial_stops):
        while trial_starts.size != trial_stops.size:
            if trial_starts.size > trial_stops.size:
                diff_length = trial_starts.size - trial_stops.size
                try:
                    first_bad_trial = self.__get_first_bad_trial(trial_starts[:-diff_length], trial_stops)
                except:
                    first_bad_trial = self.__get_first_bad_trial(trial_starts[diff_length:], trial_stops)
                trial_starts = np.delete(trial_starts, first_bad_trial)
            else:
                diff_length = trial_stops.size - trial_starts.size
                try:
                    first_bad_trial = self.__get_first_bad_trial(trial_starts, trial_stops[:-diff_length])
                except:
                    first_bad_trial = self.__get_first_bad_trial(trial_starts, trial_stops[diff_length:])
                trial_stops = np.delete(trial_stops, first_bad_trial)
        return trial_starts, trial_stops

    def __remove_misaligned_trials(self, trial_starts, trial_stops):
        while not self.__trials_aligned(trial_starts, trial_stops):
            first_bad_trial = self.__get_first_bad_trial(trial_starts, trial_stops)
            trial_starts = np.delete(trial_starts, first_bad_trial)
            trial_stops = np.delete(trial_stops, first_bad_trial)
        return trial_starts, trial_stops

    def __get_first_bad_trial(self, trial_starts, trial_stops):
        bad_trials = np.array(trial_starts > trial_stops)
        first_bad_trial = [i for i, x in enumerate(bad_trials) if x][0]
        return first_bad_trial

    def __trials_aligned(self, trial_starts, trial_stops):
        actual_correctly_aligned = sum([True for i in range(len(trial_starts)) if (trial_starts[i] < trial_stops[i])])
        return actual_correctly_aligned == len(trial_starts)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    pass
