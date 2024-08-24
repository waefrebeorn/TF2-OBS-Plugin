import websocket
import json
import base64
import hashlib

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