from .base import BaseAI
from app import get_unique_orientations
import random

# Difficulty 2: 完全ランダム配置


class Level2AI(BaseAI):
    def _move(self):
        positions = [(x, y) for x in range(self.game.board_size)
                     for y in range(self.game.board_size)]
        random.shuffle(positions)
        pieces = list(enumerate(self.player["pieces"]))
        random.shuffle(pieces)
        for idx, piece in pieces:
            shapes = get_unique_orientations(piece["shape"])
            random.shuffle(shapes)
            for shape in shapes:
                for x, y in positions:
                    valid, _ = self.game.validate_move(
                        self.player_idx, idx, x, y)
                    if valid:
                        return self.place(idx, shape, x, y)
        return self.pass_turn(force=True)
