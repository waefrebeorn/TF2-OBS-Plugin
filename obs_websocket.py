import websocket
import json
import base64
import hashlib
import time
import traceback

class OBSWebSocket:
    def __init__(self, host, port, password):
        self.host = host
        self.port = port
        self.password = password
        self.ws = None
        self.connected = False
        self.scene_item_ids = {}  # Initialize the cache

    def connect(self):
        url = f"ws://{self.host}:{self.port}"
        self.ws = websocket.WebSocket()
        self.ws.connect(url)
        self._auth()

        # Cache scene item IDs after successful connection
        self.cache_scene_item_ids()

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
        response = self.ws.recv()  # Store the response
        self.last_response = json.loads(response)  # Update the last_response attribute
        return self.last_response

    def set_current_scene(self, scene_name):
        return self.send_request("SetCurrentProgramScene", {"sceneName": scene_name})

    def set_scene_item_enabled(self, scene_name, source_name, enabled):
            scene_item_id = self.get_scene_item_id_with_retry(scene_name, source_name)
            if scene_item_id is None:
                print(f"Error: Could not find scene item ID for source '{source_name}' in scene '{scene_name}'")
                return False
    
            response = self.send_request("SetSceneItemEnabled", {
                "sceneName": scene_name,
                "sceneItemId": scene_item_id,
                "sceneItemEnabled": enabled
            })
    
            if response and 'd' in response:
                if 'requestStatus' in response['d']:
                    # If 'requestStatus' is available, use its 'result' for success indication
                    return response['d']['requestStatus']['result']
                elif 'eventData' in response['d'] and 'sceneItemEnabled' in response['d']['eventData']:
                    # If both 'eventData' and 'sceneItemEnabled' are present, use them
                    return response['d']['eventData']['sceneItemEnabled'] == enabled
                else:
                    # Log a warning or error message with the full OBS response for debugging
                    if hasattr(self, 'debug_callback'):
                        self.debug_callback(f"Warning: 'sceneItemEnabled' or 'eventData' missing from SetSceneItemEnabled response. Full response: {self.last_response}")
                    else:
                        print(f"Warning: 'sceneItemEnabled' or 'eventData' missing from SetSceneItemEnabled response. Full response: {self.last_response}")
    
            # Return False if none of the above conditions are met (indicating an error)
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
                    else:
                        print(f"Warning: Unexpected response from GetCurrentProgramScene. Full response: {self.last_response}")
    
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
        """Gets the scene item ID, first checking the cache, then sending a request if not found."""
        cache_key = f"{scene_name}:{source_name}"
        scene_item_id = self.scene_item_ids.get(cache_key)

        if scene_item_id is not None:
            return scene_item_id

        max_retries = 25  # Maximum number of retries
        retry_delay = 0.1  # Delay between retries in seconds

        for _ in range(max_retries):
            response = self.send_request("GetSceneItemId", {
                "sceneName": scene_name,
                "sourceName": source_name
            })

            if response and 'd' in response and 'responseData' in response['d']:
                response_data = response['d']['responseData']
                if 'sceneItemId' in response_data:
                    scene_item_id = response_data['sceneItemId']
                    self.scene_item_ids[cache_key] = scene_item_id  # Cache the ID
                    return scene_item_id
                else:
                    if hasattr(self, 'debug_callback'):
                        self.debug_callback(f"Warning: 'sceneItemId' missing from GetSceneItemId response for source '{source_name}' in scene '{scene_name}'")
                    else:
                        print(f"Warning: 'sceneItemId' missing from GetSceneItemId response for source '{source_name}' in scene '{scene_name}'")

            time.sleep(retry_delay)  # Wait before retrying

        # Return None if all retries fail
        return None

    def get_scene_item_id_with_retry(self, scene_name, source_name, max_retries=25):
        for _ in range(max_retries):
            scene_item_id = self.get_scene_item_id(scene_name, source_name)
            if scene_item_id is not None:
                return scene_item_id
                time.sleep(0.1)  # Short delay between retries within get_scene_item_id_with_retry
        return None

    def set_input_settings(self, input_name, settings):
        return self.send_request("SetInputSettings", {
            "inputName": input_name,
            "inputSettings": settings
        })

    def close(self):
        if self.ws:
            self.ws.close()
        self.connected = False

    def get_last_response(self):
        """Returns the last response received from OBS."""
        return self.last_response