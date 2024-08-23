import time

def follow(thefile):
    """
    Follows a file and yields new lines as they are added.
    """
    thefile.seek(0, 2)  # Go to the end of the file
    while True:
        line = thefile.readline()
        if not line:
            time.sleep(0.1)  # Sleep briefly
            continue
        yield line

if __name__ == "__main__":
    logfile_path = r"C:\Users\(YourNameHere)\AppData\Roaming\obs-studio\logs\select_from_here.txt"
    with open(logfile_path, "r") as logfile:
        loglines = follow(logfile)
        for line in loglines:
            print(line, end="")