from .base import BaseAI
from app import get_unique_orientations

# Difficulty 3: ピース数が多い順、最初に見つかった配置を採用


class Level3AI(BaseAI):
    def _move(self):
        pieces = list(enumerate(self.player["pieces"]))
        pieces.sort(key=lambda x: sum(sum(row)
                    for row in x[1]["shape"]), reverse=True)
        for idx, piece in pieces:
            for shape in get_unique_orientations(piece["shape"]):
                for x in range(self.game.board_size):
                    for y in range(self.game.board_size):
                        valid, _ = self.game.validate_move(
                            self.player_idx, idx, x, y)
                        if valid:
                            return self.place(idx, shape, x, y)
        return self.pass_turn(force=True)
