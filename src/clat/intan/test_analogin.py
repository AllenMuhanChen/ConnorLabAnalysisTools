from matplotlib import pyplot as plt

from clat.intan.analogin import read_analogin_file


def test_read_analogin_file():
    volts = read_analogin_file("/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/Test/2024-02-28/TestRecording_240228_152822/analogin.dat", 1)
    # Plotting the voltages
    plt.figure(figsize=(10, 6))  # Set the figure size
    plt.plot(volts[0], label='Channel 1 Voltage')  # Plot the voltages for channel 1
    plt.title('Voltage Readings from analogin.dat')
    plt.xlabel('Sample Number')
    plt.ylabel('Voltage (V)')
    plt.legend()
    plt.grid(True)  # Add grid for better readability
    plt.show()



