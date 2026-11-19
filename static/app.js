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
let soundEnabled = false;
let volume = 0.6;
let audioContext = null;
let previousCollectibles = new Set();
let levelTotal = 0;
let runStartedAt = 0;
let levelStartedAt = 0;

function setTheme(theme) {
  const light = theme === 'light';
  document.body.dataset.theme = light ? 'light' : 'dark';
  $('themeToggle').setAttribute('aria-pressed', String(light));
  $('themeToggle').setAttribute('aria-label', `Switch to ${light ? 'dark' : 'light'} theme`);
  $('themeToggle').querySelector('.theme-icon').textContent = light ? '☾' : '☼';
  $('themeToggle').querySelector('.theme-label').textContent = light ? 'DARK MODE' : 'LIGHT MODE';
  document.querySelector('meta[name="theme-color"]').content = light ? '#f4e9e2' : '#190f20';
  localStorage.setItem('nodeRunTheme', light ? 'light' : 'dark');
}

if (window.matchMedia('(pointer: fine)').matches && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  window.addEventListener('pointermove', event => {
    const x = (event.clientX / window.innerWidth - 0.5) * 2;
    const y = (event.clientY / window.innerHeight - 0.5) * 2;
    document.body.style.setProperty('--scene-x', `${x * -10}px`);
    const cabinet = document.querySelector('.cabinet-wrap');
    if (cabinet) {
      cabinet.style.setProperty('--cabinet-x', `${(x * 3).toFixed(2)}px`);
      cabinet.style.setProperty('--cabinet-y', `${(y * 2).toFixed(2)}px`);
    }
  }, { passive: true });
}

async function request(path, body) {
  const response = await fetch(`/api/${path}`, {
    method: body ? 'POST' : 'GET',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  });
  if (!response.ok) throw new Error(`Game request failed: ${path}`);
  return response.json();
}

const keyFor = cell => `${cell[0]},${cell[1]}`;
const cellSet = cells => new Set(cells.map(keyFor));

function buildPreview() {
  if (!gameState) return;
  const preview = $('previewMaze');
  preview.style.setProperty('--cols', gameState.cols);
  preview.style.setProperty('--rows', gameState.rows);
  const pellets = cellSet(gameState.pellets);
  const cellsFragment = document.createDocumentFragment();
  for (let row = 0; row < gameState.rows; row++) for (let col = 0; col < gameState.cols; col++) {
    const node = document.createElement('i');
    node.className = `preview-cell ${gameState.grid[row][col] === WALL ? 'wall' : 'floor'}`;
    if (pellets.has(`${row},${col}`)) node.classList.add('has-dot');
    cellsFragment.append(node);
  }
  const route = gameState.paths?.[0] || [];
  route.forEach(([row, col]) => cellsFragment.childNodes[row * gameState.cols + col]?.classList.add('route'));
  preview.replaceChildren(cellsFragment);
}

function createBoard() {
  previousCollectibles = new Set();
  levelTotal = gameState.pellets.length + gameState.pulses.length;
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
  actors[0].className = 'actor player-actor';
  actors[0].setAttribute('aria-label', 'You');
  actorLayer.append(actors[0]);
  for (let index = 0; index < 3; index++) {
    const actor = document.createElement('div');
    actor.className = `actor seeker-actor seeker-${index}`;
    actor.setAttribute('aria-label', `BFS seeker ${index + 1}`);
    actors.push(actor);
    actorLayer.append(actor);
  }
  fragment.append(actorLayer);
  board.replaceChildren(fragment);
  renderedLevel = gameState.level;
}

function placeActor(actor, cell) {
  actor.style.left = `${(cell[1] + 0.5) / gameState.cols * 100}%`;
  actor.style.top = `${(cell[0] + 0.5) / gameState.rows * 100}%`;
}

