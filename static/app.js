const WALL = 1;
const $ = id => document.getElementById(id);
const board = $('board');
const directions = { ArrowUp: 'up', w: 'up', W: 'up', ArrowDown: 'down', s: 'down', S: 'down', ArrowLeft: 'left', a: 'left', A: 'left', ArrowRight: 'right', d: 'right', D: 'right' };
let gameState = null;
let busy = false;
let queuedMoves = [];
let cells = [];
let actors = [];
let renderedLevel = null;

async function request(path, body) {
  const response = await fetch(`/api/${path}`, {
    method: body ? 'POST' : 'GET',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  });
  if (!response.ok) throw new Error(`Game request failed: ${path}`);
  return response.json();
}

function keyFor(row, col) { return `${row},${col}`; }

function createBoard() {
  const fragment = document.createDocumentFragment();
  board.style.setProperty('--cols', gameState.cols);
  board.style.setProperty('--rows', gameState.rows);
  cells = [];
  for (let row = 0; row < gameState.rows; row++) {
    cells[row] = [];
    for (let col = 0; col < gameState.cols; col++) {
      const cell = document.createElement('div');
      cell.className = `cell ${gameState.grid[row][col] === WALL ? 'wall' : 'floor'}`;
      cell.setAttribute('role', 'gridcell');
      cells[row][col] = cell;
      fragment.append(cell);
    }
  }
  const actorLayer = document.createElement('div');
  actorLayer.className = 'actor-layer';
  actors = [document.createElement('div')];
  actors[0].className = 'actor player-sprite';
  actors[0].setAttribute('aria-label', 'You');
  actorLayer.append(actors[0]);
  for (let index = 0; index < 3; index++) {
    const actor = document.createElement('div');
    actor.className = `actor seeker-sprite seeker-${index}`;
    actor.setAttribute('aria-label', `BFS seeker ${index + 1}`);
    actors.push(actor);
    actorLayer.append(actor);
  }
  fragment.append(actorLayer);
  board.replaceChildren(fragment);
  renderedLevel = gameState.level;
}

function placeActor(actor, cell, rotation = 0) {
  const [row, col] = cell;
  actor.style.left = `${(col + 0.5) / gameState.cols * 100}%`;
  actor.style.top = `${(row + 0.5) / gameState.rows * 100}%`;
  actor.style.setProperty('--facing', `${rotation}deg`);
}

function render() {
  if (!gameState) return;
  if (!cells.length || renderedLevel !== gameState.level) createBoard();

  for (const row of cells) for (const cell of row) cell.classList.remove('pursuit', 'active-dot', 'pulse-dot-cell');
  const pathSet = new Set(gameState.paths.flatMap(path => path.map(cell => keyFor(...cell))));
  const pelletSet = new Set(gameState.pellets.map(cell => keyFor(...cell)));
  const pulseSet = new Set(gameState.pulses.map(cell => keyFor(...cell)));
  for (let row = 0; row < gameState.rows; row++) for (let col = 0; col < gameState.cols; col++) {
    const key = keyFor(row, col);
    if (pathSet.has(key)) cells[row][col].classList.add('pursuit');
    if (pelletSet.has(key)) cells[row][col].classList.add('active-dot');
    if (pulseSet.has(key)) cells[row][col].classList.add('pulse-dot-cell');
  }

  const heading = { up: -90, right: 0, down: 90, left: 180 };
  placeActor(actors[0], gameState.player, heading[gameState.direction] ?? 0);
  gameState.seekers.forEach((seeker, index) => placeActor(actors[index + 1], seeker));

  $('scoreValue').textContent = String(gameState.score).padStart(4, '0');
  $('turnValue').textContent = String(gameState.tick).padStart(4, '0');
  $('gameMessage').innerHTML = `<i class="pulse"></i> ${escapeText(gameState.message)}`;
  $('positionReadout').textContent = `LOC ${String(gameState.player[0] + 1).padStart(2, '0')}, ${String(gameState.player[1] + 1).padStart(2, '0')}`;
  $('levelValue').textContent = String(gameState.level).padStart(2, '0');
  $('remainingValue').textContent = String(gameState.remaining).padStart(3, '0');
  $('powerValue').textContent = gameState.powerTurns ? `${gameState.powerTurns} moves` : 'Inactive';

  const status = $('statusPill');
  status.textContent = gameState.status === 'playing' ? 'IN PLAY' : 'CAUGHT';
  status.className = `status-pill ${gameState.status}`;
  const expanded = gameState.explored.reduce((sum, count) => sum + count, 0);
  $('expandedValue').textContent = gameState.tick ? `${expanded} nodes / move` : '—';
  const routeLengths = gameState.paths.map(path => Math.max(0, path.length - 1));
  $('pathStats').textContent = routeLengths.length
    ? `BFS distance · ${routeLengths.map((length, index) => `S${index + 1}: ${length}`).join('  ·  ')}`
    : 'Routes recalculate after every move.';

  if (gameState.status === 'caught') showEndDialog();
}

function escapeText(text) {
  const span = document.createElement('span');
  span.textContent = text;
  return span.innerHTML;
}

function showEndDialog() {
  $('endOverlay').className = 'end-overlay caught';
  $('endIcon').textContent = '×';
  $('endKicker').textContent = 'RUN TERMINATED';
  $('endTitle').textContent = 'The seekers caught you.';
  $('endMessage').textContent = `${gameState.score} points · level ${gameState.level} · ${gameState.collected} dots collected`;
  $('endOverlay').hidden = false;
  requestAnimationFrame(() => $('endOverlay').classList.add('visible'));
  $('playAgainBtn').focus();
}

async function move(direction) {
  if (!gameState || gameState.status !== 'playing') return;
  queuedMoves.push(direction);
  if (busy) return;
  busy = true;
  try {
    while (queuedMoves.length && gameState.status === 'playing') {
      const nextDirection = queuedMoves.shift();
      gameState = await request('move', { direction: nextDirection });
      render();
    }
  } catch (error) {
    $('gameMessage').textContent = `Connection lost: ${error.message}`;
  } finally {
    busy = false;
  }
}

async function restart() {
  if (busy) return;
  busy = true;
  queuedMoves = [];
  try {
    gameState = await request('reset', {});
    renderedLevel = null;
    $('endOverlay').classList.remove('visible');
    $('endOverlay').hidden = true;
    render();
  } finally {
    busy = false;
  }
}

document.addEventListener('keydown', event => {
  const direction = directions[event.key];
  if (!direction || gameState?.status !== 'playing') return;
  event.preventDefault();
  if (!event.repeat) move(direction);
});
document.querySelectorAll('.move-key').forEach(button => {
  button.addEventListener('click', () => move(button.dataset.direction));
});
$('restartBtn').addEventListener('click', restart);
$('playAgainBtn').addEventListener('click', restart);

request('state').then(state => {
  gameState = state;
  render();
}).catch(error => {
  $('gameMessage').textContent = `Could not load the game: ${error.message}`;
});
