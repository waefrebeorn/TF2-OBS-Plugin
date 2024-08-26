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
import queue
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger(__name__)

# Import your OBSWebSocket and TF2Events classes
from obs_websocket import OBSWebSocket
from tf2_events import TF2Events

# Default values
default_tf2_path = "K:/SteamLibrary/steamapps/common/Team Fortress 2/tf/console.log"
obs_host_default = "localhost"
obs_port_default = 4455
obs_password_default = "GaShyxLNXG1XT4qy"
steam_username_default = "WaefreBeorn"
steam_id_default = "76561198027081583"

class TF2LogHandler(PatternMatchingEventHandler):
    def __init__(self, obs_client, log_file_path, player_name, debug_callback, stop_event, use_images):
        super().__init__(patterns=[log_file_path], ignore_directories=True, case_sensitive=False)
        self.obs_client = obs_client
        self.player_name = player_name
        self.debug_callback = debug_callback
        self.stop_event = stop_event
        self.log_file_path = log_file_path
        self.last_position = self.get_file_size(log_file_path)
        self.debug_callback(f"Starting to monitor from position: {self.last_position}")
        self.tf2_events = TF2Events(player_name) 
        self.use_images = use_images
        # Define overlay_sources within the class
        self.overlay_sources = {
            "kill": "Kill",
            "death": "Death",
            "suicide": "Suicide",
            "capture": "Capture",
            "notification": "Notif", 
            "picked_up_intel": "PickedIntel",
            "dropped_intel": "DroppedIntel",
            "has_intel": "HasIntel",
            "built_sentrygun": "BuiltSentry",
            "built_dispenser": "BuiltDispenser",
            "built_teleporter_entrance": "BuiltTeleEntrance",
            "built_teleporter_exit": "BuiltTeleExit",
            "destroyed_sentrygun": "DestroyedSentry",
            "destroyed_dispenser": "DestroyedDispenser",
            "destroyed_teleporter_entrance": "DestroyedTeleEntrance",
            "destroyed_teleporter_exit": "DestroyedTeleExit",
            "domination": "Domination",
            "dominated": "Dominated",
            "revenge": "Revenge",
            "stunned": "Stunned",
            "jarated": "Jarated",
            "milked": "Milked",
            "extinguished": "Extinguished",
            "spawned": "Spawned",
            "medic_uber": "MedicUber",
            "medic_charge_deployed": "MedicCharge",
            "spy_disguise_complete": "SpyDisguise",
            "spy_backstab": "SpyBackstab",
            "engineer_teleported": "EngiTeleport",
            "sniper_headshot": "SniperHeadshot",
            "pyro_airblast": "PyroAirblast",
            "demoman_sticky_trap_triggered": "DemoTrap",
            "heavy_eating": "HeavyEating",
            "crit_boosted": "CritBoosted",
            "mini_crit_boosted": "MiniCritBoosted",
            "damage": "Damage",
            "healed": "Healed",
            "assist": "Assist",
            "round_win": "RoundWin",
            "round_stalemate": "RoundStalemate",
            "match_win": "MatchWin",
            "first_blood": "FirstBlood"
            # Add even more mappings as needed!
        }

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
                self.check_file() # Recheck the file from the beginning
        except Exception as e:
            self.debug_callback(f"Error reading log file: {e}")
            self.debug_callback(traceback.format_exc())

    def process_new_lines(self, lines):
        for line in lines:
            if self.stop_event.is_set():
                return
            self.debug_callback(f"New log line: {line.strip()}")

            event_data = self.tf2_events.process_log_line(line, self.debug_callback)
            if event_data:
                event_type, weapon, killstreak = event_data
                self.trigger_obs_effect(event_type, weapon, killstreak) 

    def trigger_obs_effect(self, event_type, weapon=None, killstreak=0):
        if self.stop_event.is_set():
            return
    
        if not self.obs_client.connected:
            self.debug_callback("OBS is not connected yet. Skipping effect trigger.")
            return
    
        self.debug_callback(f"Triggering OBS effect: {event_type}" + (f" with {weapon}" if weapon else ""))
    
        try:
            # Scene Switching Logic (Always switch back to TF2Scene after any event)
            time.sleep(1.5)  # Adjusted delay to 1.5 seconds
            self.obs_client.set_current_scene("TF2Scene") 
    
            # Overlay/Source Control in TF2Scene (Handles both image and media sources)
            if event_type in self.overlay_sources:
                source_name = self.overlay_sources[event_type]
                if self.use_images:  # Use image sources
                    request_type = "SetSceneItemRender"
                    request_data = {
                        "source": source_name,
                        "render": True
                    }
                else:  # Use media sources
                    request_type = "SetMediaSourceEnabled"
                    request_data = {
                        "sourceName": source_name,
                        "sourceEnabled": True
                    }
    
                self.obs_client.send_request(request_type, request_data)
                time.sleep(1.5)
    
                # Hide/disable the source
                request_data["render" if self.use_images else "sourceEnabled"] = False
                self.obs_client.send_request(request_type, request_data)
    
            # Event-specific logic
            if event_type == "kill":
                self.update_killstreak_display(killstreak) 
    
            elif event_type.startswith("built_") or event_type.startswith("destroyed_"):
                object_type = event_type.split("_")[1]
                action = "built" if event_type.startswith("built_") else "destroyed"
                notification_text = f"{self.player_name} {action} a {object_type}"
                self.display_notification(notification_text)
    
            elif event_type in ["crit_boosted", "mini_crit_boosted", "damage", "healed", "assist"]:
                target_player = weapon 
                notification_text = f"{self.player_name} {event_type} {target_player}"
                if killstreak: 
                    notification_text += f" for {killstreak} damage" 
                self.display_notification(notification_text)
    
            elif event_type in ["round_win", "round_stalemate", "match_win", "first_blood"]:
                notification_text = f"{event_type.replace('_', ' ').capitalize()}!"
                self.display_notification(notification_text)
    
            elif event_type == "spawned":
                self.update_class_overlay(weapon) 
    
            # Handle other events that only trigger overlay/media source
            elif event_type in ["picked_up_intel", "dropped_intel", "has_intel",
                                "domination", "dominated", "revenge", "stunned", "jarated",
                                "milked", "extinguished", "medic_uber", "medic_charge_deployed",
                                "spy_disguise_complete", "spy_backstab", "engineer_teleported",
                                "sniper_headshot", "pyro_airblast", "demoman_sticky_trap_triggered",
                                "heavy_eating"]:
                pass  # No additional action needed, overlay/media source is already triggered
    
            self.debug_callback(f"OBS effect for {event_type} triggered successfully")
            print(f"OBS effect for {event_type} triggered successfully!")
    
        except Exception as e:
            self.debug_callback(f"Failed to trigger OBS effect: {e}")
            self.debug_callback(traceback.format_exc())
            print(f"Failed to trigger OBS effect for {event_type}: {e}")
            
    def update_killstreak_display(self, killstreak):
        # Now implemented to update a text source in OBS
        self.obs_client.send_request("SetTextGDIPlusProperties", {
            "source": "KillstreakText", # Replace with your actual text source name
            "text": f"Killstreak: {killstreak}"
        })

    def display_notification(self, text):
        self.obs_client.send_request("SetTextGDIPlusProperties", {
            "source": "NotificationText", 
            "text": text
        })

        # Briefly show the notification overlay (directly in the TF2 scene)
        self.obs_client.set_scene_item_enabled("TF2 Scene", "NotificationOverlay", True) # Assuming "TF2 Scene" is your main scene
        time.sleep(3)
        self.obs_client.set_scene_item_enabled("TF2 Scene", "NotificationOverlay", False)

    def update_class_overlay(self, class_name):
        # Map class names to media source names (replace with your actual source names)
        class_media_sources = {
            "Scout": "ScoutOverlay",
            "Soldier": "SoldierOverlay",
            "Pyro": "PyroOverlay",
            "Demoman": "DemomanOverlay",
            "Heavy": "HeavyOverlay",
            "Engineer": "EngineerOverlay",
            "Medic": "MedicOverlay",
            "Sniper": "SniperOverlay",
            "Spy": "SpyOverlay",
            "Saxton Hale": "HaleOverlay"
        }

        if class_name in class_media_sources:
            media_source_name = class_media_sources[class_name]

            # Hide all class overlays first
            for source_name in class_media_sources.values():
                self.obs_client.send_request("SetMediaSourceEnabled", {
                    "sourceName": source_name,
                    "sourceEnabled": False
                })

            # Show the overlay for the current class
            self.obs_client.send_request("SetMediaSourceEnabled", {
                "sourceName": media_source_name,
                "sourceEnabled": True
            })

        else:
            self.debug_callback(f"Unknown class: {class_name}")
            
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
        self.use_images = False  # Default value

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
    
        # Checkbox for image/media source selection
        self.use_images_var = tk.BooleanVar(value=False)  # Default to media sources
        self.use_images_checkbox = tk.Checkbutton(self.root, text="Use Image Sources", variable=self.use_images_var)
        self.use_images_checkbox.grid(row=9, column=0, columnspan=3, padx=10, pady=10)
    
        # Debug output
        tk.Label(self.root, text="Debug Output:").grid(row=10, column=0, padx=10, pady=10)
        self.debug_output = scrolledtext.ScrolledText(self.root, width=70, height=10)
        self.debug_output.grid(row=11, column=0, columnspan=3, padx=10, pady=10)
    
        # Start monitoring button
        self.start_button = tk.Button(self.root, text="Start Monitoring", command=self.start_script)
        self.start_button.grid(row=12, column=0, columnspan=3, padx=10, pady=20)
    
        # Stop monitoring button
        self.stop_button = tk.Button(self.root, text="Stop Monitoring", command=self.stop_script, state=tk.DISABLED)
        self.stop_button.grid(row=13, column=0, columnspan=3, padx=10, pady=20)
        
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

        self.use_images = self.use_images_var.get() 
        self.stop_event.clear()
        self.debug_callback("Starting monitoring...")
        self.monitoring_thread = threading.Thread(target=self.run_monitoring,
                                                    args=(tf2_path, player_name))
        self.monitoring_thread.start()
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.debug_callback("Monitoring thread started successfully!")

    def run_monitoring(self, tf2_path, player_name):
        event_handler = TF2LogHandler(self.obs_client, tf2_path, player_name, self.debug_callback, self.stop_event, self.use_images)
        observer = Observer()
        observer.schedule(event_handler, path=os.path.dirname(tf2_path), recursive=False)

        self.debug_callback("Starting log file watcher...")
        observer.start()
        self.debug_callback("Log file watcher started successfully!")

        try:
            while not self.stop_event.is_set():
                event_handler.check_file()
                time.sleep(1) # Check every second
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
- Tf2Scene (your main scene for TF2 gameplay)

