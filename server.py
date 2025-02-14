from flask import Flask, jsonify, request
import logging
import random
from typing import Dict, Optional

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

startingDeck = [
    {"attack": 5, "health": 7}, {"attack": 6, "health": 5},
    {"attack": 8, "health": 6}, {"attack": 4, "health": 4},
    {"attack": 3, "health": 9}, {"attack": 7, "health": 7},
    {"attack": 2, "health": 10}, {"attack": 9, "health": 5},
    {"attack": 3, "health": 6}, {"attack": 6, "health": 8},
    {"attack": 5, "health": 3}, {"attack": 7, "health": 6}
]

class PlayerState:
    def __init__(self, player_id: str):
        self.player_id = player_id
        self.deck = self._create_deck()
        self.hand = [self.deck.pop() for _ in range(5)]
        self.board = []
        self.points = 0
        self.connected = True

    def _create_deck(self):
        deck = startingDeck[:]
        random.shuffle(deck)
        return deck

    def draw_card(self) -> Optional[Dict]:
        if len(self.hand) >= 6:
            return {"error": "Ręka pełna"}
        if self.deck:
            self.hand.append(self.deck.pop())
            return None
        return {"error": "Talia pusta"}

    def to_dict(self):
        return {
            "player_id": self.player_id,
            "deck": len(self.deck),
            "hand": self.hand,
            "board": self.board,
            "points": self.points,
            "connected": self.connected
        }

class GameState:
    def __init__(self):
        self.players: Dict[str, PlayerState] = {}
        self.current_turn: Optional[str] = None
        self.game_active: bool = False
        self.game_id: str = str(random.randint(1000, 9999))

    def add_player(self) -> Optional[str]:
        if len(self.players) == 0:
            player_id = "player_1"
            self.players[player_id] = PlayerState(player_id)
            self.current_turn = player_id
            return player_id
        elif len(self.players) == 1:
            player_id = "player_2"
            self.players[player_id] = PlayerState(player_id)
            self.game_active = True
            return player_id
        return None

    def end_turn(self, player_id: str) -> bool:
        if not self.game_active or self.current_turn != player_id:
            return False
        
        next_player_id = "player_2" if player_id == "player_1" else "player_1"
        player = self.players[next_player_id]
        

        if len(player.hand) < 6 and player.deck:
            player.draw_card()
        
        self.current_turn = next_player_id
        return True

    def can_play_card(self, player_id: str, card_index: int) -> bool:
        if not self.game_active or self.current_turn != player_id:
            return False
        player = self.players.get(player_id)
        if not player or card_index >= len(player.hand):
            return False
        return len(player.board) < 5

    def attack(self, attacker_id: str, attacker_idx: int, defender_id: str, defender_idx: int) -> Optional[str]:
        if not self.game_active or self.current_turn != attacker_id:
            return "Nie twoja tura"
            
        attacker = self.players.get(attacker_id)
        defender = self.players.get(defender_id)
        
        if not attacker or not defender:
            return "Nieprawidłowi gracze"
            
        if attacker_idx >= len(attacker.board) or defender_idx >= len(defender.board):
            return "Nieprawidłowe karty"
            
        attacking_card = attacker.board[attacker_idx]
        defending_card = defender.board[defender_idx]
        

        defending_card["health"] -= attacking_card["attack"]
        attacking_card["health"] -= defending_card["attack"]
        

        if defending_card["health"] <= 0:
            defender.board.pop(defender_idx)
            attacker.points += 1
            
        if attacking_card["health"] <= 0:
            attacker.board.pop(attacker_idx)
            defender.points += 1
            
        return None

    def to_dict(self):
        return {
            "game_id": self.game_id,
            "game_active": self.game_active,
            "players": {p: self.players[p].to_dict() for p in self.players},
            "current_turn": self.current_turn
        }


# Global game state
game_state = GameState()

@app.route('/create_game', methods=['POST'])
def create_game():
    global game_state
    if game_state.game_active:
        game_state = GameState()
    
    player_id = game_state.add_player()
    if player_id:
        return jsonify({"player_id": player_id, "game_state": game_state.to_dict()}), 200
    return jsonify({"error": "Nie można utworzyć gry"}), 400

@app.route('/join_game', methods=['POST'])
def join_game():
    if game_state.game_active:
        return jsonify({"error": "Gra już trwa"}), 400
        
    player_id = game_state.add_player()
    if player_id:
        return jsonify({"player_id": player_id, "game_state": game_state.to_dict()}), 200
    return jsonify({"error": "Nie można dołączyć do gry"}), 400

@app.route('/play_card', methods=['POST'])
def play_card():
    data = request.get_json()
    player_id = data.get("player_id")
    card_index = data.get("card_index")
    
    if not game_state.can_play_card(player_id, card_index):
        return jsonify({"error": "Nie można zagrać karty"}), 400
        
    player = game_state.players[player_id]
    card = player.hand.pop(card_index)
    player.board.append(card)
    
    return jsonify(game_state.to_dict()), 200

@app.route('/attack', methods=['POST'])
def attack():
    data = request.get_json()
    attacker_id = data.get("attacker_id")
    attacker_idx = data.get("attacker_idx")
    defender_id = data.get("defender_id")
    defender_idx = data.get("defender_idx")

    error = game_state.attack(attacker_id, attacker_idx, defender_id, defender_idx)
    if error:
        return jsonify({"error": error}), 400

    return jsonify(game_state.to_dict()), 200

@app.route('/game_state', methods=['GET'])
def get_game_state():
    return jsonify(game_state.to_dict())

@app.route('/end_turn', methods=['POST'])
def end_turn():
    data = request.get_json()
    player_id = data.get("player_id")
    
    if game_state.end_turn(player_id):
        return jsonify(game_state.to_dict()), 200
    return jsonify({"error": "Nie można zakończyć tury"}), 400

@app.route('/check_winner', methods=['POST'])
def check_winner():
    data = request.json
    game_id = data.get("game_id")

    if not game_id:
        return jsonify({"error": "Brak game_id"}), 400

    if not game_state.game_active:
        return jsonify({"error": "Gra nie istnieje"}), 404

    for player_id, player_data in game_state.players.items():
        if len(player_data["board"]) == 0 and len(player_data["hand"]) == 0 and len(player_data["deck"]) == 0:
            winner_id = next(pid for pid in game_state.players if pid != player_id)
            game_state.game_active = False
            return jsonify({
                "winner": winner_id,
                "loser": player_id
            })

    return jsonify({"winner": None})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
