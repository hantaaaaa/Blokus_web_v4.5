// blokus.js
let selectedPieceIndex = -1;
let currentPlayerIndex = 0;
let prevPlayerIndex = null;    // 前回の currentPlayerIndex を記憶
let gameState = null;
let currentBoardSize = 20;
let gameEnded = false;

const PLAYER_COLORS = [
  { number: 1, color: "#FF0000", corner: [0, 0] },
  { number: 2, color: "#0000FF", corner: [19, 19] },
  { number: 3, color: "#00FF00", corner: [19, 0] },
  { number: 4, color: "#FFFF00", corner: [0, 19] }
];

const scoreModal = document.createElement('div');
scoreModal.id = 'score-modal';
scoreModal.style.display = 'none';
document.body.appendChild(scoreModal);

const TURN_TIME = 60;
let timer = null;
let timeLeft = 0;

// AI プレイヤーのインデックス
let aiPlayers = [];

document.addEventListener('DOMContentLoaded', () => {
  showLevelModal();
});

function showLevelModal() {
  document.getElementById('level-modal').style.display = 'flex';
  document.querySelector('.container').style.filter = 'blur(5px)';
}

async function startGame() {
  aiPlayers = [];
  const playerCount = parseInt(document.getElementById('player-count').value);
  const boardSize = parseInt(document.getElementById('board-size').value);

  const handicapLevels = [];
  const computerLevels = {};

  for (let i = 0; i < playerCount; i++) {
    handicapLevels.push(document.getElementById(`modal-player${i+1}-handicap`).value);
    if (document.getElementById(`modal-player${i+1}-control`).value === "computer") {
      aiPlayers.push(i);
      computerLevels[i] = document.getElementById(`modal-player${i+1}-difficulty`).value;
    }
  }

  document.getElementById('level-modal').style.display = 'none';
  document.querySelector('.container').style.filter = 'none';

  rebuildPlayerPanels(playerCount);

  try {
    let res = await fetch('/reset_game', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ size: boardSize, players: playerCount })
    });
    if (!res.ok) throw new Error();
  } catch {
    alert('ゲームの初期化に失敗しました');
    return;
  }

  try {
    await fetch('/set_handicap', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ levels: handicapLevels })
    });
  } catch {
    alert('レベル設定に失敗しました');
    return;
  }

  if (Object.keys(computerLevels).length > 0) {
    try {
      await fetch('/set_computer_levels', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ levels: computerLevels })
      });
    } catch {
      alert('AIレベルの設定に失敗しました');
      return;
    }
  }

  initializeGame();
  setupEventListeners();
  startTimer();
}

function rebuildPlayerPanels(count) {
  const container = document.querySelector('.game-area');
  const template = document.getElementById('player-panel-template');
  document.querySelectorAll('.player-panel').forEach(p => p.remove());
  for (let i = 0; i < count; i++) {
    const clone = template.content.cloneNode(true);
    const panel = clone.querySelector('.player-panel');
    const colorClass = ['red','blue','green','yellow'][i];
    panel.id = `player${i+1}-panel`;
    panel.className = `player-panel ${colorClass}`;
    panel.querySelector('h3').innerHTML = `Player${i+1}(${getColorName(PLAYER_COLORS[i].color)})`;
    panel.querySelector('.pieces-container').id = `player${i+1}-pieces`;
    container.appendChild(clone);
  }
  container.className = `game-area player-count-${count}`;
}

async function applyHandicap(levels) {
  try {
    await fetch('/set_handicap', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ levels })
    });
  } catch {
    alert('レベル設定に失敗しました');
  }
}

function initializeGame() {
  createBoard();
  fetchGameState();
}

function createBoard() {
  const board = document.getElementById('board');
  board.innerHTML = '';
  const size = currentBoardSize;
  const cellSize = 24;
  board.style.gridTemplateColumns = `repeat(${size}, ${cellSize}px)`;
  board.style.width = `${size * cellSize + 2}px`;
  for (let i = 0; i < size; i++) {
    for (let j = 0; j < size; j++) {
      const cell = document.createElement('div');
      cell.className = 'cell';
      cell.dataset.x = i;
      cell.dataset.y = j;
      cell.style.width = `${cellSize}px`;
      cell.style.height = `${cellSize}px`;
      cell.addEventListener('click', handleCellClick);
      board.appendChild(cell);
    }
  }
}

