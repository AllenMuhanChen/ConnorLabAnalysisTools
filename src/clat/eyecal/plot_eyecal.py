from __future__ import annotations

import numpy as np
import xmltodict

from clat.eyecal.params import EyeCalibrationParameters
from clat.util import time_util

from clat.compile.trial.trial_collector import TrialCollector
from clat.compile.trial.trial_field import DatabaseField, FieldList, get_data_from_trials
from clat.util.connection import Connection
from clat.util.time_util import When
from typing import Optional, Tuple, Any, List
from datetime import datetime
import matplotlib.pyplot as plt


def main():
    current_conn = Connection("allen_estimshape_train_231211")
    trial_collector = TrialCollector(conn=current_conn, when=time_util.days_ago(1))
    calibration_trial_times = trial_collector.collect_calibration_trials()
    calibration_trial_times = filter_messages_after_experiment_start(current_conn, calibration_trial_times)
    print("calibration_trial_times: " + str(calibration_trial_times))

    fields = FieldList()
    fields.append(CalibrationPointPositionField(current_conn))
    fields.append(SlideOnOffTimestampField(current_conn))
    fields.append(VoltsField(current_conn))
    fields.append(AverageVoltsField(current_conn))
    fields.append(DegreesField(current_conn))
    data = get_data_from_trials(fields, calibration_trial_times)

    plot_average_volts(data)



def filter_messages_after_experiment_start(conn, calibration_trial_times):
    # Find the timestamp of the most recent "ExperimentStart" message
    query = """
        SELECT MAX(tstamp) 
        FROM BehMsg 
        WHERE type = 'ExperimentStart'
    """
    conn.execute(query)
    experiment_start_timestamp = conn.fetch_all()[0][0]

    filtered_messages = []

    # Loop through each trial time range in calibration_trial_times
    for when in calibration_trial_times:
        # Ensure the trial is after the experiment start
        if when.start > experiment_start_timestamp:
            filtered_messages.append(when)

    return filtered_messages


def hash_tuple(t):
    """ Hash a tuple to a unique value """
    return hash(t)


def plot_average_volts(data):
    # Define five distinct colors
    colors = ['red', 'green', 'blue', 'yellow', 'purple']

    # Extracting data for average volts and degrees
    left_eye_avg_volts = data['AverageVoltsLeftRight'].apply(lambda x: x[0])
    right_eye_avg_volts = data['AverageVoltsLeftRight'].apply(lambda x: x[1])
    degrees_left_right = data['DegreesLeftRight']
    calibration_points = data['CalibrationPointPosition']

    # Assign colors to each unique calibration point
    unique_points = sorted(set(calibration_points))
    color_mapping = {point: colors[i] for i, point in enumerate(unique_points)}
    calibration_colors = calibration_points.map(color_mapping)

    # Create 2x2 subplots
    fig, axs = plt.subplots(2, 2, figsize=(15, 12))

    # Plot for left eye volts
    axs[0, 0].scatter([x[0] for x in left_eye_avg_volts], [y[1] for y in left_eye_avg_volts], c=calibration_colors)
    axs[0, 0].set_title('Average Volt Positions - Left Eye')
    axs[0, 0].set_xlabel('X Position')
    axs[0, 0].set_ylabel('Y Position')

    # Plot for right eye volts
    axs[0, 1].scatter([x[0] for x in right_eye_avg_volts], [y[1] for y in right_eye_avg_volts], c=calibration_colors)
    axs[0, 1].set_title('Average Volt Positions - Right Eye')
    axs[0, 1].set_xlabel('X Position')
    axs[0, 1].set_ylabel('Y Position')

    # Plot for left eye degrees
    degrees_left = [degree[0] for degree in degrees_left_right]
    axs[1, 0].scatter([x[0] for x in degrees_left], [y[1] for y in degrees_left], c=calibration_colors)
    axs[1, 0].set_title('Degree Positions - Left Eye')
    axs[1, 0].set_xlabel('X Position')
    axs[1, 0].set_ylabel('Y Position')

    # Plot for right eye degrees
    degrees_right = [degree[1] for degree in degrees_left_right]
    axs[1, 1].scatter([x[0] for x in degrees_right], [y[1] for y in degrees_right], c=calibration_colors)
    axs[1, 1].set_title('Degree Positions - Right Eye')
    axs[1, 1].set_xlabel('X Position')
    axs[1, 1].set_ylabel('Y Position')

    # Show plot
    plt.tight_layout()
    plt.show()

class CalibrationPointPositionField(DatabaseField):
    def __init__(self, conn, name: str = "CalibrationPointPosition"):
        super().__init__(conn, name)

    def get(self, when: When):
        return self.get_calibration_point_setup_msg(when.start, when.stop)

    def get_calibration_point_setup_msg(self, start_tstamp: datetime, end_tstamp: datetime) -> tuple[Any, Any]:
        query = """
            SELECT msg 
            FROM BehMsg 
            WHERE type = 'CalibrationPointSetup' 
            AND tstamp BETWEEN %s AND %s
        """
        params = (start_tstamp, end_tstamp)
        self.conn.execute(query, params)
        result = self.conn.fetch_all()
        msg = result[0][0] if result else None
        msg_dict = xmltodict.parse(msg)
        x = msg_dict['CalibrationPointSetupMessage']['fixationPosition']['x']
        y = msg_dict['CalibrationPointSetupMessage']['fixationPosition']['y']
        return (x, y)


