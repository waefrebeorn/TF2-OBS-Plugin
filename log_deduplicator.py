import tkinter as tk
from tkinter import filedialog
import hashlib

def deduplicate_log(input_file, output_file):
    """
    Parses a large log file and removes duplicate lines.

    Args:
        input_file: Path to the input log file.
        output_file: Path to the output file where deduplicated data will be written.
    """
    seen_lines = set()

    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            # Calculate a hash of the line for efficient duplicate detection
            line_hash = hashlib.md5(line.encode()).hexdigest()
            if line_hash not in seen_lines:
                seen_lines.add(line_hash)
                outfile.write(line)

def browse_input_file():
    """
    Opens a file dialog to select the input log file.
    """
    file_path = filedialog.askopenfilename(
        title="Select Input Log File",
        filetypes=(("Log Files", "*.log"), ("All Files", "*.*"))
    )
    input_file_entry.delete(0, tk.END)
    input_file_entry.insert(0, file_path)

def browse_output_file():
    """
    Opens a file dialog to select the output file location.
    """
    file_path = filedialog.asksaveasfilename(
        title="Select Output File",
        defaultextension=".log",
        filetypes=(("Log Files", "*.log"), ("All Files", "*.*"))
    )
    output_file_entry.delete(0, tk.END)
    output_file_entry.insert(0, file_path)

def start_deduplication():
    """
    Triggers the deduplication process using the selected input and output files.
    """
    input_file = input_file_entry.get()
    output_file = output_file_entry.get()

    if input_file and output_file:
        deduplicate_log(input_file, output_file)
        status_label.config(text="Deduplication complete!")
    else:
        status_label.config(text="Please select both input and output files.")

# Create the main window
window = tk.Tk()
window.title("Log File Deduplicator")

# Input file selection
input_file_label = tk.Label(window, text="Input Log File:")
input_file_label.grid(row=0, column=0, padx=10, pady=10)
input_file_entry = tk.Entry(window, width=40)
input_file_entry.grid(row=0, column=1, padx=10, pady=10)
input_file_button = tk.Button(window, text="Browse", command=browse_input_file)
input_file_button.grid(row=0, column=2, padx=10, pady=10)

# Output file selection
output_file_label = tk.Label(window, text="Output File:")
output_file_label.grid(row=1, column=0, padx=10, pady=10)
output_file_entry = tk.Entry(window, width=40)
output_file_entry.grid(row=1, column=1, padx=10, pady=10)
output_file_button = tk.Button(window, text="Browse", command=browse_output_file)
output_file_button.grid(row=1, column=2, padx=10, pady=10)

# Start button
start_button = tk.Button(window, text="Start Deduplication", command=start_deduplication)
start_button.grid(row=2, column=0, columnspan=3, padx=10, pady=20)

# Status label
status_label = tk.Label(window, text="")
status_label.grid(row=3, column=0, columnspan=3, padx=10, pady=10)

window.mainloop()