async function fetchGameState() {
  try {
    // プレイヤー変更判定のため、前回のインデックスを保持
    const oldPlayer = currentPlayerIndex;

    const res = await fetch('/get_state');
    gameState = await res.json();
    currentPlayerIndex = gameState.current_player;

    // プレイヤーが変わったらタイマーをリセット
    if (prevPlayerIndex !== null && oldPlayer !== currentPlayerIndex) {
      resetTimer();
    }
    prevPlayerIndex = currentPlayerIndex;

    if (gameState.board_size !== currentBoardSize) {
      currentBoardSize = gameState.board_size;
      createBoard();
    }
    updateBoard();
    renderPlayerPanels();
    updateStatus();
    checkGameEnd();
    updatePanelInteractivity();
    checkAIMove();
  } catch {
    console.error('状態取得失敗');
  }
}

function updateBoard() {
  const cells = document.querySelectorAll('.cell');
  const size = currentBoardSize;
  gameState.board.forEach((row, i) => {
    row.forEach((val, j) => {
      const idx = i * size + j;
      const cell = cells[idx];
      const player = gameState.players.find(p => p.number === val);
      let color = player ? player.color : '#ecf0f1';
      if (gameState.last_placed_piece?.player === val
        && gameState.last_placed_piece.coordinates.some(([x,y]) => x===i && y===j)) {
        color = darkenColor(color, 100);
      }
      cell.style.backgroundColor = color;
    });
  });
}

function renderPlayerPanels() {
  gameState.players.forEach((player, idx) => {
    const panel = document.getElementById(`player${idx+1}-panel`);
    const piecesC = document.getElementById(`player${idx+1}-pieces`);
    panel.style.borderColor = PLAYER_COLORS[idx].color;
    panel.querySelector('h3').innerHTML =
      `Player${idx+1}(${getColorName(player.color)})<br>${player.corner.join(',')}`;
    piecesC.innerHTML = player.pieces.map((piece, pi) => `
      <div class="piece ${idx===currentPlayerIndex?'active':'inactive'}"
           data-player="${idx}" data-piece-index="${pi}"
           onclick="handlePieceSelection(${idx},${pi})">
        ${generatePieceHTML(piece.shape, player.color)}
        <div class="piece-points">${piece.points}pt</div>
      </div>
    `).join('');
    panel.style.display = 'block';
  });
}

function generatePieceHTML(shape, color) {
  return shape.map(row => `
    <div class="piece-row">
      ${row.map(cell => `
        <div class="piece-cell ${cell?'filled':''}"
             style="${cell?`background:${color};border-color:${darkenColor(color)};`:''}"></div>
      `).join('')}
    </div>
  `).join('');
}

function darkenColor(hex, amt=20) {
  const num = parseInt(hex.slice(1),16);
  return `#${[
    Math.max((num>>16)-amt,0),
    Math.max((num>>8&0xFF)-amt,0),
    Math.max((num&0xFF)-amt,0)
  ].map(v=>v.toString(16).padStart(2,'0')).join('')}`;
}

function handlePieceSelection(pi, pidx) {
  if (aiPlayers.includes(currentPlayerIndex)) return;
  if (pi !== currentPlayerIndex) return showAlert('現在のプレイヤーではありません');
  selectedPieceIndex = pidx;
  document.querySelectorAll('.piece').forEach(p=>p.classList.remove('selected'));
  event.currentTarget.classList.add('selected');
}

async function rotatePiece() {
  if (aiPlayers.includes(currentPlayerIndex) || selectedPieceIndex<0) return;
  try {
    const res = await fetch('/rotate_piece',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({player:currentPlayerIndex,pieceIndex:selectedPieceIndex})
    });
    if (!res.ok) throw await res.json();
    await fetchGameState();
  } catch (e) {
    alert(e.message||'回転エラー');
  }
}

async function flipPiece() {
  if (aiPlayers.includes(currentPlayerIndex) || selectedPieceIndex<0) return;
  try {
    const res = await fetch('/flip_piece',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({player:currentPlayerIndex,pieceIndex:selectedPieceIndex})
    });
    if (!res.ok) throw await res.json();
    await fetchGameState();
  } catch (e) {
    alert(e.message||'反転エラー');
  }
}

