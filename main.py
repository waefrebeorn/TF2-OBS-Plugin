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
import atexit

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
        self.obs_effect_queue = queue.Queue()        
        self.overlay_sources = {
            "kill": "KillOverlay",
            "death": "DeathOverlay",
            "suicide": "SuicideOverlay",
            "capture": "CaptureOverlay",
            "notification": "NotificationOverlay", 
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

    def on_event(self, event):
        if isinstance(event, FileModifiedEvent):
            self.check_file()
        else:
            # Handle other events, like scene changes from OBS
            try:
                event_data = json.loads(event.src_path)  # Assuming you're receiving OBS events as JSON strings
                if 'update-type' in event_data and event_data['update-type'] == 'SwitchScenes':
                    self.debug_callback("Scene switched in OBS. Clearing scene item ID cache.")
                    self.obs_client.clear_scene_item_id_cache()
            except json.JSONDecodeError:
                self.debug_callback(f"Error decoding event data: {event.src_path}")
                
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
                    self.debug_callback(f"Read {len(new_lines)} new lines from log file.")
                    self.process_new_lines(new_lines)
            elif current_size < self.last_position:
                self.debug_callback("Log file size decreased. File might have been truncated or replaced.")
                self.last_position = 0
                self.check_file()  # Recheck the file from the beginning
            else:
                self.debug_callback("No new content in log file.")
        except Exception as e:
            self.debug_callback(f"Error reading log file: {e}")
            self.debug_callback(traceback.format_exc())

    def process_new_lines(self, lines):
        for line in lines:
            if self.stop_event.is_set():
                return
            self.debug_callback(f"Processing log line: {line.strip()}")

            event_data = self.tf2_events.process_log_line(line, self.debug_callback)
            if event_data:
                event_type, weapon, killstreak = event_data
                self.debug_callback(f"Event detected: {event_type}, Weapon: {weapon}, Killstreak: {killstreak}")
                self.obs_effect_queue.put((event_type, weapon, killstreak))
            else:
                self.debug_callback("No event detected for this line.")

    def update_killstreak_display(self, killstreak):
        self.debug_callback(f"Updating killstreak display to {killstreak}")
        response = self.obs_client.set_input_settings("KillstreakText", {"text": f"Killstreak: {killstreak}"})
        if response and 'd' in response and 'requestStatus' in response['d'] and response['d']['requestStatus']['result']:
            self.debug_callback("Successfully updated killstreak display")
        else:
            self.debug_callback(f"Failed to update killstreak display. Response: {response}")               
                
    def get_current_scene_with_retry(self):
        retry_count = 3
        while retry_count > 0:
            current_scene = self.obs_client.get_current_scene()
            if current_scene:
                return current_scene
            retry_count -= 1
            time.sleep(0.1)  # Short delay before retrying
        return None
        
    def trigger_obs_effect(self, event_type, weapon=None, killstreak=0):
        if self.stop_event.is_set():
            return
    
        if not self.obs_client.connected:
            self.debug_callback("OBS is not connected yet. Skipping effect trigger.")
            return
    
        self.debug_callback(f"Triggering OBS effect: {event_type}" + (f" with {weapon}" if weapon else ""))
    
        try:
            current_scene = self.get_current_scene_with_retry()
            if not current_scene:
                self.debug_callback("Failed to get current scene name after retries. Skipping effect.")
                return
    
            source_name = self.overlay_sources.get(event_type)
            if source_name:
                toggle_result = self.toggle_source_visibility(current_scene, source_name)
                if not toggle_result:
                    self.debug_callback(f"Failed to toggle visibility for source '{source_name}'. Continuing with other effects.")
            else:
                self.debug_callback(f"No overlay source found for event type: {event_type}. Continuing with other effects.")
    
            # Event-specific logic
            if event_type == "kill":
                self.update_killstreak_display(killstreak)
            elif event_type in ["death", "suicide"]:
                self.update_killstreak_display(0)
            elif event_type.startswith("built_") or event_type.startswith("destroyed_"):
                self.handle_build_destroy_event(event_type)
            elif event_type in ["crit_boosted", "mini_crit_boosted", "damage", "healed", "assist"]:
                self.handle_stat_event(event_type, weapon, killstreak)
            elif event_type in ["round_win", "round_stalemate", "match_win", "first_blood"]:
                self.handle_game_event(event_type)
            elif event_type == "spawned":
                self.update_class_overlay(weapon)
    
            self.debug_callback(f"OBS effect for {event_type} triggered successfully")
    
        except Exception as e:
            self.debug_callback(f"Failed to trigger OBS effect: {str(e)}")
            self.debug_callback(traceback.format_exc())
         
    def toggle_source_visibility(self, scene, source_name):
        self.debug_callback(f"Attempting to toggle visibility for source '{source_name}' in scene '{scene}'")
        
        if scene is None or source_name is None:
            self.debug_callback(f"Error: Invalid scene ({scene}) or source name ({source_name})")
            return False
    
        try:
            if self.use_images:
                # Enable the source
                enable_result = self.obs_client.set_scene_item_enabled(scene, source_name, True)
                if enable_result is None:
                    self.debug_callback(f"Failed to enable source '{source_name}'.")
                    return False
    
                time.sleep(0.3)
    
                # Disable the source
                disable_result = self.obs_client.set_scene_item_enabled(scene, source_name, False)
                if disable_result is None:
                    self.debug_callback(f"Failed to disable source '{source_name}'.")
                    return False
            else:
                # Toggle mute state for media sources
                mute_result = self.obs_client.set_input_mute(source_name, False)
                if mute_result is None:
                    self.debug_callback(f"Failed to unmute source '{source_name}'")
                    return False
                
                time.sleep(0.3)
                
                unmute_result = self.obs_client.set_input_mute(source_name, True)
                if unmute_result is None:
                    self.debug_callback(f"Failed to mute source '{source_name}'")
                    return False
    
            self.debug_callback(f"Successfully toggled visibility for source '{source_name}'")
            return True
        except Exception as e:
            self.debug_callback(f"Error toggling source visibility: {str(e)}")
            self.debug_callback(traceback.format_exc())
            return False

 
    def update_killstreak_display(self, killstreak):
        try:
            self.debug_callback(f"Updating killstreak display to {killstreak}")
            response = self.obs_client.set_input_settings("KillstreakText", {"text": f"Killstreak: {killstreak}"})
            if not (response and 'd' in response and 'requestStatus' in response['d'] and response['d']['requestStatus']['result']):
                self.debug_callback(f"Failed to update killstreak display. Response: {response}")
        except Exception as e:
            self.debug_callback(f"Error updating killstreak display: {str(e)}")
    
    def display_notification(self, text):
        try:
            self.obs_client.set_text_gdi_plus_properties("NotificationText", text)
            
            current_scene = self.obs_client.get_current_scene()
            if current_scene:
                self.obs_client.set_scene_item_enabled(current_scene, "NotificationOverlay", True)
                time.sleep(3)
                self.obs_client.set_scene_item_enabled(current_scene, "NotificationOverlay", False)
            else:
                self.debug_callback("Failed to get current scene name. Skipping notification display.")
        except Exception as e:
            self.debug_callback(f"Error displaying notification: {str(e)}")
    
    def update_class_overlay(self, class_name):
        try:
            class_media_sources = {
                "Scout": "ScoutOverlay", "Soldier": "SoldierOverlay", "Pyro": "PyroOverlay",
                "Demoman": "DemomanOverlay", "Heavy": "HeavyOverlay", "Engineer": "EngineerOverlay",
                "Medic": "MedicOverlay", "Sniper": "SniperOverlay", "Spy": "SpyOverlay",
                "Saxton Hale": "HaleOverlay"
            }
    
            if class_name in class_media_sources:
                media_source_name = class_media_sources[class_name]
    
                for source_name in class_media_sources.values():
                    self.obs_client.send_request("SetMediaSourceEnabled", {
                        "sourceName": source_name,
                        "sourceEnabled": source_name == media_source_name
                    })
            else:
                self.debug_callback(f"Unknown class: {class_name}")
        except Exception as e:
            self.debug_callback(f"Error updating class overlay: {str(e)}")
    
    def handle_build_destroy_event(self, event_type):
        try:
            object_type = event_type.split("_")[1]
            action = "built" if event_type.startswith("built_") else "destroyed"
            notification_text = f"{self.player_name} {action} a {object_type}"
            self.display_notification(notification_text)
        except Exception as e:
            self.debug_callback(f"Error handling build/destroy event: {str(e)}")
    
    def handle_stat_event(self, event_type, target_player, killstreak):
        try:
            notification_text = f"{self.player_name} {event_type} {target_player}"
            if killstreak:
                notification_text += f" for {killstreak} damage"
            self.display_notification(notification_text)
        except Exception as e:
            self.debug_callback(f"Error handling stat event: {str(e)}")
    
    def handle_game_event(self, event_type):
        try:
            notification_text = f"{event_type.replace('_', ' ').capitalize()}!"
            self.display_notification(notification_text)
        except Exception as e:
            self.debug_callback(f"Error handling game event: {str(e)}")  
    
    
            
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
        self.root.after(100, self.process_debug_queue)
        self.last_debug_time = 0
        self.use_images = False  # Default value
        self.event_handler = None
        self.obs_effect_thread = None
        # Register the cleanup method to be called on exit
        atexit.register(self.cleanup)
    
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
        condebug_text = "Remember to add -condebug -console -log_verbose_enable 1 to TF2 launch options!"
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
    
        self.debug_callback(f"Attempting to connect to OBS at {host}:{port}")
        try:
            self.obs_client = OBSWebSocket(host, port, password, debug_callback=self.debug_callback)
            self.obs_client.connect()
            self.obs_connected = True
            self.debug_callback("Connected to OBS successfully!")
        except Exception as e:
            self.debug_callback(f"Failed to connect to OBS: {str(e)}")
            self.debug_callback(traceback.format_exc())
            self.obs_client = None
            self.obs_connected = False
    
        if self.obs_connected:
            self.debug_callback("Testing connection with GetSceneList request")
            test_response = self.obs_client.send_request("GetSceneList")
            if test_response and 'd' in test_response and 'responseData' in test_response['d']:
                self.debug_callback("Successfully retrieved scene list from OBS.")
                self.debug_callback(f"Scene list: {json.dumps(test_response['d']['responseData'], indent=2)}")
            else:
                self.debug_callback("Failed to retrieve scene list from OBS. Connection may be unstable.")
                self.debug_callback(f"Response received: {test_response}")
        else:
            self.debug_callback("Not attempting to retrieve scene list due to failed connection")
        
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
        self.event_handler = TF2LogHandler(self.obs_client, tf2_path, player_name, self.debug_callback, self.stop_event, self.use_images)
        self.monitoring_thread = threading.Thread(target=self.run_monitoring)
        self.monitoring_thread.start()
        self.obs_effect_thread = threading.Thread(target=self.process_obs_effects)
        self.obs_effect_thread.start()
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.debug_callback("Monitoring and OBS effect threads started successfully!")

    def run_monitoring(self):
        observer = Observer()
        observer.schedule(self.event_handler, path=os.path.dirname(self.event_handler.log_file_path), recursive=False)

        self.debug_callback("Starting log file watcher...")
        observer.start()
        self.debug_callback("Log file watcher started successfully!")

        try:
            while not self.stop_event.is_set():
                self.event_handler.check_file()
                time.sleep(1)  # Check every second
        except Exception as e:
            self.debug_callback(f"Error in monitoring thread: {e}")
            self.debug_callback(traceback.format_exc())
        finally:
            self.debug_callback("Stopping log file watcher...")
            observer.stop()
            observer.join()
            self.debug_callback("Log file watcher stopped.")

        self.debug_callback("Monitoring thread ended.")

    def process_obs_effects(self):
        while not self.stop_event.is_set():
            try:
                effect = self.event_handler.obs_effect_queue.get(timeout=1)
                self.event_handler.trigger_obs_effect(*effect)
                self.event_handler.obs_effect_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.debug_callback(f"Error processing OBS effect: {str(e)}")
                self.debug_callback(traceback.format_exc())

        self.debug_callback("OBS effect processing thread ended.")
        
    def stop_script(self):
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.debug_callback("Stopping monitoring...")
            self.stop_event.set()
            self.monitoring_thread.join(timeout=5)
            if self.monitoring_thread.is_alive():
                self.debug_callback("Warning: Monitoring thread did not stop gracefully.")
            else:
                self.debug_callback("Monitoring stopped successfully.")
        if self.obs_effect_thread and self.obs_effect_thread.is_alive():
            self.obs_effect_thread.join(timeout=5)
            if self.obs_effect_thread.is_alive():
                self.debug_callback("Warning: OBS effect thread did not stop gracefully.")
            else:
                self.debug_callback("OBS effect thread stopped successfully.")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
    def debug_callback(self, message):
        self.debug_queue.put(message)

    def process_debug_queue(self):
        try:
            while True:
                message = self.debug_queue.get_nowait()
                self.debug_output.insert(tk.END, f"{message}\n")
                self.debug_output.see(tk.END)
                print(message)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_debug_queue) 

    def cleanup(self):
        """Clean up resources when the application exits."""
        self.debug_callback("Cleaning up resources...")
        if self.obs_client and self.obs_client.connected:
            self.obs_client.close()
            self.debug_callback("OBS client connection closed.")
        self.stop_script()
        self.debug_callback("Cleanup complete.")

    def on_closing(self):
        """Handle the window close event."""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.cleanup()
            self.root.destroy()
            
            
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
- Make sure to add -condebug -console -log_verbose_enable 1 to TF2 launch options to enable console output logging
"""
    messagebox.showinfo("OBS and TF2 Setup Info", info_text)

def main():
    root = tk.Tk()
    app = TF2OBSPlugin(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)  # Handle window close event

    try:
        while True:
            root.update()
            app.process_debug_queue()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Application terminated by user.")
    finally:
        app.cleanup()

if __name__ == "__main__":
    main()