Sources:
- KillOverlay (Media Source)
- DeathOverlay (Media Source)
- SuicideOverlay (Media Source)
- CaptureOverlay (Media Source)
- NotificationOverlay (Media Source) 
- KillstreakText (Text GDI+ Source)
- NotificationText (Text GDI+ Source)
- ScoutOverlay (Media Source)
- SoldierOverlay (Media Source)
- PyroOverlay (Media Source)
- DemomanOverlay (Media Source)
- HeavyOverlay (Media Source)
- EngineerOverlay (Media Source)
- MedicOverlay (Media Source)
- SniperOverlay (Media Source)
- SpyOverlay (Media Source)
- HaleOverlay (Media Source)
- PickedIntel (Media Source)
- DroppedIntel (Media Source)
- HasIntel (Media Source)
- BuiltSentry (Media Source)
- BuiltDispenser (Media Source)
- BuiltTeleEntrance (Media Source)
- BuiltTeleExit (Media Source)
- DestroyedSentry (Media Source)
- DestroyedDispenser (Media Source)
- DestroyedTeleEntrance (Media Source)
- DestroyedTeleExit (Media Source)
- Domination (Media Source)
- Dominated (Media Source)
- Revenge (Media Source)
- Stunned (Media Source)
- Jarated (Media Source)
- Milked (Media Source)
- Extinguished (Media Source)
- Spawned (Media Source)
- MedicUber (Media Source)
- MedicCharge (Media Source)
- SpyDisguise (Media Source)
- SpyBackstab (Media Source)
- EngiTeleport (Media Source)
- SniperHeadshot (Media Source)
- PyroAirblast (Media Source)
- DemoTrap (Media Source)
- HeavyEating (Media Source)
- CritBoosted (Media Source)
- MiniCritBoosted (Media Source)
- Damage (Media Source)
- Healed (Media Source)
- Assist (Media Source)
- RoundWin (Media Source)
- RoundStalemate (Media Source)
- MatchWin (Media Source)
- FirstBlood (Media Source)

Ensure that these names match exactly in OBS. The app will trigger these sources based on your in-game events.

Important:
- Place the NotificationOverlay and NotificationText sources directly in your TF2 Scene.
- Make sure to add -condebug to TF2 launch options to enable console output logging
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