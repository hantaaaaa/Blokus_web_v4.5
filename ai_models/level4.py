# blokus-web/ai_models/level4.py
from .base import BaseAI
from app import get_unique_orientations
import numpy as np
import time


class Level4AI(BaseAI):
    """
    Difficulty 4: ヒューリスティック評価で最良手を選択
    ─ タイムガードを入れて、探索時間が0.5秒を超えたら即座に配置します。
    """
    MAX_SEARCH_TIME = 0.5  # 秒

    def __init__(self, game, player_idx):
        super().__init__(game, player_idx)
        self.best_score = -1  # インスタンス変数としてbest_scoreを初期化

    def _move(self):
        start_time = time.perf_counter()
        best_move = None

        # デバッグ: 手番開始時のbest_scoreをログ出力
        print(f"手番開始時のbest_score: {self.best_score}")

        # ピースをサイズ順にソート（大きい順）
        sorted_pieces = sorted(
            enumerate(
                self.player["pieces"]), key=lambda x: np.sum(
                x[1]["shape"]), reverse=True)

        board_size = self.game.board_size
        board = self.game.board  # numpy array

        for idx, piece in sorted_pieces:
            # 1 回だけオリエンテーションを生成
            orientations = get_unique_orientations(piece["shape"])

            for shape in orientations:
                shape_arr = np.array(shape)
                rows, cols = shape_arr.shape
                max_x = board_size - rows
                max_y = board_size - cols

                # スライドウィンドウ風に範囲を限定
                for x in range(max_x + 1):
                    sub_board = board[x:x + rows]
                    for y in range(max_y + 1):
                        elapsed_time = time.perf_counter() - start_time

                        # タイムアップが近い場合、現在の最良手を即座に実行
                        if elapsed_time > self.MAX_SEARCH_TIME * 0.9:
                            # デバッグ: best_moveが実行される際のログ
                            if best_move:
                                print(f"best_moveを実行: {best_move}")
                                return self._execute(best_move)
                            else:
                                print("パスを実行")
                                return self.pass_turn(force=True)

                        # 修正: タイムガードを緩和し、探索中に最良手を保持
                        if elapsed_time > self.MAX_SEARCH_TIME:
                            # デバッグ: best_moveが実行される際のログ
                            if best_move:
                                print(f"best_moveを実行: {best_move}")
                                return self._execute(best_move)
                            else:
                                print("パスを実行")
                                return self.pass_turn(force=True)

                        # デバッグ: time_leftの値をログ出力
                        # print(f"現在の残り時間: {self.game.time_left}秒")

                        # まず重複チェックだけ
                        if np.any(sub_board[:, y:y + cols] * shape_arr):
                            continue

                        # 初手の場合、コーナーに接しているかを確認
                        if not np.any(board == self.player_idx + 1):
                            corner_x, corner_y = self.player["corner"]
                            if not any(
                                (x + i, y + j) == (corner_x, corner_y)
                                for i, j in np.argwhere(shape_arr == 1)
                            ):
                                continue

                        # 2手目以降の場合、コーナー接触を確認
                        if np.any(board == self.player_idx + 1):
                            if not any(
                                board[x + i + dx, y + j + dy] == self.player_idx + 1
                                for i, j in np.argwhere(shape_arr == 1)
                                for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]
                                if 0 <= x + i + dx < board_size and 0 <= y + j + dy < board_size
                            ):
                                continue

                        # 盤面ルールの詳細チェック
                        valid, _ = self.game.validate_move(
                            self.player_idx, idx, x, y)
                        if not valid:
                            continue

                        # ４コーナーヒューリスティック
                        score = 0
                        coords = np.argwhere(shape_arr == 1)
                        for (i, j) in coords:
                            xi, yj = x + i, y + j
                            for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                                nx, ny = xi + dx, yj + dy
                                if 0 <= nx < board_size and 0 <= ny < board_size:
                                    if board[nx, ny] == 0:
                                        score += 1

                        # 修正: 残り時間が5秒以下の場合、探索途中でも最良手を即座に実行
                        if self.game.time_left <= 5:
                            print("残り時間5秒")
                            # デバッグ: best_moveが実行される際のログ
                            if best_move:
                                print(f"best_moveを実行: {best_move}")
                                return self._execute(best_move)
                            else:
                                print("パスを実行")
                                return self.pass_turn(force=True)

                        if score > self.best_score:
                            # デバッグログを追加
                            print(
                                f"best_score更新: {self.best_score} -> {score}")
                            self.best_score = score
                            best_move = (idx, shape, x, y)

        # 探索完了後、ベストムーブを実行
        if best_move:
            print(f"手番終了時のbest_score: {self.best_score}")
            self.best_score = -1
            return self._execute(best_move)
        else:
            return self.pass_turn(force=True)

    def _execute(self, move):
        idx, shape, x, y = move
        # デバッグ: placeメソッドの呼び出しをログ出力
        print(f"placeを呼び出し: piece_index={idx}, shape={shape}, x={x}, y={y}")
        result = self.place(idx, shape, x, y)
        # デバッグ: placeメソッドの結果をログ出力
        print(f"placeの結果: {result}")
        return result
