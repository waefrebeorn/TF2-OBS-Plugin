import os
import time
import re
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import threading
import traceback
import websocket
import json
import base64
import hashlib
import queue
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger(__name__)

# Default values
default_tf2_path = "C:/Program Files (x86)/Steam/steamapps/common/Team Fortress 2/tf/console.log"
obs_host_default = "192.168.1.192"
obs_port_default = 4455
obs_password_default = "yourobspassword"
steam_username_default = "WaefreBeorn"
steam_id_default = "76561198027081583"

class OBSWebSocket:
    def __init__(self, host, port, password):
        self.host = host
        self.port = port
        self.password = password
        self.ws = None
        self.connected = False

    def connect(self):
        url = f"ws://{self.host}:{self.port}"
        self.ws = websocket.WebSocket()
        self.ws.connect(url)
        self._auth()
        self.connected = True

    def _build_auth_string(self, salt, challenge):
        secret = base64.b64encode(hashlib.sha256((self.password + salt).encode('utf-8')).digest())
        auth = base64.b64encode(hashlib.sha256(secret + challenge.encode('utf-8')).digest()).decode('utf-8')
        return auth

    def _auth(self):
        message = self.ws.recv()
        result = json.loads(message)
        auth = self._build_auth_string(result['d']['authentication']['salt'], result['d']['authentication']['challenge'])

        payload = {
            "op": 1,
            "d": {
                "rpcVersion": 1,
                "authentication": auth,
                "eventSubscriptions": 1000 
            }
        }
        self.ws.send(json.dumps(payload))
        message = self.ws.recv()
        # Assuming authentication was successful

    def send_request(self, request_type, request_data=None):
        if request_data is None:
            request_data = {}
        payload = {
            "op": 6,
            "d": {
                "requestId": f"{request_type}Request",
                "requestType": request_type,
                "requestData": request_data
            }
        }
        self.ws.send(json.dumps(payload))
        return json.loads(self.ws.recv())

    def set_current_scene(self, scene_name):
        return self.send_request("SetCurrentProgramScene", {"sceneName": scene_name})

    def set_scene_item_enabled(self, scene_name, source_name, enabled):
        return self.send_request("SetSceneItemEnabled", {
            "sceneName": scene_name,
            "sceneItemId": source_name,
            "sceneItemEnabled": enabled
        })

    def close(self):
        if self.ws:
            self.ws.close()
        self.connected = False

class TF2LogHandler(PatternMatchingEventHandler):
    def __init__(self, obs_client, log_file_path, player_name, debug_callback, stop_event):
        super().__init__(patterns=[log_file_path], ignore_directories=True, case_sensitive=False)
        self.obs_client = obs_client
        self.player_name = player_name
        self.debug_callback = debug_callback
        self.stop_event = stop_event
        self.log_file_path = log_file_path
        self.last_position = self.get_file_size(log_file_path)
        self.debug_callback(f"Starting to monitor from position: {self.last_position}")

    def get_file_size(self, file_path):
        try:
            return os.path.getsize(file_path)
        except OSError as e:
            self.debug_callback(f"Error getting file size: {e}")
            return 0

    def on_modified(self, event):
        # We don't need to do anything here, as check_file is called periodically
        pass

    def check_file(self):
        if self.stop_event.is_set():
            return
        self.debug_callback(f"Checking log file: {self.log_file_path}")
        try:
            current_size = self.get_file_size(self.log_file_path)
            if current_size > self.last_position:
                with open(self.log_file_path, 'r', encoding='utf-8', errors='replace') as log_file:
                    log_file.seek(self.last_position)
                    new_lines = log_file.readlines()
                    self.last_position = log_file.tell()
                    self.process_new_lines(new_lines)
            elif current_size < self.last_position:
                self.debug_callback("Log file size decreased. File might have been truncated or replaced.")
                self.last_position = 0
                self.check_file()  # Recheck the file from the beginning
        except Exception as e:
            self.debug_callback(f"Error reading log file: {e}")
            self.debug_callback(traceback.format_exc())
            
    def process_new_lines(self, lines):
        for line in lines:
            if self.stop_event.is_set():
                return
            self.debug_callback(f"New log line: {line.strip()}")

            # Check for kill events
            kill_event = re.search(r'(\w+) killed (\w+) with (\w+)\.', line)
            if kill_event:
                killer, victim, weapon = kill_event.groups()
                self.debug_callback(f"Kill event detected: {killer} killed {victim} with {weapon}")
                if killer == self.player_name:
                    self.debug_callback(f"Player {self.player_name} made a kill with {weapon}")
                    self.trigger_obs_effect("kill", weapon)
                elif victim == self.player_name:
                    self.debug_callback(f"Player {self.player_name} was killed by {weapon}")
                    self.trigger_obs_effect("death", weapon)

            # Check for suicide event
            suicide_event = re.search(r'(\w+) suicided\.', line)
            if suicide_event:
                player = suicide_event.group(1)
                self.debug_callback(f"Suicide event detected: {player} suicided")
                if player == self.player_name:
                    self.trigger_obs_effect("suicide")

    def trigger_obs_effect(self, event_type, weapon=None):
        if self.stop_event.is_set():
            return

        if not self.obs_client.connected:
            self.debug_callback("OBS is not connected yet. Skipping effect trigger.")
            return

        self.debug_callback(f"Triggering OBS effect: {event_type}" + (f" with {weapon}" if weapon else ""))
        try:
            if event_type == "kill":
                self.obs_client.set_current_scene("KillScene")
                self.obs_client.set_scene_item_enabled("KillScene", "KillOverlay", True)
                time.sleep(2)
                self.obs_client.set_scene_item_enabled("KillScene", "KillOverlay", False)
            elif event_type == "death":
                self.obs_client.set_current_scene("DeathScene")
                self.obs_client.set_scene_item_enabled("DeathScene", "DeathOverlay", True)
                time.sleep(2)
                self.obs_client.set_scene_item_enabled("DeathScene", "DeathOverlay", False)
            elif event_type == "suicide":
                self.obs_client.set_current_scene("SuicideScene")
                self.obs_client.set_scene_item_enabled("SuicideScene", "SuicideOverlay", True)
                time.sleep(2)
                self.obs_client.set_scene_item_enabled("SuicideScene", "SuicideOverlay", False)
            self.debug_callback(f"OBS effect for {event_type} triggered successfully")
            print(f"OBS effect for {event_type} triggered successfully!")
        except Exception as e:
            self.debug_callback(f"Failed to trigger OBS effect: {e}")
            self.debug_callback(traceback.format_exc())
            print(f"Failed to trigger OBS effect for {event_type}: {e}")

