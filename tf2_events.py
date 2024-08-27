import re

class TF2Events:
    def __init__(self, player_name):
        self.player_name = player_name
        self.killstreak = 0

    def process_log_line(self, line, debug_callback):
            # Kill, Death, and Suicide Events (case-insensitive regex)
            kill_patterns = [
                r'(\w+) killed (\w+) with (\w+)(\. \(crit\))?',
                r'(\w+) backstabbed (\w+)',
                r'(\w+) headshot (\w+)',
                r'(\w+) dominated (\w+)',
                r'(\w+) got revenge on (\w+)',
                r'(\w+) killed (\w+) with the assistance of (\w+)',
                r'(\w+) pushed (\w+) into ([\w ]+)',
                r'(\w+) exploded (\w+)',
                r'([\w ]+) killed (\w+)',
                r'(\w+) taunt-killed (\w+)',
                r'(\w+) airblasted (\w+) to their death',
                r'(\w+) knocked (\w+) into the air and they exploded upon landing',
                r'(\w+) killed (\w+) while ÜberCharged',
                r'(\w+) telefragged (\w+)',
                r'(\w+) sacrificed (\w+)'
            ]
    
            for pattern in kill_patterns:
                kill_event = re.search(pattern, line, re.IGNORECASE)
                if kill_event:
                    groups = kill_event.groups()
    
                    # Extract killer, victim, and optional crit info
                    if len(groups) == 4:
                        killer, victim, weapon, is_crit = groups
                        is_crit = is_crit is not None
                    elif len(groups) == 2:
                        killer, victim = groups
                        weapon = None  # Some kill types don't mention the weapon
                        is_crit = False
                    elif len(groups) == 3:  # Handle "assisted killing" format
                        killer, victim, assistant = groups
                        weapon = None
                        is_crit = False
                    else:
                        continue  # Skip if the pattern doesn't match the expected formats
    
                    debug_callback(f"Kill event detected: {killer} killed {victim} {'(crit)' if is_crit else ''}")
                    print(f"Kill event detected: {killer} killed {victim} {'(crit)' if is_crit else ''}")
    
                    if killer == self.player_name:
                        self.killstreak += 1
                        debug_callback(f"Player {self.player_name} made a kill. Killstreak: {self.killstreak}")
                        print(f"Player {self.player_name} made a kill. Killstreak: {self.killstreak}")
                        return ("kill", weapon, self.killstreak) 
                    elif victim == self.player_name:
                        self.killstreak = 0
                        debug_callback(f"Player {self.player_name} was killed. Killstreak reset.")
                        return ("death", weapon, 0)
    
            suicide_event = re.search(r'(\w+) suicided\.', line)
            if suicide_event:
                player = suicide_event.group(1)
                debug_callback(f"Suicide event detected: {player} suicided")
                if player == self.player_name:
                    self.killstreak = 0
                    debug_callback(f"Player {self.player_name} suicided. Killstreak reset.")
                    return ("suicide", None, 0)
    
            # Capture & Defend Events 
            capture_event = re.search(r'(.+) captured control point (.+)', line)
            if capture_event:
                player, point = capture_event.groups()
                if player == self.player_name:
                    return ("capture", point, None) 
    
            # Payload Events
            payload_event = re.search(r'(.+) (picked up|dropped) the intelligence', line)
            if payload_event:
                player, action = payload_event.groups()
                if player == self.player_name:
                    return (action + "_intel", None, None)
    
            payload_event = re.search(r'(.+) has the intelligence!', line)
            if payload_event:
                player = payload_event.group(1)
                if player == self.player_name:
                    return ("has_intel", None, None)
    
            # Building & Destroying Objects
            build_destroy_event = re.search(r'(.+) (built|destroyed) object (.+)', line)
            if build_destroy_event:
                player, action, object_type = build_destroy_event.groups()
                if player == self.player_name:
                    return (action + "_" + object_type, None, None)
    
            # Dominations & Revenge
            domination_event = re.search(r'(.+) dominated (.+)', line)
            if domination_event:
                player, victim = domination_event.groups()
                if player == self.player_name:
                    return ("domination", victim, None)
                elif victim == self.player_name:
                    self.killstreak = 0  # Domination breaks killstreak
                    return ("dominated", player, 0) 
    
            revenge_event = re.search(r'(.+) got revenge on (.+)', line)
            if revenge_event:
                player, victim = revenge_event.groups()
                if player == self.player_name:
                    return ("revenge", victim, None)
    
            # Round & Match Outcomes
            round_win_event = re.search(r'World triggered "Round_Win"', line)
            if round_win_event:
                self.killstreak = 0 
                return ("round_win", None, 0)
    
            round_stalemate_event = re.search(r'World triggered "Round_Stalemate"', line)
            if round_stalemate_event:
                self.killstreak = 0
                return ("round_stalemate", None, 0)
    
            # First Blood
            first_blood_event = re.search(r'(.+) drew first blood!', line)
            if first_blood_event:
                player = first_blood_event.group(1)
                if player == self.player_name:
                    return ("first_blood", None, None)
    
            # Class-Specific Events 
    
            # Medic Events
            medic_event = re.search(r'(.+) triggered "ubercharge_deployed"', line)
            if medic_event:
                player = medic_event.group(1)
                if player == self.player_name:
                    return ("medic_uber", None, None)
    
            medic_event = re.search(r'(.+) triggered "charge_deployed"', line)
            if medic_event:
                player = medic_event.group(1)
                if player == self.player_name:
                    return ("medic_charge_deployed", None, None)
    
            # Crit boosts 
            crit_boost_event = re.search(r'(.+) triggered "crit_boosted" against (.+)', line)
            if crit_boost_event:
                medic, player = crit_boost_event.groups()
                if medic == self.player_name:
                    return ("crit_boosted", player, None)
    
            mini_crit_boost_event = re.search(r'(.+) triggered "mini_crit_boosted" against (.+)', line)
            if mini_crit_boost_event:
                medic, player = mini_crit_boost_event.groups()
                if medic == self.player_name:
                    return ("mini_crit_boosted", player, None)
    
            # Heal Events 
            heal_event = re.search(r'(.+) triggered "healed" against (.+) \(healing "(\d+)"\)', line)
            if heal_event:
                medic, patient, healing = heal_event.groups()
                if medic == self.player_name:
                    return ("healed", patient, healing)
    
            # Spy Events
            spy_event = re.search(r'(.+) triggered "disguise_complete"', line)
            if spy_event:
                player = spy_event.group(1)
                if player == self.player_name:
                    return ("spy_disguise_complete", None, None)
    
            spy_event = re.search(r'(.+) triggered "backstab" against (.+)', line)
            if spy_event:
                spy, victim = spy_event.groups()
                if spy == self.player_name:
                    return ("spy_backstab", victim, None)
    
            # Engineer Events
            engineer_event = re.search(r'(.+) triggered "teleported"', line) 
            if engineer_event:
                player = engineer_event.group(1)
                if player == self.player_name:
                    return ("engineer_teleported", None, None)
    
            # Sniper Events
            sniper_event = re.search(r'(.+) triggered "headshot" against (.+)', line)
            if sniper_event:
                sniper, victim = sniper_event.groups()
                if sniper == self.player_name:
                    return ("sniper_headshot", victim, None)
    
            # Pyro Events
            pyro_event = re.search(r'(.+) triggered "airblast" against (.+)', line)
            if pyro_event:
                pyro, victim = pyro_event.groups()
                if pyro == self.player_name:
                    return ("pyro_airblast", victim, None)
    
            # Demoman Events
            demoman_event = re.search(r'(.+) sticky trap triggered', line)
            if demoman_event:
                player = demoman_event.group(1)
                if player == self.player_name:
                    return ("demoman_sticky_trap_triggered", None, None)
    
            # Heavy Events
            heavy_event = re.search(r'(.+) triggered "player_is_eating"', line)
            if heavy_event:
                player = heavy_event.group(1)
                if player == self.player_name:
                    return ("heavy_eating", None, None)
    
            # Other Interesting Events 
            other_events = [
                (r'(.+) triggered "player_stunned"', "stunned"),
                (r'(.+) triggered "player_jarated"', "jarated"),
                (r'(.+) triggered "player_milked"', "milked"),
                (r'(.+) triggered "player_extinguished"', "extinguished"),
            ]
    
            for pattern, event_type in other_events:
                match = re.search(pattern, line)
                if match:
                    player = match.group(1)
                    if player == self.player_name:
                        return (event_type, None, None)
    
            # Class Change Event & Spawn
            class_change_event = re.search(r'(.+) changed role to "(Scout|Soldier|Pyro|Demoman|Heavy|Engineer|Medic|Sniper|Spy)"', line)
            if class_change_event:
                player, new_class = class_change_event.groups()
                if player == self.player_name:
                    self.killstreak = 0
                    debug_callback(f"Player {self.player_name} changed class to {new_class}. Killstreak reset.")
                    return ("class_change", new_class, 0)
    
            spawn_event = re.search(r'(.+) has spawned as a "(Scout|Soldier|Pyro|Demoman|Heavy|Engineer|Medic|Sniper|Spy|Saxton Hale)"', line)
            if spawn_event:
                player, class_name = spawn_event.groups()
                if player == self.player_name:
                    self.killstreak = 0 
                    debug_callback(f"Player {self.player_name} spawned as {class_name}. Killstreak reset.")
                    return ("spawned", class_name, 0)
    
            # Team Change 
            team_change_event = re.search(r'(.+) joined team "(RED|BLU)"', line)
            if team_change_event:
                player, team = team_change_event.groups()
                if player == self.player_name:
                    self.killstreak = 0
                    debug_callback(f"Player {self.player_name} changed to team {team}. Killstreak reset.")
                    return ("team_change", team, 0)
    
            # Map Change 
            map_change_event = re.search(r'Loading map "(.+)"', line)
            if map_change_event:
                map_name = map_change_event.group(1)
                self.killstreak = 0
                debug_callback(f"Map changed to {map_name}. Killstreak reset.")
                return ("map_change", map_name, 0)
    
            # Damage & Assists
            damage_event = re.search(r'(.+) triggered "damage" against (.+) \(damage "(\d+)"\)', line)
            if damage_event:
                attacker, victim, damage = damage_event.groups()
                if attacker == self.player_name:
                    return ("damage", victim, damage)
    
            assist_event = re.search(r'assisted killing (.+)', line)
            if assist_event:
                victim = assist_event.group(1)
                return ("assist", victim, None)
    
            return None            
            
        


