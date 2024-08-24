import re

class TF2Events:
    def __init__(self, player_name):
        self.player_name = player_name
        self.killstreak = 0

    def process_log_line(self, line, debug_callback):
        # Kill, Death, and Suicide Events
        kill_event = re.search(r'(\w+) killed (\w+) with (\w+)\.', line)
        if kill_event:
            killer, victim, weapon = kill_event.groups()
            debug_callback(f"Kill event detected: {killer} killed {victim} with {weapon}")
            if killer == self.player_name:
                self.killstreak += 1
                debug_callback(f"Player {self.player_name} made a kill with {weapon}. Killstreak: {self.killstreak}")
                return ("kill", weapon, self.killstreak) 
            elif victim == self.player_name:
                self.killstreak = 0 
                debug_callback(f"Player {self.player_name} was killed by {weapon}. Killstreak reset.")
                return ("death", weapon, 0) 

        suicide_event = re.search(r'(\w+) suicided\.', line)
        if suicide_event:
            player = suicide_event.group(1)
            debug_callback(f"Suicide event detected: {player} suicided")
            if player == self.player_name:
                self.killstreak = 0 
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
                return ("dominated", player, None)

        revenge_event = re.search(r'(.+) got revenge on (.+)', line)
        if revenge_event:
            player, victim = revenge_event.groups()
            if player == self.player_name:
                return ("revenge", victim, None)

        # Round & Match Outcomes
        round_win_event = re.search(r'World triggered "Round_Win"', line)
        if round_win_event:
            return ("round_win", None, None)

        round_stalemate_event = re.search(r'World triggered "Round_Stalemate"', line)
        if round_stalemate_event:
            return ("round_stalemate", None, None)

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

        # Crit boosts (could also be considered Medic events)
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

        # Other Interesting Events (grouped together for now)
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
        spawn_event = re.search(r'(.+) has spawned as a "(Scout|Soldier|Pyro|Demoman|Heavy|Engineer|Medic|Sniper|Spy|Saxton Hale)"', line)
        if spawn_event:
            player, class_name = spawn_event.groups()
            if player == self.player_name:
                return ("spawned", class_name, None)

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

        return None  # Return None if no relevant event is found