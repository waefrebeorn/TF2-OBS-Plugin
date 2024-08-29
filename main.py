import os
import time
import re
import webbrowser
import json
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
obs_password_default = "obspassword"
steam_username_default = "WaefreBeorn"
steam_id_default = "76561198027081583"

class TF2LogHandler(PatternMatchingEventHandler):
    def __init__(self, obs_client, log_file_path, player_name, debug_callback, stop_event, use_images):
        super().__init__(patterns=[log_file_path], ignore_directories=True, case_sensitive=False)
        self.obs_client = obs_client
        self.current_scene_cache = None  # Initialize the scene cache
        self.cache_expiry_time = None  # Initialize the cache expiry time
        self.player_name = player_name
        self.debug_callback = debug_callback
        self.stop_event = stop_event
        self.log_file_path = log_file_path
        self.last_position = self.get_file_size(log_file_path)
        self.debug_callback(f"Starting to monitor from position: {self.last_position}")
        self.tf2_events = TF2Events(player_name) 
        self.use_images = use_images
        self.obs_effect_queue = queue.Queue()  
        self.last_check_had_content = False   
        self.notification_duration = 3  # Duration in seconds for notifications        
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
            "first_blood": "FirstBlood",
            "multi_kill": "MultiKill",
            "killstreak": "Killstreak",
            "cap_point_blocked": "CapPointBlocked",
            "teleporter_used": "TeleporterUsed",
            "destroyed_building": "DestroyedBuilding",
            "sapped_building": "SappedBuilding",
            "ubercharge_deployed": "UberchargeDeployed",
            "deflected_projectile": "DeflectedProjectile",
            "environment_kill": "EnvironmentKill",
            "flag_picked_up": "FlagPickedUp",
            "flag_captured": "FlagCaptured",
            "flag_defended": "FlagDefended",
            "cart_pushed": "CartPushed",
            "cart_blocked": "CartBlocked",
            "point_captured": "PointCaptured",
            "point_defended": "PointDefended",
            "mvm_credit_collected": "MVMCreditCollected",
            "mvm_wave_completed": "MVMWaveCompleted",
            "mvm_bomb_reset": "MVMBombReset",
            "halloween_boss_killed": "HalloweenBossKilled",
            "halloween_gift_grabbed": "HalloweenGiftGrabbed",
            "player_upgraded": "PlayerUpgraded",
            "player_teleported": "PlayerTeleported",
            "player_resupplied": "PlayerResupplied",
            "player_stunned": "PlayerStunned",
            "player_ignited": "PlayerIgnited",
            "player_extinguished": "PlayerExtinguished",
            "player_mvp": "PlayerMVP",
            "taunt_kill": "TauntKill",
            "contract_completed": "ContractCompleted",
            "contract_points_gained": "ContractPointsGained"
        }
        self.recognized_weapons = [
            # Scout
            "scattergun", "pistol_scout", "bat", "force_a_nature", "bonk", "sandman", "flying_guillotine", "wrap_assassin",
            
            # Soldier
            "tf_projectile_rocket", "shotgun_soldier", "shovel", "buff_banner", "gunboats", "battalion_backup", "concheror", "mantreads", "market_gardener", "disciplinary_action",
            
            # Pyro
            "flamethrower", "shotgun_pyro", "fireaxe", "degreaser", "backburner", "flaregun", "detonator", "reserve_shooter", "powerjack", "axtinguisher", "homewrecker",
            
            # Demoman
            "tf_projectile_pipe", "bottle", "grenade_launcher", "tf_projectile_pipe_remote", "loch_n_load", "chargin_targe", "splendid_screen", "stickybomb_launcher", "scottish_resistance", "eyelander", "ullapool_caber",
            
            # Heavy
            "minigun", "shotgun_hwg", "fists", "natascha", "sandvich", "dalokohs_bar", "buffalo_steak_sandvich", "holiday_punch", "eviction_notice",
            
            # Engineer
            "shotgun_primary", "pistol", "wrench", "frontier_justice", "wrangler", "short_circuit", "widowmaker", "pomson", "eureka_effect", "gunslinger",
            
            # Medic
            "syringegun_medic", "medigun", "bonesaw", "crusaders_crossbow", "blutsauger", "kritzkrieg", "quick_fix", "vaccinator", "ubersaw", "vita_saw",
            
            # Sniper
            "sniperrifle", "smg", "club", "huntsman", "jarate", "sydney_sleeper", "bazaar_bargain", "machina", "shahanshah", "bushwacka",
            
            # Spy
            "revolver", "knife", "invis", "ambassador", "letranger", "enforcer", "diamondback", "your_eternal_reward", "conniver's_kunai", "big_earner", "spy_cicle",
            
            # Multi-class weapons
            "shotgun", "pistol", "panic_attack", "reserve_shooter", "family_business",
            
            # Special kill types
            "world", "trigger_hurt", "environmental", "saw_kill", "pumpkin_bomb", "goomba", "backstab", "headshot", "deflect_rocket", "deflect_promode", "telefrag", "tauntkill",
            
            # Buildings
            "obj_sentrygun", "obj_dispenser", "obj_teleporter",
            
            # MvM specific
            "robot_arm", "robot_arm_blender_kill", "robot_arm_combo_kill", "robot_shotgun", "deflect_arrow", "deflect_flare",
            
            # Holiday/Event specific
            "holiday_punch", "spellbook_fireball", "spellbook_lightning", "spellbook_teleport", "spellbook_ball_o_bats", "spellbook_meteor", "spellbook_mirv", "skull", "tf_pumpkin_bomb",
            
            # Miscellaneous
            "bleed_kill", "dragons_fury", "gas_blast", "grappling_hook", "crossing_guard", "passtime_gun", "flame_thrower", "rocketlauncher_directhit", "compound_bow", "the_classic", "long_heatmaker"
        ]
        self.event_handlers = {
            "kill": self._handle_kill_event,
            "death": self._handle_death_event,
            "suicide": self._handle_death_event,
            "spawned": self._handle_spawn_event,
            "capture": self._handle_capture_event,
            "picked_up_intel": self._handle_intel_event,
            "dropped_intel": self._handle_intel_event,
            "has_intel": self._handle_intel_event,
            "built_sentrygun": self._handle_build_event,
            "built_dispenser": self._handle_build_event,
            "built_teleporter_entrance": self._handle_build_event,
            "built_teleporter_exit": self._handle_build_event,
            "destroyed_sentrygun": self._handle_destroy_event,
            "destroyed_dispenser": self._handle_destroy_event,
            "destroyed_teleporter_entrance": self._handle_destroy_event,
            "destroyed_teleporter_exit": self._handle_destroy_event,
            "domination": self._handle_domination_event,
            "dominated": self._handle_dominated_event,
            "revenge": self._handle_revenge_event,
            "stunned": self._handle_status_effect_event,
            "jarated": self._handle_status_effect_event,
            "milked": self._handle_status_effect_event,
            "extinguished": self._handle_status_effect_event,
            "medic_uber": self._handle_medic_event,
            "medic_charge_deployed": self._handle_medic_event,
            "spy_disguise_complete": self._handle_spy_event,
            "spy_backstab": self._handle_spy_event,
            "engineer_teleported": self._handle_engineer_event,
            "sniper_headshot": self._handle_sniper_event,
            "pyro_airblast": self._handle_pyro_event,
            "demoman_sticky_trap_triggered": self._handle_demoman_event,
            "heavy_eating": self._handle_heavy_event,
            "crit_boosted": self._handle_crit_event,
            "mini_crit_boosted": self._handle_crit_event,
            "damage": self._handle_stat_event,
            "healed": self._handle_stat_event,
            "assist": self._handle_stat_event,
            "round_win": self._handle_game_event,
            "round_stalemate": self._handle_game_event,
            "match_win": self._handle_game_event,
            "first_blood": self._handle_first_blood_event,
            "multi_kill": self._handle_multi_kill_event,
            "killstreak": self._handle_killstreak_event,
            "cap_point_blocked": self._handle_objective_event,
            "teleporter_used": self._handle_teleporter_event,
            "destroyed_building": self._handle_destroy_event,
            "sapped_building": self._handle_sap_event,
            "ubercharge_deployed": self._handle_uber_event,
            "deflected_projectile": self._handle_deflect_event,
            "environment_kill": self._handle_environment_kill_event,
            "flag_picked_up": self._handle_flag_event,
            "flag_captured": self._handle_flag_event,
            "flag_defended": self._handle_flag_event,
            "cart_pushed": self._handle_cart_event,
            "cart_blocked": self._handle_cart_event,
            "point_captured": self._handle_point_event,
            "point_defended": self._handle_point_event,
            "mvm_credit_collected": self._handle_mvm_event,
            "mvm_wave_completed": self._handle_mvm_event,
            "mvm_bomb_reset": self._handle_mvm_event,
            "halloween_boss_killed": self._handle_halloween_event,
            "halloween_gift_grabbed": self._handle_halloween_event,
            "player_upgraded": self._handle_upgrade_event,
            "player_teleported": self._handle_teleporter_event,
            "player_resupplied": self._handle_resupply_event,
            "player_stunned": self._handle_status_effect_event,
            "player_ignited": self._handle_status_effect_event,
            "player_extinguished": self._handle_status_effect_event,
            "player_mvp": self._handle_mvp_event,
            "taunt_kill": self._handle_taunt_kill_event,
            "contract_completed": self._handle_contract_event,
            "contract_points_gained": self._handle_contract_event
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
                event_data = json.loads(event.src_path)
                if 'update-type' in event_data and event_data['update-type'] == 'SwitchScenes':
                    self.debug_callback("Scene switched in OBS. Clearing scene item ID cache.")
                    self.obs_client.clear_scene_item_id_cache()
                    self.current_scene_cache = None  # Invalidate the scene cache on scene switch
            except json.JSONDecodeError:
                self.debug_callback(f"Error decoding event data: {event.src_path}")

    def check_file(self):
        if self.stop_event.is_set():
            return
        try:
            current_size = self.get_file_size(self.log_file_path)
            if current_size > self.last_position:
                with open(self.log_file_path, 'r', encoding='utf-8', errors='replace') as log_file:
                    log_file.seek(self.last_position)
                    new_lines = log_file.readlines()
                    self.last_position = log_file.tell()
                    if new_lines:
                        self.debug_callback(f"Read {len(new_lines)} new lines from log file.")
                        self.process_new_lines(new_lines)
                        self.last_check_had_content = True
                    elif self.last_check_had_content:
                        self.debug_callback("No new content in log file.")
                        self.last_check_had_content = False
            elif current_size < self.last_position:
                self.debug_callback("Log file size decreased. File might have been truncated or replaced.")
                self.last_position = 0
                self.check_file()  # Recheck the file from the beginning
            elif self.last_check_had_content:
                self.debug_callback("No new content in log file.")
                self.last_check_had_content = False
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
                event_type, data, killstreak = event_data
                self.debug_callback(f"Event detected: {event_type}, Data: {data}, Killstreak: {killstreak}")
    
                # Get the current scene 
                current_scene = self.get_current_scene_with_retry()
                if current_scene: 
                    if event_type == "spawned":
                        # For spawn events, 'data' is the class name
                        self.obs_effect_queue.put((current_scene, event_type, data, killstreak))
                    elif event_type in ["kill", "death"]:
                        # For kill/death events, 'data' is the weapon
                        if data and data not in self.recognized_weapons:
                            self.debug_callback(f"Unrecognized weapon: {data}")
                            data = "unknown weapon"
                        self.obs_effect_queue.put((current_scene, event_type, data, killstreak))
                    else:
                        # For other events, just pass the data as is
                        self.obs_effect_queue.put((current_scene, event_type, data, killstreak))
                else:
                    self.debug_callback("Failed to get current scene. Skipping OBS effect.")
            else:
                self.debug_callback("No event detected for this line.")

    def get_current_scene_with_retry(self):
        if self.current_scene_cache and (self.cache_expiry_time is None or time.time() < self.cache_expiry_time):
            return self.current_scene_cache

        retry_count = 3
        while retry_count > 0:
            current_scene = self.obs_client.get_current_scene()
            if current_scene:
                self.current_scene_cache = current_scene
                self.cache_expiry_time = time.time() + 5  # Cache for 5 seconds
                return current_scene
            retry_count -= 1
            time.sleep(0.1)  # Short delay before retrying
        return None
            
    def trigger_obs_effect(self, event_type, data=None, killstreak=0):
        if self.stop_event.is_set():
            return
    
        if not self.obs_client.connected:
            self.debug_callback("OBS is not connected yet. Skipping effect trigger.")
            return
    
        self.debug_callback(f"Triggering OBS effect: {event_type}" + (f" with {data}" if data else ""))
    
        try:
            current_scene = self.get_current_scene_with_retry()
            if not current_scene:
                self.debug_callback("Failed to get current scene name after retries. Skipping effect.")
                return
    
            # Queue the OBS effect to be processed sequentially, including the current_scene
            self.obs_effect_queue.put((current_scene, event_type, data, killstreak))
    
        except Exception as e:
            self.debug_callback(f"Failed to trigger OBS effect: {str(e)}")
            self.debug_callback(traceback.format_exc())
            
    def process_obs_effects(self):
        while not self.stop_event.is_set():
            try:
                scene, event_type, data, killstreak = self.obs_effect_queue.get(timeout=1)
                self.debug_callback(f"process_obs_effects: Received from queue: scene={scene}, event_type={event_type}, data={data}, killstreak={killstreak}")
    
                source_name = self.overlay_sources.get(event_type)
                if source_name:
                    self._toggle_source_visibility(scene, source_name)
    
                handler = self.event_handlers.get(event_type)
                if handler:
                    handler(scene, data, killstreak)
                else:
                    self._handle_generic_event(scene, event_type, data, killstreak)
    
                self.debug_callback(f"OBS effect for {event_type} triggered successfully")
            except queue.Empty:
                continue
            except Exception as e:
                self.debug_callback(f"Error processing OBS effect: {str(e)}")
                self.debug_callback(traceback.format_exc())
                
    def _toggle_overlay(self, scene, event_type):
        source_name = self.overlay_sources.get(event_type)
        if source_name:
            self.debug_callback(f"_toggle_overlay: Toggling visibility for source_name={source_name} in scene={scene}")
            self._toggle_source_visibility(scene, source_name)
        else:
            self.debug_callback(f"No overlay source found for event type: {event_type}")

    def _toggle_source_visibility(self, scene, source_name):
        try:
            scene_item_id = self.obs_client.get_scene_item_id(scene, source_name)
            if scene_item_id is not None:
                self.debug_callback(f"_toggle_source_visibility: Toggling visibility for source_name={source_name} (ID: {scene_item_id}) in scene={scene}")
                self.obs_client.set_scene_item_enabled(scene, source_name, True)
                # Schedule hiding the source after a delay
                threading.Timer(0.3, lambda: self.obs_client.set_scene_item_enabled(scene, source_name, False)).start()
            else:
                self.debug_callback(f"Error: Could not find scene item ID for source '{source_name}' in scene '{scene}'")
        except Exception as e:
            self.debug_callback(f"Error toggling source visibility: {str(e)}")
            
    def display_notification(self, scene, source_name, text):
        try:
            # Set the notification text
            self.obs_client.set_input_settings("NotificationText", {"text": text})
    
            # Get the scene item IDs (with retry logic)
            notification_text_id = self.obs_client.get_scene_item_id_with_retry(scene, "NotificationText")
            notification_overlay_id = self.obs_client.get_scene_item_id_with_retry(scene, "NotificationOverlay")
            event_overlay_id = self.obs_client.get_scene_item_id_with_retry(scene, source_name) if source_name else None
    
            # Log the retrieved IDs for debugging
            self.debug_callback(f"display_notification: Retrieved IDs - notification_text_id: {notification_text_id}, notification_overlay_id: {notification_overlay_id}, event_overlay_id: {event_overlay_id}")
    
            # Show the image (if available), text notification, and overlay
            if event_overlay_id is not None:
                self.debug_callback(f"display_notification: Enabling event_overlay_id={event_overlay_id} in scene={scene}") 
                self.obs_client.set_scene_item_enabled(scene, source_name, True)
                # Schedule hiding of the event overlay
                threading.Timer(self.notification_duration, lambda: self.obs_client.set_scene_item_enabled(scene, source_name, False)).start()
            else:
                self.debug_callback(f"Warning: Could not find source '{source_name}' in scene '{scene}'")
    
            if notification_text_id is not None and notification_overlay_id is not None:
                self.debug_callback(f"display_notification: Enabling notification_text_id={notification_text_id} and notification_overlay_id={notification_overlay_id} in scene={scene}")
                self.obs_client.set_scene_item_enabled(scene, "NotificationText", True)
                self.obs_client.set_scene_item_enabled(scene, "NotificationOverlay", True)
                # Schedule hiding of both the notification text and overlay
                threading.Timer(self.notification_duration, lambda: self._hide_notification(scene)).start()
            else:
                self.debug_callback(f"Warning: Could not find NotificationText or NotificationOverlay in scene '{scene}'")
        except Exception as e:
            self.debug_callback(f"Error displaying notification: {str(e)}")
            self.debug_callback(traceback.format_exc())
    
    def _hide_notification(self, scene):
        try:
            # Hide both the NotificationText and NotificationOverlay
            self.obs_client.set_scene_item_enabled(scene, "NotificationText", False)
            self.obs_client.set_scene_item_enabled(scene, "NotificationOverlay", False)
        except Exception as e:
            self.debug_callback(f"Error hiding notification: {str(e)}")
        
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
                current_scene = self.obs_client.get_current_scene()
    
                if current_scene:
                    for source_name in class_media_sources.values():
                        if self.use_images:
                            scene_item_id = self.obs_client.get_scene_item_id_with_retry(current_scene, source_name)
                            if scene_item_id is not None:
                                self.obs_client.set_scene_item_enabled(current_scene, source_name, source_name == media_source_name)
                            else:
                                self.debug_callback(f"Could not find scene item ID for source '{source_name}' in scene '{current_scene}'")
                        else:
                            self.obs_client.set_input_mute(source_name, source_name != media_source_name)
    
                    time.sleep(0.1)
                else:
                    self.debug_callback("Failed to get current scene name. Skipping class overlay update.")
            else:
                self.debug_callback(f"Unknown class: {class_name}")
        except Exception as e:
            self.debug_callback(f"Error updating class overlay: {str(e)}")
            self.debug_callback(traceback.format_exc())
            
    def _handle_spawn_event(self, scene, class_name, killstreak):
        notification_text = f"{self.player_name} spawned as {class_name}"

        # Log scene_item_id before calling display_notification
        spawned_source_name = self.overlay_sources["spawned"]
        scene_item_id_before = self.obs_client.get_scene_item_id(scene, spawned_source_name)
        self.debug_callback(f"_handle_spawn_event: scene={scene}, class_name={class_name}, killstreak={killstreak}, scene_item_id_before={scene_item_id_before}")

        self.display_notification(scene, spawned_source_name, notification_text)

        # Log scene_item_id after calling display_notification
        scene_item_id_after = self.obs_client.get_scene_item_id(scene, spawned_source_name)
        self.debug_callback(f"_handle_spawn_event: scene_item_ids after display_notification: {scene_item_id_after}")

        self.update_class_overlay(class_name)
        
    def _handle_kill_event(self, scene, weapon, killstreak):
        self.update_killstreak_display(killstreak)
        notification_text = f"{self.player_name} killed with {weapon}"
        self.display_notification(scene, self.overlay_sources["kill"], notification_text)
    
    def _handle_death_event(self, scene, weapon, killstreak):
        self.update_killstreak_display(0)
        notification_text = f"{self.player_name} died"
        self.display_notification(scene, self.overlay_sources["death"], notification_text)
    
    def _handle_capture_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} captured a point!"
        self.display_notification(scene, self.overlay_sources["capture"], notification_text)
    
    def _handle_intel_event(self, scene, weapon, killstreak):
        action = "picked up" if "picked_up_intel" in self.current_event else "dropped" if "dropped_intel" in self.current_event else "has"
        notification_text = f"{self.player_name} {action} the intelligence!"
        source_name = self.overlay_sources.get(self.current_event, "NotificationOverlay")
        self.display_notification(scene, source_name, notification_text)
    
    def _handle_build_event(self, scene, weapon, killstreak):
        object_type = self.current_event.split('_')[1]
        notification_text = f"{self.player_name} built a {object_type}!"
        source_name = self.overlay_sources.get(self.current_event, "NotificationOverlay")
        self.display_notification(scene, source_name, notification_text)
    
    def _handle_destroy_event(self, scene, weapon, killstreak):
        object_type = self.current_event.split('_')[1]
        notification_text = f"{self.player_name} destroyed a {object_type}!"
        source_name = self.overlay_sources.get(self.current_event, "NotificationOverlay")
        self.display_notification(scene, source_name, notification_text)
    
    def _handle_domination_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} dominated an enemy!"
        self.display_notification(scene, self.overlay_sources["domination"], notification_text)
    
    def _handle_dominated_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} was dominated!"
        self.display_notification(scene, self.overlay_sources["dominated"], notification_text)
    
    def _handle_revenge_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} got revenge!"
        self.display_notification(scene, self.overlay_sources["revenge"], notification_text)
    
    def _handle_status_effect_event(self, scene, weapon, killstreak):
        effect = self.current_event
        notification_text = f"{self.player_name} was {effect}!"
        source_name = self.overlay_sources.get(effect, "NotificationOverlay")
        self.display_notification(scene, source_name, notification_text)
    
    def _handle_medic_event(self, scene, weapon, killstreak):
        action = "deployed Übercharge" if "uber" in self.current_event else "deployed charge"
        notification_text = f"{self.player_name} {action}!"
        source_name = self.overlay_sources["medic_uber"] if "uber" in self.current_event else self.overlay_sources["medic_charge_deployed"]
        self.display_notification(scene, source_name, notification_text)
    
    def _handle_spy_event(self, scene, weapon, killstreak):
        action = "completed disguise" if "disguise" in self.current_event else "performed a backstab"
        notification_text = f"{self.player_name} {action}!"
        source_name = self.overlay_sources["spy_disguise_complete"] if "disguise" in self.current_event else self.overlay_sources["spy_backstab"]
        self.display_notification(scene, source_name, notification_text)
    
    def _handle_engineer_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} used a teleporter!"
        self.display_notification(scene, self.overlay_sources["engineer_teleported"], notification_text)
    
    def _handle_sniper_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} got a headshot!"
        self.display_notification(scene, self.overlay_sources["sniper_headshot"], notification_text)
    
    def _handle_pyro_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} performed an airblast!"
        self.display_notification(scene, self.overlay_sources["pyro_airblast"], notification_text)
    
    def _handle_demoman_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name}'s sticky trap was triggered!"
        self.display_notification(scene, self.overlay_sources["demoman_sticky_trap_triggered"], notification_text)
    
    def _handle_heavy_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} is eating a sandvich!"
        self.display_notification(scene, self.overlay_sources["heavy_eating"], notification_text)
    
    def _handle_crit_event(self, scene, weapon, killstreak):
        crit_type = "Crit" if "crit_boosted" in self.current_event else "Mini-crit"
        notification_text = f"{self.player_name} is {crit_type} boosted!"
        source_name = self.overlay_sources["crit_boosted"] if "crit_boosted" in self.current_event else self.overlay_sources["mini_crit_boosted"]
        self.display_notification(scene, source_name, notification_text)
    
    def _handle_stat_event(self, scene, weapon, killstreak):
        stat_type = self.current_event
        notification_text = f"{self.player_name} {stat_type}!"
        self.display_notification(scene, self.overlay_sources.get(stat_type, "NotificationOverlay"), notification_text)
    
    def _handle_game_event(self, scene, weapon, killstreak):
        event_type = self.current_event.replace('_', ' ').capitalize()
        notification_text = f"{event_type}!"
        self.display_notification(scene, self.overlay_sources.get(self.current_event, "NotificationOverlay"), notification_text)
    
    def _handle_first_blood_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} got First Blood!"
        self.display_notification(scene, self.overlay_sources["first_blood"], notification_text)
    
    def _handle_multi_kill_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} got a Multi-kill!"
        self.display_notification(scene, self.overlay_sources["multi_kill"], notification_text)
    
    def _handle_killstreak_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} is on a {killstreak} killstreak!"
        self.display_notification(scene, self.overlay_sources["killstreak"], notification_text)
    
    def _handle_objective_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} blocked a capture point!"
        self.display_notification(scene, self.overlay_sources["cap_point_blocked"], notification_text)
    
    def _handle_teleporter_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} used a teleporter!"
        self.display_notification(scene, self.overlay_sources["teleporter_used"], notification_text)
    
    def _handle_sap_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} sapped an enemy building!"
        self.display_notification(scene, self.overlay_sources["sapped_building"], notification_text)
    
    def _handle_uber_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} deployed Übercharge!"
        self.display_notification(scene, self.overlay_sources["ubercharge_deployed"], notification_text)
    
    def _handle_deflect_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} deflected a projectile!"
        self.display_notification(scene, self.overlay_sources["deflected_projectile"], notification_text)
    
    def _handle_environment_kill_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} got an environmental kill!"
        self.display_notification(scene, self.overlay_sources["environment_kill"], notification_text)
    
    def _handle_flag_event(self, scene, weapon, killstreak):
        action = self.current_event.split('_')[1]
        notification_text = f"{self.player_name} {action} the flag!"
        self.display_notification(scene, self.overlay_sources.get(self.current_event, "NotificationOverlay"), notification_text)
    
    def _handle_cart_event(self, scene, weapon, killstreak):
        action = "pushed" if "pushed" in self.current_event else "blocked"
        notification_text = f"{self.player_name} {action} the cart!"
        source_name = self.overlay_sources["cart_pushed"] if "pushed" in self.current_event else self.overlay_sources["cart_blocked"]
        self.display_notification(scene, source_name, notification_text)
    
    def _handle_point_event(self, scene, weapon, killstreak):
        action = "captured" if "captured" in self.current_event else "defended"
        notification_text = f"{self.player_name} {action} a point!"
        source_name = self.overlay_sources["point_captured"] if "captured" in self.current_event else self.overlay_sources["point_defended"]
        self.display_notification(scene, source_name, notification_text)
    
    def _handle_mvm_event(self, scene, weapon, killstreak):
        if "credit" in self.current_event:
            notification_text = f"{self.player_name} collected credits!"
            source_name = self.overlay_sources["mvm_credit_collected"]
        elif "wave" in self.current_event:
            notification_text = "Wave completed!"
            source_name = self.overlay_sources["mvm_wave_completed"]
        elif "bomb" in self.current_event:
            notification_text = "Bomb reset!"
            source_name = self.overlay_sources["mvm_bomb_reset"]
        else:
            notification_text = "MvM event occurred!"
            source_name = "NotificationOverlay"
        self.display_notification(scene, source_name, notification_text)
    
    def _handle_halloween_event(self, scene, weapon, killstreak):
        if "boss" in self.current_event:
            notification_text = f"{self.player_name} killed the Halloween boss!"
            source_name = self.overlay_sources["halloween_boss_killed"]
        elif "gift" in self.current_event:
            notification_text = f"{self.player_name} grabbed a Halloween gift!"
            source_name = self.overlay_sources["halloween_gift_grabbed"]
        else:
            notification_text = "Halloween event occurred!"
            source_name = "NotificationOverlay"
        self.display_notification(scene, source_name, notification_text)
    
    def _handle_upgrade_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} upgraded their gear!"
        self.display_notification(scene, self.overlay_sources["player_upgraded"], notification_text)
    
    def _handle_resupply_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} resupplied!"
        self.display_notification(scene, self.overlay_sources["player_resupplied"], notification_text)
    
    def _handle_mvp_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} is the MVP!"
        self.display_notification(scene, self.overlay_sources["player_mvp"], notification_text)
    
    def _handle_taunt_kill_event(self, scene, weapon, killstreak):
        notification_text = f"{self.player_name} got a taunt kill!"
        self.display_notification(scene, self.overlay_sources["taunt_kill"], notification_text)
    
    def _handle_contract_event(self, scene, weapon, killstreak):
        if "completed" in self.current_event:
            notification_text = f"{self.player_name} completed a contract!"
            source_name = self.overlay_sources["contract_completed"]
        elif "points" in self.current_event:
            notification_text = f"{self.player_name} gained contract points!"
            source_name = self.overlay_sources["contract_points_gained"]
        else:
            notification_text = "Contract event occurred!"
            source_name = "NotificationOverlay"
        self.display_notification(scene, source_name, notification_text)
    
    def _handle_generic_event(self, scene, event_type, data, killstreak):
        notification_text = f"{self.player_name} {event_type.replace('_', ' ')}"
        if data:
            notification_text += f" with {data}"
        self.display_notification(scene, self.overlay_sources.get(event_type, "NotificationOverlay"), notification_text)
        
    def update_killstreak_display(self, killstreak):
        try:
            self.debug_callback(f"Updating killstreak display to {killstreak}")
            response = self.obs_client.set_input_settings("KillstreakText", {"text": f"Killstreak: {killstreak}"})
            if not (response and 'd' in response and 'requestStatus' in response['d'] and response['d']['requestStatus']['result']):
                self.debug_callback(f"Failed to update killstreak display. Response: {response}")
        except Exception as e:
            self.debug_callback(f"Error updating killstreak display: {str(e)}")
    


    
            
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

def main():
    root = tk.Tk()
    app = TF2OBSPlugin(root)
    
    try:
        root.mainloop()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        app.is_running = False
        try:
            root.destroy()
        except tk.TclError:
            pass  # Ignore Tkinter errors during shutdown

if __name__ == "__main__":
    main()        