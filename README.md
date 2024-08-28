Here's an improved and updated README for the TF2-OBS-Plugin:

```markdown
# TF2-OBS-Plugin

Enhance your Team Fortress 2 streaming experience with dynamic overlays and scene transitions based on in-game actions!

## Overview

TF2-OBS-Plugin is a Python-based tool that integrates Team Fortress 2 with OBS Studio, providing real-time visual feedback for various in-game events. This plugin monitors the TF2 console log and triggers corresponding actions in OBS, creating a more engaging and interactive streaming experience.

## Key Features

- **Real-time Event Monitoring**: Watches TF2 console log for various in-game events (kills, deaths, captures, etc.).
- **Dynamic OBS Integration**: Automatically toggles visibility of scenes and sources in response to game events.
- **Extensive Event Coverage**: Supports a wide range of TF2 events, from basic kills to specific class actions.
- **Customizable Configuration**: Easily set up your TF2 log file path, Steam username, and OBS connection details.
- **Live Debug Output**: Provides real-time feedback on connection status and detected events.
- **Flexible Overlay System**: Works independently of your current OBS scene, allowing for versatile stream layouts.

## How It Works

1. The plugin continuously reads the TF2 console log in real-time.
2. It identifies relevant events using regex patterns matched against log messages.
3. When an event is detected, it sends commands to OBS via WebSocket to toggle the visibility of corresponding sources.

## Setup Instructions

### OBS Studio Setup

1. Install the obs-websocket plugin for OBS Studio.
2. In OBS, go to Tools -> WebSocket Server Settings to configure your server.
3. Create a new scene called "Tf2Scene" for your main TF2 gameplay.
4. Add the following sources to your OBS setup:

   - KillOverlay (Media Source)
   - DeathOverlay (Media Source)
   - SuicideOverlay (Media Source)
   - CaptureOverlay (Media Source)
   - NotificationOverlay (Media Source)
   - KillstreakText (Text GDI+ Source)
   - NotificationText (Text GDI+ Source)
   - ScoutOverlay, SoldierOverlay, PyroOverlay, etc. (Media Sources for each class)
   - PickedIntel, DroppedIntel, HasIntel (Media Sources)
   - BuiltSentry, BuiltDispenser, BuiltTeleEntrance, BuiltTeleExit (Media Sources)
   - DestroyedSentry, DestroyedDispenser, DestroyedTeleEntrance, DestroyedTeleExit (Media Sources)
   - Domination, Dominated, Revenge, Stunned, Jarated, Milked, Extinguished, Spawned, etc. (Media Sources for various events)

   (Refer to the full list in the plugin code for all required sources)

### Team Fortress 2 Setup

1. Add the following launch options to TF2:
   ```
   -condebug -console -log_verbose_enable 1
   ```
   This enables detailed console logging necessary for the plugin.

### Plugin Setup

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/TF2-OBS-Plugin.git
   ```
2. Install the required Python libraries:
   ```
   pip install -r requirements.txt
   ```
3. Run the plugin:
   ```
   python main.py
   ```
4. In the GUI, enter your TF2 log file path, Steam username, and OBS WebSocket details.
5. Click "Connect to OBS" and then "Start Monitoring" to begin.

## Important Notes

- Ensure that the names of scenes and sources in OBS match exactly with those listed in the plugin code.
- The plugin toggles source visibility independently of the current scene, allowing for flexible OBS layouts.
- Some users have reported issues with certain OBS WebSocket Python libraries. If you encounter connection problems, you may need to modify the WebSocket connection code.

## Troubleshooting

- If you're having trouble connecting to OBS, double-check your WebSocket server settings in OBS and ensure they match what you've entered in the plugin.
- Make sure your TF2 launch options are set correctly to enable detailed logging.
- Check the debug output in the plugin GUI for any error messages or connection issues.

## Contributing

Contributions to improve the plugin are welcome! Please feel free to submit pull requests or open issues for any bugs or feature requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Thanks to the OBS Project for creating OBS Studio and the WebSocket plugin.
- Credit to mud_punk for their insights on OBS WebSocket connections in Python.
```