function selectedSearch() {
  const index = Number($('seekerSelect').value);
  const trace = gameState.traces?.[index] || [];
  const discoveries = gameState.discovered?.[index] || [];
  const paths = gameState.paths?.[index] || [];
  const step = Math.min(Number($('traceSlider').value) || 0, Math.max(0, trace.length - 1));
  const frame = trace[step];
  return { index, trace, discoveries, paths, frame, step };
}

function renderTrace() {
  if (!gameState) return;
  const { index, trace, discoveries, paths, frame, step } = selectedSearch();
  const discoveredCount = frame?.discovered || 0;
  const expanded = frame ? step + 1 : 0;
  const discovered = discoveries.slice(0, discoveredCount);
  const visitedSet = cellSet(discovered);
  const frontierSet = cellSet(frame?.frontier || []);
  const pathSet = cellSet(paths);
  for (const row of cells) for (const cell of row) cell.classList.remove('trace-visited', 'trace-frontier', 'trace-current', 'trace-path');
  for (const cell of discovered) cells[cell[0]]?.[cell[1]]?.classList.add('trace-visited');
  for (const cell of frontierSet) { const [row, col] = cell.split(',').map(Number); cells[row]?.[col]?.classList.add('trace-frontier'); }
  for (const cell of paths) cells[cell[0]]?.[cell[1]]?.classList.add('trace-path');
  if (frame) cells[frame.current[0]]?.[frame.current[1]]?.classList.add('trace-current');
  $('expandedValue').textContent = expanded;
  $('frontierValue').textContent = frontierSet.size;
  $('pathValue').textContent = paths.length ? `${paths.length - 1} STEPS` : 'NO ROUTE';
  $('stepValue').textContent = trace.length ? `${String(step + 1).padStart(2, '0')} / ${String(trace.length).padStart(2, '0')}` : '—';
  $('traceFoot').textContent = frame
    ? `Seeker ${index + 1} is expanding ${frame.current[0] + 1}:${frame.current[1] + 1}. The queue is the next layer to inspect.`
    : 'Move once to record a search.';
  $('traceSlider').max = Math.max(0, trace.length - 1);
  $('traceSlider').value = step;
  $('traceSlider').disabled = !trace.length;
  $('distance' + index).textContent = paths.length ? `${paths.length - 1} STEPS` : '—';
  $('distance' + index).classList.add('distance-live');
  for (let other = 0; other < 3; other++) if (other !== index) {
    const route = gameState.paths?.[other] || [];
    $('distance' + other).textContent = route.length ? `${route.length - 1} STEPS` : '—';
    $('distance' + other).classList.remove('distance-live');
  }
}

function makeCollectEffect(cellKey, isPulse) {
  if (!cellKey) return;
  const [row, col] = cellKey.split(',').map(Number);
  const effect = document.createElement('i');
  effect.className = `collect-effect ${isPulse ? 'pulse-effect' : ''}`;
  effect.style.left = `${(col + 0.5) / gameState.cols * 100}%`;
  effect.style.top = `${(row + 0.5) / gameState.rows * 100}%`;
  board.append(effect);
  setTimeout(() => effect.remove(), 650);
}

