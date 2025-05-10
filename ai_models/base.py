from abc import ABC, abstractmethod
import numpy as np
from app import get_unique_orientations


class BaseAI(ABC):
    def __init__(self, game, player_idx):
        self.game = game
        self.player_idx = player_idx
        self.player = game.players[player_idx]
        self.difficulty = self.player.get("difficulty", 1)

    def move(self):
        if self.player_idx != self.game.current_player:
            return False, "Not your turn"
        return self._move()

    @abstractmethod
    def _move(self):
        pass

    def pass_turn(self, force=False):
        return self.game.pass_turn(self.player_idx, force=force)

    def place(self, piece_index, shape, x, y):
        self.player["pieces"][piece_index]["shape"] = shape
        return self.game.place_piece(self.player_idx, piece_index, x, y)