class SlideOnOffTimestampField(DatabaseField):
    def __init__(self, conn, name: str = "SlideOnOffTimestamps"):
        super().__init__(conn, name)

    def get(self, when: When) -> Tuple[Optional[Any], Optional[Any]]:
        return self.get_slide_on_off_timestamps(when.start, when.stop)

    def get_slide_on_off_timestamps(self, start_tstamp: datetime, end_tstamp: datetime) -> Tuple[
        Optional[Any], Optional[Any]]:
        slide_on_query = """
            SELECT tstamp 
            FROM BehMsg 
            WHERE type = 'SlideOn' 
            AND tstamp BETWEEN %s AND %s
            ORDER BY tstamp ASC
            LIMIT 1
        """
        slide_off_query = """
            SELECT tstamp 
            FROM BehMsg 
            WHERE type = 'SlideOff' 
            AND tstamp BETWEEN %s AND %s
            ORDER BY tstamp ASC
            LIMIT 1
        """

        # Execute the query for SlideOn
        params = (start_tstamp, end_tstamp)
        self.conn.execute(slide_on_query, params)
        result = self.conn.fetch_all()
        slide_on_timestamp = result[0][0] if result else None

        # Execute the query for SlideOff
        self.conn.execute(slide_off_query, params)
        result = self.conn.fetch_all()
        slide_off_timestamp = result[0][0] if result else None

        return slide_on_timestamp, slide_off_timestamp


class VoltsField(DatabaseField):
    def __init__(self, conn, name: str = "VoltsLeftRight"):
        super().__init__(conn, name)

    def get(self, when: When) -> Tuple[
        List[Tuple[float, float]], List[Tuple[float, float]]]:
        return self.get_eye_device_messages(when.start, when.stop)

    def get_eye_device_messages(self, start_tstamp: datetime, end_tstamp: datetime) -> Tuple[
        List[Tuple[float, float]], List[Tuple[float, float]]]:
        query = """
            SELECT msg 
            FROM BehMsgEye 
            WHERE type = 'EyeDeviceMessage' 
            AND tstamp BETWEEN %s AND %s
        """
        params = (start_tstamp, end_tstamp)
        self.conn.execute(query, params)
        results = self.conn.fetch_all()

        left_eye_positions = []
        right_eye_positions = []

        for row in results:
            msg = row[0]
            msg_dict = xmltodict.parse(msg)
            eye_id = msg_dict['EyeDeviceMessage']['id']
            volt_x = float(msg_dict['EyeDeviceMessage']['volt']['x'])
            volt_y = float(msg_dict['EyeDeviceMessage']['volt']['y'])

            if eye_id == 'leftIscan':
                left_eye_positions.append((volt_x, volt_y))
            elif eye_id == 'rightIscan':
                right_eye_positions.append((volt_x, volt_y))

        return left_eye_positions, right_eye_positions


class AverageVoltsField(VoltsField):
    def __init__(self, conn, name: str = "AverageVoltsLeftRight"):
        super().__init__(conn, name)

    def get(self, when: When) -> Tuple[Optional[Tuple[float, float]], Optional[Tuple[float, float]]]:
        left_eye_positions, right_eye_positions = super().get(when)
        left_eye_positions_filtered = self.remove_outliers(left_eye_positions)
        right_eye_positions_filtered = self.remove_outliers(right_eye_positions)
        return self.calculate_average(left_eye_positions_filtered), self.calculate_average(right_eye_positions_filtered)

    @staticmethod
    def calculate_average(positions: List[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
        if not positions:
            return None

        sum_x = sum(pos[0] for pos in positions)
        sum_y = sum(pos[1] for pos in positions)
        count = len(positions)

        return sum_x / count, sum_y / count

    @staticmethod
    def remove_outliers(positions: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if not positions:
            return []

        # Flatten the list of tuples and separate into x and y components
        x_vals, y_vals = zip(*positions)
        x_vals_filtered = AverageVoltsField.filter_outlier_values(x_vals)
        y_vals_filtered = AverageVoltsField.filter_outlier_values(y_vals)

        # Reconstruct the list of tuples with filtered values
        return list(zip(x_vals_filtered, y_vals_filtered))

    @staticmethod
    def filter_outlier_values(values):
        data = np.array(values)
        median = np.percentile(data, 50)
        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1
        lower_bound = median - 1.5 * iqr
        upper_bound = median + 1.5 * iqr
        return data[(data >= lower_bound) & (data <= upper_bound)]


class DegreesField(AverageVoltsField):
    def __init__(self, conn, name: str = "DegreesLeftRight"):
        super().__init__(conn, name)

    def get(self, when: When):
        params = EyeCalibrationParameters.read_params(self.conn)
        left_eye_positions, right_eye_positions = super().get(when)
        return params.volt_to_degree((left_eye_positions, right_eye_positions))

if __name__ == '__main__':
    main()
