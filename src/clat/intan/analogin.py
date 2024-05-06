import numpy as np
import os


def read_analogin_file(filename, num_channels):
    """
    Reads ADC data from a file and converts it to volts.

    Args:
        filename (str): The path to the binary file containing ADC data.
        num_channels (int): The number of channels in the ADC data.

    Returns:
        np.ndarray: A 2D array containing the voltage data for each channel.
    """
    # Get the size of the file in bytes
    file_size = os.path.getsize(filename)

    # Calculate the number of samples per channel
    num_samples = file_size // (num_channels * 2)  # uint16 = 2 bytes

    # Read the binary data from the file
    with open(filename, 'rb') as f:
        data = np.fromfile(f, dtype=np.uint16, count=num_channels * num_samples)

    # Reshape the data into a 2D array [num_channels, num_samples]
    data = data.reshape((num_channels, num_samples))

    # Convert ADC values to volts
    volts = (data - 32768) * 0.0003125

    return volts
