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

**True Irony**
* simpleobsws and obsws-python, the plugins used as requirements in this project are both broken in obs currently and you have to rewrite the hash stuff 
* credit to mud_punk in thread https://obsproject.com/forum/threads/python-script-to-connect-to-obs-websocket-server-help.173395/ for noting the exact code he used
* Please notify the obs team to update documentation and plugin recommendations that use these libraries 

**Enhance your TF2 streams with dynamic overlays and scene transitions based on your in-game actions!** 

**Here's a list of OBS scenes and media sources you need to create based on the provided Python code:**

**Scenes:**

* NotificationScene: This scene will be used specifically for displaying notifications during the game.

**Media Sources:**

* KillOverlay: This media source will be triggered when you get a kill in TF2.

* DeathOverlay: This media source will be triggered when you die in TF2.

* SuicideOverlay: This media source will be triggered when you commit suicide in TF2.

* CaptureOverlay: This media source will be triggered when you capture a point in TF2.

* NotificationOverlay: This media source will be triggered to display general notifications.

* KillstreakText: This is a text source that will display your current killstreak.

* NotificationText: This is a text source that will display the content of notifications.

* ScoutOverlay, SoldierOverlay, PyroOverlay, DemomanOverlay, HeavyOverlay, EngineerOverlay, MedicOverlay, SniperOverlay, SpyOverlay, HaleOverlay: These media sources represent the class overlays that will be displayed based on the class you are currently playing.

* PickedIntel, DroppedIntel, HasIntel: These media sources will be triggered when you pick up, drop, or have the intelligence, respectively.

* BuiltSentry, BuiltDispenser, BuiltTeleEntrance, BuiltTeleExit: These media sources will be triggered when you build a sentry gun, dispenser, teleporter entrance, or teleporter exit, respectively.

* DestroyedSentry, DestroyedDispenser, DestroyedTeleEntrance, DestroyedTeleExit: These media sources will be triggered when you destroy a sentry gun, dispenser, teleporter entrance, or teleporter exit, respectively

* Domination, Dominated, Revenge, Stunned, Jarated, Milked, Extinguished, Spawned, MedicUber, MedicCharge, SpyDisguise, SpyBackstab, EngiTeleport, SniperHeadshot, PyroAirblast, DemoTrap, HeavyEating, CritBoosted, MiniCritBoosted, Damage, Healed, Assist, RoundWin, RoundStalemate, MatchWin, FirstBlood: These media sources correspond to various in-game events and will be triggered accordingly.

**Important Notes:**

Make sure the names of these scenes and sources in OBS match exactly as they are listed here in the code.
The types of media sources (e.g., image, video, text) are not explicitly specified in the code, so you will need to choose appropriate media types based on how you want to visually represent these events in your OBS stream.
Remember to add -condebug to your TF2 launch options to enable detailed console logging, which is necessary for this plugin to work correctly.

The source changes triggered by the TF2 OBS Plugin are *independent of the scene you're currently in.* This means you can have a dedicated "TF2 Scene" with your ScoutOverlay, SoldierOverlay, and other class-specific sources, and the plugin will still be able to control their visibility as needed.

How it works:

* The plugin directly interacts with the OBS sources themselves, turning them on or off (making them visible or invisible) regardless of which scene is active at the moment. This allows you to have a flexible setup where you can design your scenes however you like, and the plugin will handle the dynamic overlay elements on top of that.

Example:

You're in your "TF2 Scene" which already has the ScoutOverlay visible because you're playing as Scout.
You get a kill, triggering the "KillOverlay".
The plugin will temporarily make the KillOverlay visible, even though it might be in a different scene.
After a few seconds (as defined in the code), the KillOverlay will be hidden again, and your "TF2 Scene" with the ScoutOverlay will remain as it was.
Key takeaway: You have full control over your scene design, and the plugin will seamlessly integrate the event-triggered overlays on top of it.