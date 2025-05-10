from .base import BaseAI
from app import get_unique_orientations

# Difficulty 1: ピースのサイズが小さい順に配置（弱手）


class Level1AI(BaseAI):
    def _move(self):
        pieces = list(enumerate(self.player["pieces"]))
        pieces.sort(key=lambda x: sum(sum(row) for row in x[1]["shape"]))
        for idx, piece in pieces:
            for shape in get_unique_orientations(piece["shape"]):
                for x in range(self.game.board_size):
                    for y in range(self.game.board_size):
                        valid, _ = self.game.validate_move(
                            self.player_idx, idx, x, y)
                        if valid:
                            return self.place(idx, shape, x, y)
        return self.pass_turn(force=True)
