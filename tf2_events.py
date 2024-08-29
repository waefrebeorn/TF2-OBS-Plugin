import re

class TF2Events:
    def __init__(self, player_name):
        self.player_name = player_name
        self.killstreak = 0
        self.current_class = None

    def process_log_line(self, line, debug_callback):
        debug_callback(f"Processing line for player: {self.player_name}")
        debug_callback(f"Line content: {line.strip()}")

        # Check for class config execution
        class_match = re.search(r"'(\w+)\.cfg' not present; not executing\.", line)
        if class_match:
            class_name = class_match.group(1)
            return self._handle_class_change(class_name)

        # Define event patterns
        patterns = [
            (r'(\w+) killed (\w+) with (\w+)(\. \(crit\))?', self._handle_kill),
            (r'(\w+) suicided\.', self._handle_suicide),
            (r'(\w+) captured (\w+)', self._handle_capture),
            (r'(\w+) picked up the intelligence', self._handle_intel_pickup),
            (r'(\w+) dropped the intelligence', self._handle_intel_drop),
            (r'(\w+) has the intelligence!', self._handle_has_intel),
            (r'(\w+) built Object (\w+)', self._handle_build),
            (r'(\w+) destroyed (\w+)\'s (\w+)', self._handle_destroy),
            (r'(\w+) dominated (\w+)', self._handle_domination),
            (r'(\w+) got revenge on (\w+)', self._handle_revenge),
            (r'(\w+) triggered "(.*?)"', self._handle_triggered_event),
            (r'(\w+) joined team "(RED|BLU)"', self._handle_team_change),
            (r'World triggered "Round_Win"', self._handle_round_win),
            (r'World triggered "Round_Stalemate"', self._handle_round_stalemate),
            (r'World triggered "Game_Over"', self._handle_game_over),
            (r'(\w+) drew first blood!', self._handle_first_blood),
            (r'(\w+) is on a killing spree!', self._handle_killstreak_start),
            (r'(\w+) is on a rampage!', self._handle_killstreak_rampage),
            (r'(\w+) is UNSTOPPABLE!', self._handle_killstreak_unstoppable),
            (r'(\w+) is DOMINATING!', self._handle_killstreak_dominating),
            (r'(\w+) is GODLIKE!', self._handle_killstreak_godlike),
            (r'(\w+) lost their killstreak', self._handle_killstreak_end),
            (r'(\w+) defended (\w+)', self._handle_defend),
            (r'(\w+) said "(.*?)"', self._handle_chat),
            (r'(\w+) changed role to (\w+)', self._handle_role_change),
            (r'(\w+) triggered "damage" against "(\w+)" \(damage "(\d+)"\)', self._handle_damage),
            (r'(\w+) triggered "healed" against "(\w+)" \(healing "(\d+)"\)', self._handle_healing),
            (r'(\w+) triggered "captureblocked"', self._handle_capture_blocked),
            (r'(\w+) triggered "pointcaptured"', self._handle_point_captured),
            (r'(\w+) triggered "chargedeployed"', self._handle_charge_deployed),
            (r'(\w+) triggered "teleported"', self._handle_teleported),
            (r'(\w+) triggered "killedobject" \(object "(\w+)"\)', self._handle_object_destroyed),
            (r'(\w+) triggered "jarated"', self._handle_jarated),
            (r'(\w+) triggered "deflect_rocket"', self._handle_deflect),
            (r'(\w+) triggered "player_extinguished"', self._handle_extinguished),
            (r'(\w+) triggered "player_teleported"', self._handle_player_teleported),
            (r'(\w+) triggered "player_stealsandwich"', self._handle_steal_sandwich),
            (r'(\w+) triggered "player_stunned"', self._handle_stunned),
            (r'(\w+) triggered "ubercharge_deployed"', self._handle_ubercharge),
        ]

        # Check each pattern
        for pattern, handler in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return handler(match)

        debug_callback("No matching event found for this line.")
        return None

    def _handle_class_change(self, class_name):
        class_map = {
            "scout": "Scout",
            "soldier": "Soldier",
            "pyro": "Pyro",
            "demoman": "Demoman",
            "heavyweapons": "Heavy",
            "engineer": "Engineer",
            "medic": "Medic",
            "sniper": "Sniper",
            "spy": "Spy"
        }
        self.current_class = class_map.get(class_name.lower(), class_name.capitalize())
        self.killstreak = 0
        return ("spawned", self.current_class, 0)

    def _handle_kill(self, match):
        killer, victim, weapon, is_crit = match.groups()
        is_crit = is_crit is not None

        if killer == self.player_name:
            self.killstreak += 1
            return ("kill", weapon, self.killstreak)
        elif victim == self.player_name:
            self.killstreak = 0
            return ("death", weapon, 0)
        return None

    def _handle_suicide(self, match):
        player = match.group(1)
        if player == self.player_name:
            self.killstreak = 0
            return ("suicide", None, 0)
        return None

    def _handle_capture(self, match):
        player, point = match.groups()
        if player == self.player_name:
            return ("capture", point, None)
        return None

    def _handle_intel_pickup(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("picked_up_intel", None, None)
        return None

    def _handle_intel_drop(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("dropped_intel", None, None)
        return None

    def _handle_has_intel(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("has_intel", None, None)
        return None

    def _handle_build(self, match):
        player, obj_type = match.groups()
        if player == self.player_name:
            return (f"built_{obj_type.lower()}", None, None)
        return None

    def _handle_destroy(self, match):
        destroyer, owner, obj_type = match.groups()
        if destroyer == self.player_name:
            return (f"destroyed_{obj_type.lower()}", None, None)
        return None

    def _handle_domination(self, match):
        dominator, victim = match.groups()
        if dominator == self.player_name:
            return ("domination", victim, None)
        elif victim == self.player_name:
            return ("dominated", dominator, None)
        return None

    def _handle_revenge(self, match):
        player, victim = match.groups()
        if player == self.player_name:
            return ("revenge", victim, None)
        return None

    def _handle_triggered_event(self, match):
        player, event = match.groups()
        if player == self.player_name:
            event_lower = event.lower()
            if "stunned" in event_lower:
                return ("stunned", None, None)
            elif "jarated" in event_lower:
                return ("jarated", None, None)
            elif "milked" in event_lower:
                return ("milked", None, None)
            elif "extinguished" in event_lower:
                return ("extinguished", None, None)
            elif "ubercharge_deployed" in event_lower:
                return ("medic_uber", None, None)
            elif "charge_deployed" in event_lower:
                return ("medic_charge_deployed", None, None)
            elif "disguise_complete" in event_lower:
                return ("spy_disguise_complete", None, None)
            elif "backstab" in event_lower:
                return ("spy_backstab", None, None)
            elif "teleported" in event_lower:
                return ("engineer_teleported", None, None)
            elif "headshot" in event_lower:
                return ("sniper_headshot", None, None)
            elif "airblast" in event_lower:
                return ("pyro_airblast", None, None)
            elif "sticky_trap_triggered" in event_lower:
                return ("demoman_sticky_trap_triggered", None, None)
            elif "player_is_eating" in event_lower:
                return ("heavy_eating", None, None)
            elif "crit_boosted" in event_lower:
                return ("crit_boosted", None, None)
            elif "mini_crit_boosted" in event_lower:
                return ("mini_crit_boosted", None, None)
        return None

    def _handle_team_change(self, match):
        player, team = match.groups()
        if player == self.player_name:
            self.killstreak = 0
            return ("team_change", team, 0)
        return None

    def _handle_round_win(self, match):
        self.killstreak = 0
        return ("round_win", None, 0)

    def _handle_round_stalemate(self, match):
        self.killstreak = 0
        return ("round_stalemate", None, 0)

    def _handle_game_over(self, match):
        self.killstreak = 0
        return ("game_over", None, 0)

    def _handle_first_blood(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("first_blood", None, None)
        return None

    def _handle_killstreak_start(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("killstreak", "start", self.killstreak)
        return None

    def _handle_killstreak_rampage(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("killstreak", "rampage", self.killstreak)
        return None

    def _handle_killstreak_unstoppable(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("killstreak", "unstoppable", self.killstreak)
        return None

    def _handle_killstreak_dominating(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("killstreak", "dominating", self.killstreak)
        return None

    def _handle_killstreak_godlike(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("killstreak", "godlike", self.killstreak)
        return None

    def _handle_killstreak_end(self, match):
        player = match.group(1)
        if player == self.player_name:
            self.killstreak = 0
            return ("killstreak", "end", 0)
        return None

    def _handle_defend(self, match):
        player, point = match.groups()
        if player == self.player_name:
            return ("defend", point, None)
        return None

    def _handle_chat(self, match):
        player, message = match.groups()
        if player == self.player_name:
            return ("chat", message, None)
        return None

    def _handle_role_change(self, match):
        player, new_role = match.groups()
        if player == self.player_name:
            return ("role_change", new_role, None)
        return None

    def _handle_damage(self, match):
        attacker, victim, damage = match.groups()
        if attacker == self.player_name:
            return ("damage", victim, int(damage))
        return None

    def _handle_healing(self, match):
        healer, patient, healing = match.groups()
        if healer == self.player_name:
            return ("healing", patient, int(healing))
        return None

    def _handle_capture_blocked(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("capture_blocked", None, None)
        return None

    def _handle_point_captured(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("point_captured", None, None)
        return None

    def _handle_charge_deployed(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("charge_deployed", None, None)
        return None

    def _handle_teleported(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("teleported", None, None)
        return None

    def _handle_object_destroyed(self, match):
        destroyer, obj_type = match.groups()
        if destroyer == self.player_name:
            return ("object_destroyed", obj_type, None)
        return None

    def _handle_jarated(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("jarated", None, None)
        return None

    def _handle_deflect(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("deflect", None, None)
        return None

    def _handle_extinguished(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("extinguished", None, None)
        return None

    def _handle_player_teleported(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("player_teleported", None, None)
        return None

    def _handle_steal_sandwich(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("steal_sandwich", None, None)
        return None

    def _handle_stunned(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("stunned", None, None)
        return None

    def _handle_ubercharge(self, match):
        player = match.group(1)
        if player == self.player_name:
            return ("ubercharge", None, None)
        return None