async function handleCellClick(e) {
  if (aiPlayers.includes(currentPlayerIndex)||selectedPieceIndex<0) return;
  const x = +e.target.dataset.x, y = +e.target.dataset.y;
  try {
    const res = await fetch('/place_piece',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({player:currentPlayerIndex,pieceIndex:selectedPieceIndex,x,y})
    });
    const data = await res.json();
    if (data.status==='success') {
      selectedPieceIndex = -1;
      // プレイヤーが変われば resetTimer されるので、ここでは呼ばなくてOK
      await fetchGameState();
    } else {
      showAlert(data.message);
    }
  } catch {
    alert('配置エラー');
  }
}

function updateStatus() {
  const cur = gameState.players[currentPlayerIndex];
  const rem = cur.pieces.reduce((s,p)=>s+p.points,0);
  document.getElementById('status').innerHTML = `
    Player ${cur.number}(${getColorName(cur.color)})のターン<br>
    残りピース: ${cur.pieces.length}個<br>
    残りポイント: ${rem}<br>
    連続パス: ${gameState.consecutive_passes}回
  `;
}

function updatePanelInteractivity() {
  document.querySelectorAll('.player-panel').forEach((panel, idx) => {
    const active = idx===currentPlayerIndex;
    panel.style.opacity = active?1:0.5;
    panel.style.pointerEvents = active&&!aiPlayers.includes(currentPlayerIndex)?'auto':'none';
    panel.querySelectorAll('.piece').forEach(p=>p.classList.toggle('inactive',!active));
  });
}

async function passTurn(force=false) {
  if (aiPlayers.includes(currentPlayerIndex)&&!force) return;
  try {
    const res = await fetch('/pass_turn',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({player:currentPlayerIndex,force})
    });
    const data = await res.json();
    if (data.status==='success') {
      // プレイヤーが変われば resetTimer されるので、ここでは呼ばなくてOK
      await fetchGameState();
    } else {
      showAlert(data.message);
    }
  } catch {
    alert('パスエラー');
  }
}

function startTimer() {
  resetTimer();
  timer = setInterval(updateTimer,1000);
}

function resetTimer() {
  timeLeft = TURN_TIME;
  updateTimerDisplay();
  document.querySelector('.timer-display').classList.remove('blinking');
  syncTimeLeftWithServer(); // サーバーのtime_leftをリセット
}

async function syncTimeLeftWithServer() {
  try {
    await fetch('/reset_time_left', { method: 'POST', body: JSON.stringify({ time: TURN_TIME }), headers: { 'Content-Type': 'application/json' } });
  } catch (error) {
    console.error('Failed to reset server timeLeft:', error);
  }
}

function updateTimer() {
  timeLeft--;
  decrementServerTimeLeft(); // サーバーのtime_leftを減少
  updateTimerDisplay();
  if (timeLeft === 10) {
    document.getElementById('alertSound')?.play().catch(() => {});
  }
  if (timeLeft <= 0) {
    clearInterval(timer);
    passTurn(true);
    startTimer();
  }
}

function updateTimerDisplay() {
  const tm = document.getElementById('timer');
  const m = String(Math.floor(timeLeft/60)).padStart(2,'0');
  const s = String(timeLeft%60).padStart(2,'0');
  tm.textContent = `${m}:${s}`;
  tm.parentElement.classList.toggle('blinking', timeLeft<=10);
}

async function syncTimeLeft() {
  try {
    const response = await fetch('/get_time_left');
    const data = await response.json();
    timeLeft = data.time_left;
    updateTimerDisplay();
  } catch (error) {
    console.error('Failed to sync timeLeft:', error);
  }
}

async function decrementServerTimeLeft() {
  try {
    await fetch('/decrement_time_left', { method: 'POST' });
  } catch (error) {
    console.error('Failed to decrement server timeLeft:', error);
  }
}

function setupEventListeners() {
  document.getElementById('rotate').addEventListener('click', rotatePiece);
  document.getElementById('flip').addEventListener('click', flipPiece);
  document.getElementById('pass').addEventListener('click', passTurn);
  document.addEventListener('keydown', e => {
    if (e.key==='r') rotatePiece();
    if (e.key==='f') flipPiece();
    if (e.key==='p') passTurn();
  });
}

