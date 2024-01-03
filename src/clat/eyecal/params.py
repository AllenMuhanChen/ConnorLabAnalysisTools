from typing import Tuple

from clat.util import time_util

from clat.util.connection import Connection


class EyeCalibrationParameters:
    def __init__(self, parameters=None):
        if parameters is None:
            self.parameters = [
                ('xper_right_iscan_mapping_algorithm_parameter', 3, None),
                ('xper_right_iscan_mapping_algorithm_parameter', 2, None),
                ('xper_right_iscan_mapping_algorithm_parameter', 1, None),
                ('xper_right_iscan_mapping_algorithm_parameter', 0, None),
                ('xper_left_iscan_mapping_algorithm_parameter', 0, None),
                ('xper_left_iscan_mapping_algorithm_parameter', 1, None),
                ('xper_left_iscan_mapping_algorithm_parameter', 2, None),
                ('xper_left_iscan_mapping_algorithm_parameter', 3, None),
                ('xper_right_iscan_eye_zero', 0, None),
                ('xper_right_iscan_eye_zero', 1, None),
                ('xper_left_iscan_eye_zero', 0, None),
                ('xper_left_iscan_eye_zero', 1, None)
            ]
        else:
            self.parameters = parameters

    @classmethod
    def read_params(cls, conn: Connection) -> 'EyeCalibrationParameters':
        temp_parameters = cls().parameters
        for i, (name, arr_ind, _) in enumerate(temp_parameters):
            query = "SELECT val FROM SystemVar WHERE name = %s AND arr_ind = %s order by tstamp desc limit 1"
            conn.execute(query, (name, arr_ind))
            result = conn.fetch_all()
            if result:
                temp_parameters[i] = (name, arr_ind, result[0][0])
        return cls(temp_parameters)

    @classmethod
    def clear_and_reset_eyecal(cls, conn: Connection) -> None:
        EyeCalibrationParameters._clear_eyecal(conn)

        # Insert new data
        insert_query = """
            INSERT INTO SystemVar (name, arr_ind, tstamp, val) VALUES
            ('xper_right_iscan_mapping_algorithm_parameter', 3, 1097000000000340, '1'),
            ('xper_right_iscan_mapping_algorithm_parameter', 2, 1097000000000340, '0'),
            ('xper_right_iscan_mapping_algorithm_parameter', 1, 1097000000000340, '0'),
            ('xper_right_iscan_mapping_algorithm_parameter', 0, 1097000000000340, '1'),
            ('xper_left_iscan_mapping_algorithm_parameter', 0, 1097000000000340, '1'),
            ('xper_left_iscan_mapping_algorithm_parameter', 1, 1097000000000340, '0'),
            ('xper_left_iscan_mapping_algorithm_parameter', 2, 1097000000000340, '0'),
            ('xper_left_iscan_mapping_algorithm_parameter', 3, 1097000000000340, '1'),
            ('xper_right_iscan_eye_zero', 0, 1097000000000320, '0'),
            ('xper_right_iscan_eye_zero', 1, 1097000000000320, '0'),
            ('xper_left_iscan_eye_zero', 0, 1097000000000320, '0'),
            ('xper_left_iscan_eye_zero', 1, 1097000000000320, '0')
        """
        conn.execute(insert_query)

    @classmethod
    def _clear_eyecal(cls, conn: Connection):
        # Clear existing data
        delete_queries = [
            "DELETE FROM SystemVar WHERE name = 'xper_left_iscan_eye_zero'",
            "DELETE FROM SystemVar WHERE name = 'xper_right_iscan_eye_zero'",
            "DELETE FROM SystemVar WHERE name = 'xper_left_iscan_mapping_algorithm_parameter'",
            "DELETE FROM SystemVar WHERE name = 'xper_right_iscan_mapping_algorithm_parameter'"
        ]
        for query in delete_queries:
            conn.execute(query)

    def write_params(self, conn: Connection, tstamp: int = time_util.now()) -> None:
        EyeCalibrationParameters._clear_eyecal(conn)

        query = "INSERT INTO SystemVar (name, arr_ind, tstamp, val) VALUES (%s, %s, %s, %s)"
        for name, arr_ind, val in self.parameters:
            conn.execute(query, (name, arr_ind, tstamp, val))

    def volt_to_degree(self, volts_left_right: Tuple[Tuple[float], Tuple[float]]) -> Tuple[Tuple[float, float], Tuple[float,float]]:
        # Retrieve calibration parameters for left eye
        Sxh_left = self._get_param_value('xper_left_iscan_mapping_algorithm_parameter', 0)
        Sxv_left = self._get_param_value('xper_left_iscan_mapping_algorithm_parameter', 1)
        Syh_left = self._get_param_value('xper_left_iscan_mapping_algorithm_parameter', 2)
        Syv_left = self._get_param_value('xper_left_iscan_mapping_algorithm_parameter', 3)

        # Retrieve calibration parameters for right eye
        Sxh_right = self._get_param_value('xper_right_iscan_mapping_algorithm_parameter', 0)
        Sxv_right = self._get_param_value('xper_right_iscan_mapping_algorithm_parameter', 1)
        Syh_right = self._get_param_value('xper_right_iscan_mapping_algorithm_parameter', 2)
        Syv_right = self._get_param_value('xper_right_iscan_mapping_algorithm_parameter', 3)

        # Retrieve eyeZero values for left and right eyes
        eyeZero_left_x = self._get_param_value('xper_left_iscan_eye_zero', 0)
        eyeZero_left_y = self._get_param_value('xper_left_iscan_eye_zero', 1)
        eyeZero_right_x = self._get_param_value('xper_right_iscan_eye_zero', 0)
        eyeZero_right_y = self._get_param_value('xper_right_iscan_eye_zero', 1)

        # Calculate degree for left eye
        left_volt_x, left_volt_y = volts_left_right[0]
        left_degree_y = ((left_volt_y - eyeZero_left_y) * Sxh_left - (left_volt_x - eyeZero_left_x) * Sxv_left) / (
                Syv_left * Sxh_left - Syh_left * Sxv_left)
        left_degree_x = ((left_volt_x - eyeZero_left_x) - left_degree_y * Syh_left) / Sxh_left

        # Calculate degree for right eye
        right_volt_x, right_volt_y = volts_left_right[1]
        right_degree_y = ((right_volt_y - eyeZero_right_y) * Sxh_right - (
                right_volt_x - eyeZero_right_x) * Sxv_right) / (Syv_right * Sxh_right - Syh_right * Sxv_right)
        right_degree_x = ((right_volt_x - eyeZero_right_x) - right_degree_y * Syh_right) / Sxh_right

        # Clamp values to a maximum of 90
        left_degree_x = min(left_degree_x, 90)
        left_degree_y = min(left_degree_y, 90)
        right_degree_x = min(right_degree_x, 90)
        right_degree_y = min(right_degree_y, 90)

        return (left_degree_x, left_degree_y), (right_degree_x, right_degree_y)

    def _get_param_value(self, name, arr_ind):
        for param_name, param_index, param_value in self.parameters:
            if param_name == name and param_index == arr_ind:
                return float(param_value)
        return None  # Or handle the case where the parameter is not found

    def serialize(self) -> str:
        """Serializes the parameters to a text string with each parameter on a new line."""
        serialized_data = '\n'.join([f"{name},{arr_ind},{val}" for name, arr_ind, val in self.parameters])
        return serialized_data

    @classmethod
    def deserialize(cls, serialized_data: str) -> 'EyeCalibrationParameters':
        """Deserializes the text string back into an EyeCalibrationParameters object."""
        parameters = []
        for param_str in serialized_data.strip().split('\n'):
            name, arr_ind, val = param_str.split(',')
            parameters.append((name, int(arr_ind), val))
        return cls(parameters)

    def __str__(self):
        return '\n'.join(f'Name: {name}, Arr_ind: {arr_ind}, Value: {val}' for name, arr_ind, val in self.parameters)