function render() {
  if (!gameState) return;
  if (!cells.length || renderedLevel !== gameState.level) createBoard();
  const pelletSet = cellSet(gameState.pellets);
  const pulseSet = cellSet(gameState.pulses);
  const collectibleSet = new Set([...pelletSet, ...pulseSet]);
  for (const row of cells) for (const cell of row) cell.classList.remove('active-dot', 'pulse-dot-cell', 'pursuit');
  for (let row = 0; row < gameState.rows; row++) for (let col = 0; col < gameState.cols; col++) {
    const key = `${row},${col}`;
    if (pelletSet.has(key)) cells[row][col].classList.add('active-dot');
    if (pulseSet.has(key)) cells[row][col].classList.add('pulse-dot-cell');
  }
  if (previousCollectibles.size) for (const key of previousCollectibles) if (!collectibleSet.has(key)) makeCollectEffect(key, !pelletSet.has(key) && gameState.collected > 0 && Number($('scoreValue').textContent) < gameState.score);
  previousCollectibles = collectibleSet;

  board.classList.toggle('pulsed', Boolean(gameState.powerTurns));
  placeActor(actors[0], gameState.player);
  gameState.seekers.forEach((seeker, index) => placeActor(actors[index + 1], seeker));
  $('scoreValue').textContent = String(gameState.score).padStart(4, '0');
  $('turnValue').textContent = `TURN ${String(gameState.tick).padStart(3, '0')}`;
  $('gameMessage').textContent = gameState.message;
  $('positionReadout').textContent = `${String(gameState.player[0] + 1).padStart(2, '0')} / ${String(gameState.player[1] + 1).padStart(2, '0')}`;
  $('levelValue').textContent = String(gameState.level).padStart(2, '0');
  $('remainingValue').textContent = `${String(gameState.remaining).padStart(3, '0')} LEFT`;
  $('powerValue').textContent = gameState.powerTurns ? `PULSE ${gameState.powerTurns}` : 'PULSE OFF';
  $('powerValue').classList.toggle('power-active', Boolean(gameState.powerTurns));
  $('statusText').textContent = gameState.status === 'playing' ? 'LIVE RUN' : 'RUN ENDED';
  const clearedThisLevel = Math.max(0, levelTotal - gameState.remaining);
  $('progressBar').style.width = `${levelTotal ? clearedThisLevel / levelTotal * 100 : 100}%`;
  renderTrace();
  if (gameState.status === 'caught') showEndDialog();
}

function showEndDialog() {
  $('endIcon').textContent = '×';
  $('endKicker').textContent = 'RUN TERMINATED';
  $('endTitle').textContent = 'The search caught up.';
  $('endMessage').textContent = gameState.message;
  $('finalScore').textContent = gameState.score;
  $('finalDots').textContent = gameState.collected;
  $('finalTurns').textContent = gameState.tick;
  const elapsed = Math.max(0, Math.floor((Date.now() - runStartedAt) / 1000));
  $('finalTime').textContent = `${String(Math.floor(elapsed / 60)).padStart(2, '0')}:${String(elapsed % 60).padStart(2, '0')}`;
  board.classList.remove('hit'); void board.offsetWidth; board.classList.add('hit');
  $('endOverlay').hidden = false;
  requestAnimationFrame(() => $('endOverlay').classList.add('visible'));
  $('playAgainBtn').focus();
  playTone(150, 0.18, 'sawtooth');
}

function playTone(frequency, duration = 0.07, type = 'sine') {
  if (!soundEnabled) return;
  try {
    audioContext ||= new (window.AudioContext || window.webkitAudioContext)();
    if (audioContext.state === 'suspended') audioContext.resume();
    const oscillator = audioContext.createOscillator();
    const gain = audioContext.createGain();
    oscillator.type = type;
    oscillator.frequency.setValueAtTime(frequency, audioContext.currentTime);
    gain.gain.setValueAtTime(0.06 * volume, audioContext.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + duration);
    oscillator.connect(gain).connect(audioContext.destination);
    oscillator.start();
    oscillator.stop(audioContext.currentTime + duration);
  } catch (_) { /* Sound is optional; gameplay remains available without Web Audio. */ }
}

async function move(direction) {
  if (!gameState || gameState.status !== 'playing' || $('gameScreen').hidden || !$('levelOverlay').hidden) return;
  queuedMoves.push(direction);
  if (busy) return;
  busy = true;
  try {
    while (queuedMoves.length && gameState.status === 'playing') {
      const nextDirection = queuedMoves.shift();
      const oldLevel = gameState.level;
      const oldScore = gameState.score;
      const oldLevelTotal = levelTotal;
      gameState = await request('move', { direction: nextDirection });
      render();
      if (gameState.score > oldScore) playTone(gameState.score - oldScore >= 50 ? 760 : 520, 0.1);
      else playTone(260, 0.035);
      if (gameState.level > oldLevel) {
        $('levelMessage').textContent = `Level ${oldLevel} cleared. A new random maze is ready.`;
        $('levelScore').textContent = gameState.score;
        $('levelCleared').textContent = oldLevelTotal;
        const levelElapsed = Math.max(0, Math.floor((Date.now() - levelStartedAt) / 1000));
        $('levelTime').textContent = `${String(Math.floor(levelElapsed / 60)).padStart(2, '0')}:${String(levelElapsed % 60).padStart(2, '0')}`;
        levelStartedAt = Date.now();
        $('levelOverlay').hidden = false;
        requestAnimationFrame(() => $('levelOverlay').classList.add('visible'));
        queuedMoves = [];
      }
    }
  } catch (error) {
    $('gameMessage').textContent = `Connection lost: ${error.message}`;
  } finally { busy = false; }
}

