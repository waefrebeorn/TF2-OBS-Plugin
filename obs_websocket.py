import websocket
import json
import base64
import hashlib
import time
import traceback
import queue
import random
import threading
import ssl
from cachetools import TTLCache 

class OBSWebSocket:
    def __init__(self, host, port, password, debug_callback=None):
        self.host = host
        self.port = port
        self.password = password
        self.ws = None
        self.connected = False
        self.scene_item_ids = {}
        self.debug_callback = debug_callback or (lambda x: print(x))
        self.last_response = None
        self.response_queue = queue.Queue()
        self.event_queue = queue.Queue()
        self.receive_thread = None
        self.pending_requests = {}
        self.cache = TTLCache(maxsize=100, ttl=60)  # Cache up to 100 items for 60 seconds
        self.cache_lock = threading.Lock()  # Add this line 


        
    def connect(self):
        url = f"ws://{self.host}:{self.port}"
        self.ws = websocket.WebSocket(sslopt={"cert_reqs": ssl.CERT_NONE})
        try:
            self.debug_callback(f"Attempting to connect to {url}")
            self.ws.connect(url)
            self.debug_callback("WebSocket connection established")
            
            self.debug_callback("Attempting authentication")
            self._auth()
            self.debug_callback("Authentication successful")
    
            self.connected = True  # Set connected to True after successful authentication
    
            self.debug_callback("Starting receive thread")
            self.receive_thread = threading.Thread(target=self._receive_loop)
            self.receive_thread.daemon = True
            self.receive_thread.start()
    
            # Verify connection with a test request
            #self.debug_callback("Sending test request (GetVersion)")
            #test_response = self.send_request("GetVersion", timeout=5)
            #self.debug_callback(f"Test response received: {test_response}")
            
            #if test_response and 'd' in test_response and 'responseData' in test_response['d']:
            #    self.debug_callback(f"Connected to OBS successfully! Version: {test_response['d']['responseData']['obsVersion']}")
            #else:
            #    raise Exception("Failed to verify OBS connection: Invalid response format")
    
            self.debug_callback("Caching scene item IDs")
            self.cache_scene_item_ids()
            self.debug_callback("Connection process completed successfully")
        except websocket.WebSocketConnectionClosedException:
            self.debug_callback("WebSocket connection was closed unexpectedly")
            self.connected = False
            raise
        except Exception as e:
            self.debug_callback(f"Failed to connect to OBS: {str(e)}")
            self.debug_callback(traceback.format_exc())
            self.connected = False
            raise
        
    def _build_auth_string(self, salt, challenge):
        secret = base64.b64encode(hashlib.sha256((self.password + salt).encode('utf-8')).digest())
        auth = base64.b64encode(hashlib.sha256(secret + challenge.encode('utf-8')).digest()).decode('utf-8')
        return auth

    def _auth(self):
        self.debug_callback("Waiting for initial message from OBS")
        message = self.ws.recv()
        self.debug_callback(f"Received initial message: {message}")
        result = json.loads(message)
        
        if 'd' not in result or 'authentication' not in result['d']:
            raise Exception("Invalid initial message format from OBS")
        
        salt = result['d']['authentication']['salt']
        challenge = result['d']['authentication']['challenge']
        
        self.debug_callback("Generating authentication string")
        auth = self._build_auth_string(salt, challenge)
    
        payload = {
            "op": 1,
            "d": {
                "rpcVersion": 1,
                "authentication": auth,
                "eventSubscriptions": 33
            }
        }
        
        self.debug_callback("Sending authentication payload")
        self.ws.send(json.dumps(payload))
        
        self.debug_callback("Waiting for authentication response")
        message = self.ws.recv()
        self.debug_callback(f"Received authentication response: {message}")
        auth_response = json.loads(message)
        
        if auth_response['op'] != 2:
            raise Exception(f"Authentication failed. Response: {auth_response}")
        
        self.debug_callback("Authentication successful")
        
    def cache_scene_item_ids(self):
        """Caches scene item IDs for all scenes and sources."""
        response = self.send_request("GetSceneList")
        if response and 'd' in response and 'scenes' in response['d']:
            for scene in response['d']['scenes']:
                scene_name = scene['sceneName']
                for source in scene.get('sources', []):
                    source_name = source['name']
                    cache_key = f"{scene_name}:{source_name}"
                    self.scene_item_ids[cache_key] = source['id']

    def _debug(self, message):
        self.debug_queue.put(message)
        if self.debug_callback:
            self.debug_callback(message)

    def _receive_loop(self):
        while self.connected:
            try:
                message = self.ws.recv()
                data = json.loads(message)
                if data['op'] == 7:  # Response
                    request_id = data['d']['requestId']
                    if request_id in self.pending_requests:
                        self.pending_requests[request_id].put(data)
                    else:
                        self.response_queue.put(data)
                elif data['op'] == 5:  # Event
                    self.event_queue.put(data)
    
                    # Invalidate cache for relevant events
                    event_type = data['d'].get('eventType')
                    if event_type in [
                        'SceneItemAdded', 'SceneItemRemoved', 'SceneItemVisibilityChanged',
                        'SceneItemTransformChanged', 'SceneItemSelected', 'SceneItemDeselected'
                    ]:
                        self.clear_scene_item_id_cache()
                        self.debug_callback(f"Invalidated scene item ID cache due to {event_type} event.")
    
                self.debug_callback(f"Processed message from OBS: {json.dumps(data, indent=2)}")

            except Exception as e:
                self.debug_callback(f"Error in receive loop: {str(e)}")
                time.sleep(0.1)
                
    def send_request(self, request_type, request_data=None, timeout=10):
        if not self.ws:
            self.debug_callback("WebSocket is not initialized. Cannot send request.")
            return None
    
        if request_data is None:
            request_data = {}
        request_id = f"{request_type}Request"
        payload = {
            "op": 6,
            "d": {
                "requestId": request_id,
                "requestType": request_type,
                "requestData": request_data
            }
        }
        self.debug_callback(f"Sending request to OBS: {json.dumps(payload, indent=2)}")
        
        response_event = threading.Event()
        response_data = []
        
        def response_callback(data):
            response_data.append(data)
            response_event.set()
        
        self.pending_requests[request_id] = response_callback
        
        try:
            self.ws.send(json.dumps(payload))
            
            if response_event.wait(timeout):
                response = response_data[0]
                self.last_response = response
                self.debug_callback(f"Received response from OBS: {json.dumps(self.last_response, indent=2)}")
                return response
            else:
                self.debug_callback(f"Timed out waiting for response to {request_type}")
                return None
        except Exception as e:
            self.debug_callback(f"Error sending request: {str(e)}")
            return None
        finally:
            del self.pending_requests[request_id]
        
    def _receive_loop(self):
        while self.connected:
            try:
                message = self.ws.recv()
                self.debug_callback(f"Raw message received: {message}")
                data = json.loads(message)
                if data['op'] == 7:  # Response
                    request_id = data['d']['requestId']
                    if request_id in self.pending_requests:
                        self.pending_requests[request_id](data)
                    else:
                        self.response_queue.put(data)
                elif data['op'] == 5:  # Event
                    self.event_queue.put(data)
                self.debug_callback(f"Processed message from OBS: {json.dumps(data, indent=2)}")
            except websocket.WebSocketConnectionClosedException:
                self.debug_callback("WebSocket connection closed. Attempting to reconnect...")
                self.reconnect()
                break
            except json.JSONDecodeError:
                self.debug_callback(f"Failed to decode message: {message}")
            except Exception as e:
                self.debug_callback(f"Error in receive loop: {str(e)}")
                self.debug_callback(traceback.format_exc())
                time.sleep(1)
        self.debug_callback("Receive loop ended")
               
    def reconnect(self):
        self.connected = False
        try:
            self.ws.close()
        except:
            pass
        
        retry_count = 0
        max_retries = 5
        while retry_count < max_retries:
            try:
                self.connect()
                return
            except Exception as e:
                retry_count += 1
                self.debug_callback(f"Reconnection attempt {retry_count} failed: {str(e)}")
                time.sleep(5)
        
        self.debug_callback("Failed to reconnect after multiple attempts")
        
    def set_current_scene(self, scene_name):
        return self.send_request("SetCurrentProgramScene", {"sceneName": scene_name})

        
    def set_scene_item_enabled(self, scene_name, source_name, enabled):
        scene_item_id = self.get_scene_item_id(scene_name, source_name)
        if scene_item_id is None:
            self.debug_callback(f"Error: Could not find scene item ID for source '{source_name}' in scene '{scene_name}'")
            return False
    
        response = self.send_request("SetSceneItemEnabled", {
            "sceneName": scene_name,
            "sceneItemId": scene_item_id,
            "sceneItemEnabled": enabled
        })
    
        if response and 'd' in response and 'requestStatus' in response['d']:
            return response['d']['requestStatus']['result']
        else:
            self.debug_callback(f"Error: Invalid response from SetSceneItemEnabled. Full response: {json.dumps(response, indent=2)}")
            return False
            
    def set_input_mute(self, input_name, muted):
        return self.send_request("SetInputMute", {
            "inputName": input_name,
            "inputMuted": muted
        })

    def set_text_gdi_plus_properties(self, source_name, text):
        return self.send_request("SetTextGDIPlusProperties", {
            "source": source_name,
            "text": text
        })

    def get_current_scene(self):
        max_retries = 25  # Maximum number of retries
        retry_delay = 0.2  # Delay between retries in seconds

        for _ in range(max_retries):
            response = self.send_request("GetCurrentProgramScene")

            if response and 'd' in response:
                if 'responseData' in response['d'] and 'currentProgramSceneName' in response['d']['responseData']:
                    # Standard case: 'currentProgramSceneName' is present
                    return response['d']['responseData']['currentProgramSceneName']
                elif 'requestType' in response['d'] and response['d']['requestType'] == 'GetSceneItemId':
                    # Workaround: 'currentProgramSceneName' is missing, but we got a 'GetSceneItemId' response
                    # Use GetCurrentScene to get the actual scene name
                    scene_response = self.send_request("GetCurrentScene")
                    if scene_response and 'd' in scene_response and 'name' in scene_response['d']:
                        return scene_response['d']['name']
                elif 'eventType' in response['d'] and response['d']['eventType'] == 'InputSettingsChanged':
                    # Filter out 'InputSettingsChanged' events
                    continue  # Retry if it's an InputSettingsChanged event
                else:
                    # Log a warning or error message indicating an unexpected response structure
                    if hasattr(self, 'debug_callback'):
                        self.debug_callback(f"Warning: Unexpected response from GetCurrentProgramScene. Full response: {self.last_response}")

            time.sleep(retry_delay)  # Wait before retrying
            
                # Return None or a default scene name if all retries fail
        return None
        
    def get_current_scene_with_retry(self):
        retry_count = 3
        while retry_count > 0:
            # Try GetCurrentProgramScene first
            current_scene_data = self.get_current_program_scene()
            if current_scene_data and 'currentProgramSceneName' in current_scene_data:
                return current_scene_data['currentProgramSceneName']

            # If that fails, try GetCurrentScene as a fallback
            current_scene_data = self.get_current_scene()
            if current_scene_data and 'name' in current_scene_data:
                return current_scene_data['name']

            retry_count -= 1
            time.sleep(0.1)  # Short delay before retrying
        return None

    def get_scene_item_id(self, scene_name, source_name):
        response = self.send_request("GetSceneItemId", {
            "sceneName": scene_name,
            "sourceName": str(source_name)  # Convert to string
        })
    
        if response and 'd' in response and 'responseData' in response['d']:
            return response['d']['responseData'].get('sceneItemId')
        else:
            self.debug_callback(f"Error: Could not get scene item ID for source '{source_name}' in scene '{scene_name}'")
            return None
        
    def clear_scene_item_id_cache(self):
        with self.cache_lock:  # Acquire the lock before clearing the cache
            self.scene_item_ids.clear()
        if hasattr(self, 'debug_callback'):
            self.debug_callback("Scene item ID cache cleared.")
            
    def get_scene_item_id_with_retry(self, scene_name, source_name, max_retries=5, base_delay=0.1, max_delay=10):
        delay = base_delay
        for attempt in range(max_retries):
            scene_item_id = self.get_scene_item_id(scene_name, source_name)
            if scene_item_id is not None:
                return scene_item_id
    
            jitter = random.uniform(0, delay * 0.5)
            time.sleep(delay + jitter)
    
            # Exponential backoff with a maximum delay
            delay *= 2
            delay = min(delay, max_delay)
    
        self.debug_callback(f"Failed to get scene item ID for source '{source_name}' in scene '{scene_name}' after {max_retries} attempts")
        return None
        
    def set_input_settings(self, input_name, settings):
        return self.send_request("SetInputSettings", {
            "inputName": input_name,
            "inputSettings": settings
        })

    def get_scene_item_properties(self, scene_name, item_id):
        """
        Gets the properties of a scene item in the specified scene.
        Args:
            scene_name (str): The name of the scene containing the item.
            item_id (int or str): The ID of the scene item.
        Returns:
            dict: A dictionary containing the scene item's properties, or None if an error occurs.
        """ 
        # Convert item_id to string if it's an integer
        if isinstance(item_id, int):
            item_id = str(item_id)
    
        response = self.send_request("GetSceneItemProperties", {
            "sceneName": scene_name,
            "itemId": item_id
        })
    
        if response and 'd' in response and 'sceneItemProperties' in response['d']:
            return response['d']['sceneItemProperties']
        else:
            if hasattr(self, 'debug_callback'):
                self.debug_callback(f"Warning: Failed to get scene item properties for item ID {item_id} in scene '{scene_name}'. Full response: {self.last_response}")
            else:
                print(f"Warning: Failed to get scene item properties for item ID {item_id} in scene '{scene_name}'. Full response: {self.last_response}")
            return None
                       
    def close(self):
        self.connected = False
        if self.ws:
            self.ws.close()
        if self.receive_thread:
            self.receive_thread.join()
            
    def clear_scene_item_id_cache(self):
        self.scene_item_ids.clear()
        if hasattr(self, 'debug_callback'):
            self.debug_callback("Scene item ID cache cleared.")
    
    def get_last_response(self):
        """Returns the last response received from OBS."""
        return self.last_response