function checkGameEnd() {
  if (gameState.consecutive_passes>=gameState.players.length ||
      gameState.players.every(p=>p.pieces.length===0)) {
    const scores = calculateScores();
    showScoreModal(scores);
    gameEnded = true;
    clearInterval(timer);
  } else {
    scoreModal.style.display = 'none';
    gameEnded = false;
  }
}

function calculateScores() {
  const TOTAL = 89;
  return gameState.players.map(p => {
    const rem = p.pieces.reduce((s,x)=>s+x.points,0);
    const placed = TOTAL-rem;
    const bonus = p.pieces.length===0?15:0;
    return { player:p.number, color:p.color, score:placed+bonus, details:{placed,remaining:rem,bonus} };
  });
}

function showScoreModal(scores) {
  const max = Math.max(...scores.map(s=>s.score));
  const winners = scores.filter(s=>s.score===max);
  const isDraw = winners.length>1;
  scoreModal.style.cssText = `
    position:fixed; right:30px; top:50%; transform:translateY(-50%);
    width:300px; height:400px; background:rgba(255,255,255,0.8);
    border:2px solid #333; border-radius:10px; padding:20px;
    box-shadow:0 0 20px rgba(0,0,0,0.3); backdrop-filter:blur(5px);
    cursor:move; z-index:1000;
  `;
  scoreModal.innerHTML = `
    <div style="position:relative; height:100%;">
      <h3 style="margin-bottom:20px; border-bottom:2px solid #333; padding-bottom:10px;">
        ${isDraw?'🏆 引き分け！':`🏆 Player${winners[0].player}(${getColorName(winners[0].color)})の勝ち！`}
      </h3>
      <div style="overflow-y:auto; height:calc(100% - 40px);">
        ${formatScores(scores,max)}
      </div>
    </div>
  `;
  scoreModal.addEventListener('mousedown', initDrag);
}

function formatScores(scores, maxScore) {
  return scores.map(s => {
    const name = getColorName(s.color);
    const win = s.score===maxScore;
    return `
      <div style="margin-bottom:20px; ${win?'background:rgba(255,215,0,0.2); padding:5px; border-radius:5px;':''}">
        <strong>Player${s.player}(${name})</strong>${win?'👑':''}<br>
        <div style="margin-left:10px;">
          🏆 総合スコア: ${s.score}<br>
          ✅ 配置ポイント: ${s.details.placed}<br>
          ❌ 残りポイント: -${s.details.remaining}<br>
          ✨ ボーナス: +${s.details.bonus}
        </div>
      </div>
    `;
  }).join('');
}

function getColorName(color) {
  switch(color) {
    case '#FF0000': return '赤';
    case '#0000FF': return '青';
    case '#00FF00': return '緑';
    case '#FFFF00': return '黄';
    default: return '';
  }
}

function showAlert(msg) {
  const modal = document.getElementById('alert-modal');
  document.getElementById('alert-message').textContent = msg;
  modal.style.display = 'block';
}

function hideAlert() {
  document.getElementById('alert-modal').style.display = 'none';
}

function initDrag(e) {
  isDragging = true;
  dragStartX = e.clientX;
  dragStartY = e.clientY;
  initialX = scoreModal.offsetLeft;
  initialY = scoreModal.offsetTop;
  document.addEventListener('mousemove', handleDrag);
  document.addEventListener('mouseup', stopDrag);
}

function handleDrag(e) {
  if (!isDragging) return;
  const dx = e.clientX - dragStartX;
  const dy = e.clientY - dragStartY;
  scoreModal.style.left = `${initialX + dx}px`;
  scoreModal.style.top = `${initialY + dy}px`;
}

function stopDrag() {
  isDragging = false;
  document.removeEventListener('mousemove', handleDrag);
  document.removeEventListener('mouseup', stopDrag);
}

function checkAIMove() {
  if (gameEnded) return;
  if (aiPlayers.includes(currentPlayerIndex)) aiMove();
}

function aiMove() {
  setTimeout(() => {
    fetch('/computer_move', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ player: currentPlayerIndex })
    })
    .then(res => res.json())
    .then(data => {
      console.log(data.message);
      // プレイヤー変更でリセットするため、ここでは何もしない
      return fetchGameState();
    })
    .catch(err => console.error('AI move error:', err));
  }, 2000);
}
