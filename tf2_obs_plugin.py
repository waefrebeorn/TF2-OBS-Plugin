import os
import time
import re
import webbrowser
import json
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from watchdog.observers import Observer
import threading
import queue
import logging
import atexit

from obs_websocket import OBSWebSocket
from tf2_events import TF2Events
from tf2_log_handler import TF2LogHandler
from config import (default_tf2_path, obs_host_default, obs_port_default,
                    obs_password_default, steam_username_default, steam_id_default)
                    
                    
class TF2OBSPlugin:
    def __init__(self, root):
        self.root = root
        self.root.title("TF2 OBS Plugin Configuration")
        self.obs_client = None
        self.monitoring_thread = None
        self.stop_event = threading.Event()
        self.obs_connected = False
        self.is_running = True
        self.create_widgets()
        self.debug_queue = queue.Queue()
        self.root.after(100, self.process_debug_queue)
        self.process_debug_queue_id = None        
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

        # Delete console.log button
        self.delete_log_button = tk.Button(self.root, text="Delete console.log", command=self.delete_console_log)
        self.delete_log_button.grid(row=14, column=0, columnspan=3, padx=10, pady=20)

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
    
        ##if self.obs_connected:
        ##    self.debug_callback("Testing connection with GetSceneList request")
        ##    # Print the cached scene item IDs for debugging
        ##    self.debug_callback("Caching scene item IDs")
        ##    self.obs_client.cache_scene_item_ids()
        ##    print(self.obs_client.scene_item_ids)
        ##    test_response = self.obs_client.send_request("GetSceneList")
        ##    if test_response and 'd' in test_response and 'responseData' in test_response['d']:
        ##        self.debug_callback("Successfully retrieved scene list from OBS.")
        ##        self.debug_callback(f"Scene list: {json.dumps(test_response['d']['responseData'], indent=2)}")
        ##    else:
        ##        self.debug_callback("Failed to retrieve scene list from OBS. Connection may be unstable.")
        ##        self.debug_callback(f"Response received: {test_response}")
        ##else:
        ##    self.debug_callback("Not attempting to retrieve scene list due to failed connection")
        
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
    
        # Initialize event_handler BEFORE creating the obs_effect_thread
        self.event_handler = TF2LogHandler(self.obs_client, tf2_path, player_name, self.debug_callback, self.stop_event, self.use_images)
    
        self.monitoring_thread = threading.Thread(target=self.run_monitoring)
        self.monitoring_thread.start()
    
        # Now it's safe to start the obs_effect_thread
        self.obs_effect_thread = threading.Thread(target=self.event_handler.process_obs_effects)
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

    def process_debug_queue(self):
        if not self.is_running:
            return
        try:
            while True:
                message = self.debug_queue.get_nowait()
                if self.is_running:
                    self.debug_output.insert(tk.END, f"{message}\n")
                    self.debug_output.see(tk.END)
                print(message)
        except queue.Empty:
            pass
        finally:
            if self.is_running:
                self.process_debug_queue_id = self.root.after(100, self.process_debug_queue)

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
        if self.is_running:
            try:
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
            except tk.TclError:
                pass  # Ignore Tkinter errors during shutdown

    def delete_console_log(self):
        directory = os.path.dirname(self.tf2_dir_entry.get())
        log_path = os.path.join(directory, "console.log")
        if os.path.exists(log_path):
            try:
                os.remove(log_path)
                self.debug_callback(f"Deleted console.log from {directory}")
                messagebox.showinfo("Success", f"console.log deleted from {directory}")
            except Exception as e:
                self.debug_callback(f"Error deleting console.log: {str(e)}")
                messagebox.showerror("Error", f"Failed to delete console.log: {str(e)}")
        else:
            self.debug_callback(f"console.log not found in {directory}")
            messagebox.showinfo("Info", f"console.log not found in {directory}")

    def cleanup(self):
        self.debug_callback("Cleaning up resources...")
        if self.obs_client and self.obs_client.connected:
            self.obs_client.close()
            self.debug_callback("OBS client connection closed.")
        self.stop_script()
        self.debug_callback("Cleanup complete.")

    def on_closing(self):
        self.is_running = False
        if self.process_debug_queue_id:
            self.root.after_cancel(self.process_debug_queue_id)
        self.cleanup()
        self.root.quit()

    def debug_callback(self, message):
        self.debug_queue.put(message)
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
- MultiKill (Media Source)
- Killstreak (Media Source)
- CapPointBlocked (Media Source)
- TeleporterUsed (Media Source)
- DestroyedBuilding (Media Source)
- SappedBuilding (Media Source)
- UberchargeDeployed (Media Source)
- DeflectedProjectile (Media Source)
- EnvironmentKill (Media Source)
- FlagPickedUp (Media Source)
- FlagCaptured (Media Source)
- FlagDefended (Media Source)
- CartPushed (Media Source)
- CartBlocked (Media Source)
- PointCaptured (Media Source)
- PointDefended (Media Source)
- MVMCreditCollected (Media Source)
- MVMWaveCompleted (Media Source)
- MVMBombReset (Media Source)
- HalloweenBossKilled (Media Source)
- HalloweenGiftGrabbed (Media Source)
- PlayerUpgraded (Media Source)
- PlayerTeleported (Media Source)
- PlayerResupplied (Media Source)
- PlayerStunned (Media Source)
- PlayerIgnited (Media Source)
- PlayerExtinguished (Media Source)
- PlayerMVP (Media Source)
- TauntKill (Media Source)
- ContractCompleted (Media Source)
- ContractPointsGained (Media Source)

Ensure that these names match exactly in OBS. The app will trigger these sources based on your in-game events.

Important:
- Place the NotificationOverlay and NotificationText sources directly in your TF2 Scene.
- Make sure to add -condebug -console -log_verbose_enable 1 to TF2 launch options to enable console output logging
"""
    messagebox.showinfo("OBS and TF2 Setup Info", info_text)