async function restart() {
  if (busy) return;
  busy = true;
  queuedMoves = [];
  try {
    gameState = await request('reset', {});
    runStartedAt = Date.now();
    levelStartedAt = runStartedAt;
    renderedLevel = null;
    previousCollectibles = new Set();
    $('endOverlay').classList.remove('visible');
    $('endOverlay').hidden = true;
    $('levelOverlay').classList.remove('visible');
    $('levelOverlay').hidden = true;
    render();
  } catch (error) {
    $('gameMessage').textContent = `Could not restart: ${error.message}`;
  } finally { busy = false; }
}

async function enterGame() {
  if (!gameState) return;
  runStartedAt = Date.now();
  levelStartedAt = runStartedAt;
  $('welcomeScreen').hidden = true;
  $('gameScreen').hidden = false;
  await restart();
  render();
  $('gameScreen').classList.add('screen-enter');
}

$('startBtn').addEventListener('click', enterGame);
$('brandHome').addEventListener('click', async event => { event.preventDefault(); await restart(); $('gameScreen').hidden = true; $('welcomeScreen').hidden = false; buildPreview(); });
$('backBtn').addEventListener('click', async () => { await restart(); $('gameScreen').hidden = true; $('welcomeScreen').hidden = false; buildPreview(); });
$('restartBtn').addEventListener('click', restart);
$('playAgainBtn').addEventListener('click', restart);
$('outcomeHomeBtn').addEventListener('click', async () => { await restart(); $('endOverlay').classList.remove('visible'); $('endOverlay').hidden = true; $('gameScreen').hidden = true; $('welcomeScreen').hidden = false; buildPreview(); });
$('continueBtn').addEventListener('click', () => { $('levelOverlay').classList.remove('visible'); setTimeout(() => $('levelOverlay').hidden = true, 180); });
$('soundToggle').addEventListener('click', () => {
  soundEnabled = !soundEnabled;
  $('soundToggle').setAttribute('aria-pressed', String(soundEnabled));
  $('soundToggle').querySelector('span:last-child').textContent = soundEnabled ? 'Sound on' : 'Sound off';
  if (soundEnabled) playTone(660, 0.08);
});
$('volumeSlider').addEventListener('input', event => { volume = Number(event.target.value) / 100; });
$('themeToggle').addEventListener('click', () => setTheme(document.body.dataset.theme === 'light' ? 'dark' : 'light'));
$('seekerSelect').addEventListener('change', renderTrace);
$('traceSlider').addEventListener('input', renderTrace);
document.querySelectorAll('.dpad button').forEach(button => button.addEventListener('click', () => move(button.dataset.direction)));
document.addEventListener('keydown', event => {
  const direction = directions[event.key];
  if (!direction || gameState?.status !== 'playing' || $('gameScreen').hidden || !$('levelOverlay').hidden) return;
  if (event.target.matches('input, select, textarea, [contenteditable="true"]')) return;
  event.preventDefault();
  if (!event.repeat) move(direction);
});

request('state').then(state => { gameState = state; buildPreview(); }).catch(error => {
  $('startBtn').disabled = true;
  $('gameMessage').textContent = `Could not load the game: ${error.message}`;
  $('previewMaze').textContent = 'Game server unavailable';
});

setTheme(localStorage.getItem('nodeRunTheme') || 'dark');