class TF2OBSPlugin:
    def __init__(self, root):
        self.root = root
        self.root.title("TF2 OBS Plugin Configuration")
        self.obs_client = None
        self.monitoring_thread = None
        self.stop_event = threading.Event()
        self.obs_connected = False

        self.create_widgets()
        self.debug_queue = queue.Queue()

    def create_widgets(self):
        # TF2 log file selection
        tk.Label(self.root, text="Select TF2 console.log File:").grid(row=0, column=0, padx=10, pady=10)
        self.tf2_dir_entry = tk.Entry(self.root, width=50)
        self.tf2_dir_entry.grid(row=0, column=1, padx=10, pady=10)
        self.tf2_dir_entry.insert(0, default_tf2_path)
        tk.Button(self.root, text="Browse", command=self.select_directory).grid(row=0, column=2, padx=10, pady=10)

        # Steam username
        tk.Label(self.root, text="Enter Your Steam Username:").grid(row=1, column=0, padx=10, pady=10)
        self.steam_username_entry = tk.Entry(self.root, width=50)
        self.steam_username_entry.grid(row=1, column=1, padx=10, pady=10)
        self.steam_username_entry.insert(0, steam_username_default)

        # Steam ID
        tk.Label(self.root, text="Enter Your SteamID64 (Dec):").grid(row=2, column=0, padx=10, pady=10)
        self.steam_id_entry = tk.Entry(self.root, width=50)
        self.steam_id_entry.grid(row=2, column=1, padx=10, pady=10)
        self.steam_id_entry.insert(0, steam_id_default)
        tk.Button(self.root, text="Find your Steam ID", command=self.open_steamid_finder).grid(row=2, column=2, padx=10, pady=10)

        # OBS connection details
        tk.Label(self.root, text="Enter OBS Host:").grid(row=3, column=0, padx=10, pady=10)
        self.obs_host_entry = tk.Entry(self.root, width=50)
        self.obs_host_entry.grid(row=3, column=1, padx=10, pady=10)
        self.obs_host_entry.insert(0, obs_host_default)

        tk.Label(self.root, text="Enter OBS Port:").grid(row=4, column=0, padx=10, pady=10)
        self.obs_port_entry = tk.Entry(self.root, width=50)
        self.obs_port_entry.grid(row=4, column=1, padx=10, pady=10)
        self.obs_port_entry.insert(0, obs_port_default)

        tk.Label(self.root, text="Enter OBS Password:").grid(row=5, column=0, padx=10, pady=10)
        self.obs_password_entry = tk.Entry(self.root, show='*', width=50)
        self.obs_password_entry.grid(row=5, column=1, padx=10, pady=10)
        self.obs_password_entry.insert(0, obs_password_default)

        # Connect with OBS button
        tk.Button(self.root, text="Connect with OBS", command=self.connect_obs).grid(row=6, column=0, columnspan=3, padx=10, pady=10)

        # OBS Info Button
        tk.Button(self.root, text="Show Setup Info", command=show_obs_info).grid(row=7, column=0, columnspan=3, padx=10, pady=10)

        # -condebug reminder
        condebug_text = "Remember to add -condebug to TF2 launch options!"
        tk.Label(self.root, text=condebug_text, fg="red", font=("Arial", 12, "bold")).grid(row=8, column=0, columnspan=3, padx=10, pady=10)

        # Debug output
        tk.Label(self.root, text="Debug Output:").grid(row=9, column=0, padx=10, pady=10)
        self.debug_output = scrolledtext.ScrolledText(self.root, width=70, height=10)
        self.debug_output.grid(row=10, column=0, columnspan=3, padx=10, pady=10)

        # Start monitoring button
        self.start_button = tk.Button(self.root, text="Start Monitoring", command=self.start_script)
        self.start_button.grid(row=11, column=0, columnspan=3, padx=10, pady=20)

        # Stop monitoring button
        self.stop_button = tk.Button(self.root, text="Stop Monitoring", command=self.stop_script, state=tk.DISABLED)
        self.stop_button.grid(row=12, column=0, columnspan=3, padx=10, pady=20)
        
    def select_directory(self):
        path = filedialog.askopenfilename(initialdir="/", title="Select TF2 console.log file",
                                          filetypes=(("Log files", "*.log"), ("All files", "*.*")))
        if path:
            self.tf2_dir_entry.delete(0, tk.END)
            self.tf2_dir_entry.insert(0, path)

    def open_steamid_finder(self):
        webbrowser.open("https://www.steamidfinder.com/")

    def connect_obs(self):
        host = self.obs_host_entry.get()
        port = int(self.obs_port_entry.get())
        password = self.obs_password_entry.get()

        try:
            self.obs_client = OBSWebSocket(host, port, password)
            self.obs_client.connect()
            self.obs_connected = True
            self.debug_callback("Connected to OBS successfully!")
        except Exception as e:
            self.debug_callback(f"Failed to connect to OBS: {e}")
            self.debug_callback(traceback.format_exc())

    def start_script(self):
        if not self.obs_client or not self.obs_client.connected:
            self.debug_callback("Error: Please connect to OBS first.")
            return

        tf2_path = self.tf2_dir_entry.get()
        player_name = self.steam_username_entry.get()
        steam_id = self.steam_id_entry.get()

        if not tf2_path or not player_name or not steam_id:
            self.debug_callback("Error: Please fill in all required fields.")
            return

        self.stop_event.clear()
        self.debug_callback("Starting monitoring...")
        self.monitoring_thread = threading.Thread(target=self.run_monitoring,
                                                  args=(tf2_path, player_name))
        self.monitoring_thread.start()
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.debug_callback("Monitoring thread started successfully!")

    def run_monitoring(self, tf2_path, player_name):
        event_handler = TF2LogHandler(self.obs_client, tf2_path, player_name, self.debug_callback, self.stop_event)
        observer = Observer()
        observer.schedule(event_handler, path=os.path.dirname(tf2_path), recursive=False)

        self.debug_callback("Starting log file watcher...")
        observer.start()
        self.debug_callback("Log file watcher started successfully!")

        try:
            while not self.stop_event.is_set():
                event_handler.check_file()
                time.sleep(1)  # Check every second
        except Exception as e:
            self.debug_callback(f"Error in monitoring thread: {e}")
            self.debug_callback(traceback.format_exc())
        finally:
            self.debug_callback("Stopping log file watcher...")
            observer.stop()
            observer.join()
            self.debug_callback("Log file watcher stopped.")

    def stop_script(self):
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.debug_callback("Stopping monitoring...")
            self.stop_event.set()
            self.monitoring_thread.join(timeout=5)
            if self.monitoring_thread.is_alive():
                self.debug_callback("Warning: Monitoring thread did not stop gracefully.")
            else:
                self.debug_callback("Monitoring stopped successfully.")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def debug_callback(self, message):
        self.debug_queue.put(message)

    def process_debug_queue(self):
        while not self.debug_queue.empty():
            message = self.debug_queue.get_nowait()
            self.debug_output.insert(tk.END, f"{message}\n")
            self.debug_output.see(tk.END)
            print(message)

def show_obs_info():
    info_text = """
To make the app work with OBS, please create the following:

Scenes:
- KillScene
- DeathScene
- SuicideScene

Sources:
- KillOverlay
- DeathOverlay
- SuicideOverlay

Ensure that these names match exactly in OBS. The app will trigger these scenes and sources based on your in-game events.

Important:
Make sure to add -condebug to TF2 launch options to enable console output logging.
To do this:
1. Right-click on TF2 in your Steam library
2. Select Properties
3. In the General tab, find "Launch Options"
4. Add -condebug to the launch options
5. Click OK and restart TF2 if it's running
"""
    messagebox.showinfo("OBS and TF2 Setup Info", info_text)

def main():
    root = tk.Tk()
    app = TF2OBSPlugin(root)

    try:
        while True:
            root.update()
            app.process_debug_queue()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Application terminated by user.")
    finally:
        if app.obs_client:
            app.obs_client.close()

if __name__ == "__main__":
    main()
            