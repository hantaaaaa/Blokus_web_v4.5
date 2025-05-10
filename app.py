from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import numpy as np
from itertools import product
import copy
import importlib

app = Flask(__name__)
CORS(app)


def get_unique_orientations(shape):
    """
    与えられた2次元リスト（ピースの形状）のすべてのユニークな回転・反転形状を返す。
    """
    orientations = []
    seen = set()
    arr = np.array(shape)
    for flip in [False, True]:
        arr_to_test = np.fliplr(arr) if flip else arr
        for k in range(4):
            rotated = np.rot90(arr_to_test, k=k)
            t = tuple(tuple(row) for row in rotated.tolist())
            if t not in seen:
                seen.add(t)
                orientations.append(rotated.tolist())
    return orientations


class BlokusGame:
    def __init__(self, board_size=20, num_players=2):
        self.board_size = board_size
        self.num_players = num_players
        self.board = np.zeros((board_size, board_size), dtype=int)
        self.players = self.initialize_players()
        self.current_player = 0
        self.consecutive_passes = 0
        self.handicap_levels = [0] * num_players
        self.original_pieces = self.create_initial_pieces()
        self.last_placed_piece = None
        self.time_left = 60  # 各ターンの初期残り時間（秒）

    def update_time_left(self, time):
        """
        残り時間を更新する。
        """
        self.time_left = time

    def decrement_time_left(self):
        """
        残り時間を1秒減少させる。
        """
        if self.time_left > 0:
            self.time_left -= 1

    def initialize_players(self):
        settings = [
            {"number": 1, "color": "#FF0000", "corner": (0, 0)},
            {"number": 2, "color": "#0000FF", "corner": (self.board_size - 1, self.board_size - 1)},
            {"number": 3, "color": "#00FF00", "corner": (self.board_size - 1, 0)},
            {"number": 4, "color": "#FFFF00", "corner": (0, self.board_size - 1)}
        ]
        return [self.create_player(s) for s in settings[:self.num_players]]

    def create_player(self, setting):
        return {
            "number": setting["number"],
            "color": setting["color"],
            "corner": setting["corner"],
            "pieces": self.create_initial_pieces()
        }

    def create_initial_pieces(self):
        return [
            {"shape": [[1]], "points": 1},
            {"shape": [[1, 1]], "points": 2},
            {"shape": [[1, 1, 1]], "points": 3},
            {"shape": [[1, 1], [1, 0]], "points": 3},
            {"shape": [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "points": 3},
            {"shape": [[1, 1, 1, 1]], "points": 4},
            {"shape": [[1, 1, 1], [1, 0, 0]], "points": 4},
            {"shape": [[1, 1], [1, 1]], "points": 4},
            {"shape": [[1, 1, 1], [0, 1, 0]], "points": 4},
            {"shape": [[1, 1, 0], [0, 1, 1]], "points": 4},
            {"shape": [[1, 1, 1, 1, 1]], "points": 5},
            {"shape": [[1, 1, 1, 1], [1, 0, 0, 0]], "points": 5},
            {"shape": [[1, 1, 1], [1, 0, 1]], "points": 5},
            {"shape": [[1, 1, 1], [1, 1, 0]], "points": 5},
            {"shape": [[1, 1, 0], [0, 1, 1], [0, 0, 1]], "points": 5},
            {"shape": [[1, 0, 1], [0, 1, 0], [1, 0, 1]], "points": 5},
            {"shape": [[1, 1, 1], [0, 1, 0], [0, 1, 0]], "points": 5},
            {"shape": [[1, 1, 1, 1], [0, 1, 0, 0]], "points": 5},
            {"shape": [[0, 1, 1, 1], [1, 1, 0, 0]], "points": 5},
            {"shape": [[1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 1, 0], [1, 0, 0]], "points": 5},
            {"shape": [[1, 1, 0], [0, 1, 0], [0, 1, 1]], "points": 5}
        ]

    def get_state(self):
        return {
            "board": self.board.tolist(),
            "board_size": self.board_size,
            "players": self.players,
            "current_player": self.current_player,
            "consecutive_passes": self.consecutive_passes,
            "handicap_levels": self.handicap_levels,
            "last_placed_piece": self.last_placed_piece
        }

    def set_handicap(self, levels):
        self.handicap_levels = levels
        for i, lvl in enumerate(levels):
            max_p = {0: 10, 1: 15, 2: 21}.get(int(lvl), 21)
            self.players[i]["pieces"] = copy.deepcopy(
                self.original_pieces[:max_p])

    def validate_move(self, player_idx, piece_idx, x, y):
        player = self.players[player_idx]
        piece = player["pieces"][piece_idx]
        shape = np.array(piece["shape"])
        num = player["number"]
        # 範囲外 or 重複
        if x < 0 or y < 0 or x + \
                shape.shape[0] > self.board_size or y + shape.shape[1] > self.board_size:
            return False, "ボードの外には置けません"
        if np.any(self.board[x:x + shape.shape[0],
                  y:y + shape.shape[1]] * shape):
            return False, "既にピースが存在します"
        # 初手 or 以降
        if not np.any(self.board == num):
            tgt = player["corner"]
            for i, j in product(range(shape.shape[0]), range(shape.shape[1])):
                if shape[i][j] and (x + i, y + j) == tgt:
                    if self.check_other_corners_contact(x + i, y + j, num):
                        return False, "他プレイヤーのコーナーに接しています"
                    return True, ""
            return False, "自分のコーナーに接していません"
        else:
            corner_ct = False
            edge_ct = False
            for i, j in product(range(shape.shape[0]), range(shape.shape[1])):
                if not shape[i][j]:
                    continue
                cx, cy = x + i, y + j
                for dx, dy in product([-1, 0, 1], repeat=2):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < self.board_size and 0 <= ny < self.board_size:
                        if self.board[nx][ny] == num:
                            if abs(dx) == 1 and abs(dy) == 1:
                                corner_ct = True
                            else:
                                edge_ct = True
            if not corner_ct:
                return False, "コーナーで接していません"
            if edge_ct:
                return False, "辺で接しています"
        return True, ""

    def check_other_corners_contact(self, x, y, cur_num):
        for p in self.players:
            if p["number"] != cur_num and (x, y) == p["corner"]:
                return True
        return False

    def rotate_piece(self, player_idx, piece_idx):
        p = self.players[player_idx]
        arr = np.array(p["pieces"][piece_idx]["shape"])
        p["pieces"][piece_idx]["shape"] = np.rot90(arr, k=-1).tolist()

    def flip_piece(self, player_idx, piece_idx):
        p = self.players[player_idx]
        arr = np.array(p["pieces"][piece_idx]["shape"])
        p["pieces"][piece_idx]["shape"] = np.fliplr(arr).tolist()

    def place_piece(self, player_idx, piece_idx, x, y):
        valid, msg = self.validate_move(player_idx, piece_idx, x, y)
        if not valid:
            return False, msg
        p = self.players[player_idx]
        shape = np.array(p["pieces"][piece_idx]["shape"])
        num = p["number"]
        self.board[x:x + shape.shape[0], y:y + shape.shape[1]] += shape * num
        del p["pieces"][piece_idx]
        self.current_player = (self.current_player + 1) % self.num_players
        self.consecutive_passes = 0
        self.last_placed_piece = {
            "player": num,
            "coordinates": [
                (x + i, y + j)
                for i, j in product(range(shape.shape[0]), range(shape.shape[1]))
                if shape[i][j]
            ]
        }
        return True, ""

    def pass_turn(self, player_idx, force=False):
        if player_idx != self.current_player:
            return False, "現在のプレイヤーではありません"
        if not force and self.has_valid_moves(player_idx):
            return False, "まだ配置可能なピースがあります"
        self.current_player = (self.current_player + 1) % self.num_players
        self.consecutive_passes += 1
        return True, ""

    def has_valid_moves(self, player_idx):
        for idx in range(len(self.players[player_idx]["pieces"])):
            for x in range(self.board_size):
                for y in range(self.board_size):
                    if self.validate_move(player_idx, idx, x, y)[0]:
                        return True
        return False


game = BlokusGame()


@app.route('/reset_game', methods=['POST'])
def reset_game():
    global game
    data = request.json
    sz = int(data.get('size', 20))
    pl = int(data.get('players', 2))
    if sz not in [14, 17, 20]:
        return jsonify({"status": "error", "message": "無効なボードサイズ"}), 400
    if not 2 <= pl <= 4:
        return jsonify({"status": "error", "message": "無効なプレイヤー数"}), 400
    game = BlokusGame(board_size=sz, num_players=pl)
    return jsonify({"status": "success"})


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/get_state')
def get_state():
    return jsonify(game.get_state())


@app.route('/set_handicap', methods=['POST'])
def set_handicap():
    levels = request.json.get('levels', [])
    game.set_handicap(levels)
    return jsonify({"status": "success"})


@app.route('/set_computer_levels', methods=['POST'])
def set_computer_levels():
    data = request.json.get('levels', {})
    for k, v in data.items():
        idx = int(k)
        if idx < len(game.players):
            game.players[idx]['difficulty'] = int(v)
    return jsonify({"status": "success"})


@app.route('/place_piece', methods=['POST'])
def place_piece():
    d = request.json
    ok, msg = game.place_piece(d['player'], d['pieceIndex'], d['x'], d['y'])
    return jsonify({"status": "success" if ok else "invalid", "message": msg})


@app.route('/rotate_piece', methods=['POST'])
def rotate_piece():
    d = request.json
    game.rotate_piece(d['player'], d['pieceIndex'])
    return jsonify({"status": "success"})


@app.route('/flip_piece', methods=['POST'])
def flip_piece():
    d = request.json
    game.flip_piece(d['player'], d['pieceIndex'])
    return jsonify({"status": "success"})


@app.route('/pass_turn', methods=['POST'])
def pass_turn():
    d = request.json
    ok, msg = game.pass_turn(d['player'], force=d.get('force', False))
    return jsonify({"status": "success" if ok else "invalid", "message": msg})


@app.route('/computer_move', methods=['POST'])
def computer_move_endpoint():
    d = request.json
    idx = int(d.get('player', 0))
    diff = game.players[idx].get('difficulty', 1)
    module = importlib.import_module(f"ai_models.level{diff}")
    cls = getattr(module, f"Level{diff}AI")
    ai = cls(game, idx)
    ok, msg = ai.move()
    return jsonify({"status": "success" if ok else "invalid", "message": msg})


@app.route('/get_time_left')
def get_time_left():
    return jsonify({"time_left": game.time_left})


@app.route('/decrement_time_left', methods=['POST'])
def decrement_time_left():
    game.decrement_time_left()
    return jsonify({"status": "success"})


@app.route('/reset_time_left', methods=['POST'])
def reset_time_left():
    data = request.json
    game.update_time_left(data.get('time', 60))
    return jsonify({"status": "success"})


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
