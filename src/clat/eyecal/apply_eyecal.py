from tkinter import filedialog

from clat.eyecal.params import EyeCalibrationParameters
from clat.util.connection import Connection


def main():
    current_conn = Connection("allen_estimshape_train_231211")

    #Open a GUI window to select a file
    filename = filedialog.askopenfilename(initialdir = "/home/r2_allen/git/EStimShape/xper-train",title = "Select file")

    #Read the file as one big string
    with open(filename, 'r') as f:
        lines = f.readlines()

    string = ""
    for line in lines:
        string += line

    EyeCalibrationParameters.deserialize(string).write_params(current_conn)




if __name__ == '__main__':
    main()
