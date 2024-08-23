# TF2-OBS-Plugin
This code creates a **TF2 OBS Plugin** that enhances your Team Fortress 2 streaming experience by integrating with OBS Studio. 

**Key Features:**

* **Monitors TF2 console log:** Watches for in-game events like kills, deaths, and suicides.
* **Triggers OBS scenes and sources:** Automatically switches scenes or enables/disables overlays in response to events.
* **Customizable:** Configure your TF2 log file path, Steam username, OBS connection details, and more.
* **Real-time debug output:** Provides feedback on connection status and events in a clear and concise manner.

**How it works:**

* The plugin reads the TF2 console log in real-time.
* It identifies relevant events based on specific patterns in the log messages.
* When an event is triggered, it sends commands to OBS via WebSocket to change scenes or manipulate sources.

**Enhance your TF2 streams with dynamic overlays and scene transitions based on your in-game actions!** 
