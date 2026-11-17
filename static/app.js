const EMPTY = 0, WALL = 1, EXIT = 2, START = 3, VISITED = 4, PATH = 5;
const colors = { 0: 'empty', 1: 'wall', 2: 'exit', 3: 'start', 4: 'visited', 5: 'path' };
const stages = {
  1: ['Draw the walls', 'Click or drag across the grid to mark obstacles and shape your building.', 'Walls are the first step in planning a safe evacuation.', 'Click and drag to draw walls', '01', '▦'],
  2: ['Place emergency exits', 'Mark one or more exits where people can leave the building.', 'Add at least one exit, then continue to your starting point.', 'Click cells to add or remove exits', '02', '↗'],
  3: ['Set the starting point', 'Choose where the person begins their evacuation.', 'Set one starting point to enable the simulation.', 'Click a walkable cell to set start', '03', '◎'],
  4: ['Finding a safe route…', 'Breadth-first search is exploring every reachable corridor.', 'Follow the amber exploration wave and cyan shortest path.', 'SIMULATION IN PROGRESS', '—', '◌'],
  5: ['Simulation complete', 'Review the result below or reset to try another route.', 'The shortest accessible route has been calculated.', 'SIMULATION COMPLETE', '—', '✓']
};
const $ = id => document.getElementById(id);
const gridEl = $('grid');
let state, dragging = false, dragMode = 'place', locked = false;
let animationTimer = null, animationEvents = [], animationIndex = 0, debugMode = false, animationDelay = 60;

async function api(path, body = {}) {
  const options = { method: path === 'state' ? 'GET' : 'POST', headers: { 'Content-Type': 'application/json' } };
  if (path !== 'state') options.body = JSON.stringify(body);
  const response = await fetch(`/api/${path}`, options);
  if (!response.ok) throw new Error(`Request failed: ${path}`);
  return response.json();
}

function cellAtPoint(x, y) {
  const el = document.elementFromPoint(x, y)?.closest('.cell');
  return el && gridEl.contains(el) ? [+el.dataset.row, +el.dataset.col] : null;
}
function cellPayload(event) { return cellAtPoint(event.clientX, event.clientY); }

function drawGrid() {
  const fragment = document.createDocumentFragment();
  gridEl.style.setProperty('--cols', GRID_SIZE.cols);
  for (let row = 0; row < GRID_SIZE.rows; row++) for (let col = 0; col < GRID_SIZE.cols; col++) {
    const cell = document.createElement('button');
    cell.className = `cell ${colors[state.grid[row][col]]}`;
    cell.dataset.row = row; cell.dataset.col = col;
    cell.setAttribute('role', 'gridcell');
    cell.setAttribute('aria-label', `Row ${row + 1}, column ${col + 1}`);
    fragment.append(cell);
  }
  gridEl.replaceChildren(fragment);
}

function render(skipGrid = false) {
  if (!state) return;
  if (!skipGrid) drawGrid();
  const stage = state.stage, copy = stages[stage];
  $('stageTitle').textContent = copy[0]; $('stageDescription').textContent = copy[1];
  $('stageMessage').textContent = copy[2]; $('editHint').textContent = copy[3];
  $('stepCounter').innerHTML = `${copy[4]} <i>/ 03</i>`; $('stageIcon').textContent = copy[5];
  $('progressBar').style.width = `${stage < 4 ? stage * 33.333 : 100}%`;
  $('mapStatus').textContent = stage === 4 ? 'BFS RUNNING' : stage === 5 ? 'ROUTE FOUND' : 'EDIT MODE';
  document.querySelectorAll('.workflow-step').forEach((step, index) => {
    const number = index + 1;
    step.classList.toggle('active', stage === number);
    step.classList.toggle('complete', stage > number);
  });
  $('wallCount').textContent = `${state.grid.flat().filter(cell => cell === WALL).length} cells`;
  $('exitCount').textContent = `${state.exits.length} ${state.exits.length === 1 ? 'exit' : 'exits'}`;
  $('startValue').textContent = state.start ? `(${state.start[0]}, ${state.start[1]})` : 'Not set';
  $('nextBtn').hidden = stage === 3 || stage >= 4; $('backBtn').hidden = stage === 1 || stage >= 4;
  $('startBtn').hidden = stage !== 3;
  $('nextBtn').innerHTML = stage === 1 ? 'Choose exits <span>→</span>' : 'Set starting point <span>→</span>';
  $('startBtn').disabled = stage !== 3 || !state.start || !state.exits.length;
  $('resetBtn').disabled = stage !== 4 && stage !== 5;
  $('stepBtn').disabled = stage < 3 || stage === 5;
  $('stepLabel').textContent = debugMode ? 'Advance one step' : 'Step-by-step debug';
  $('exportBtn').disabled = !state.path?.length;
  $('clearBtn').disabled = stage === 4;
  $('resultText').textContent = state.result;
  $('resultCard').className = `result-card ${state.resultType || ''}`;
  $('startBtn').classList.toggle('ready', !$('startBtn').disabled);
}

async function sync() { state = await api('state'); render(); }
function paint(row, col, value) {
  const cell = gridEl.querySelector(`[data-row="${row}"][data-col="${col}"]`);
  if (!cell) return;
  cell.className = `cell ${colors[value]}`;
  cell.animate([{ transform: 'scale(.72)', filter: 'brightness(1.8)' }, { transform: 'scale(1)', filter: 'brightness(1)' }], { duration: 190, easing: 'cubic-bezier(.2,.8,.2,1)' });
}
async function clickCell(row, col, action) {
  state = await api('cell', { row, col, action }); render(true);
  const cell = gridEl.querySelector(`[data-row="${row}"][data-col="${col}"]`);
  if (cell) { cell.className = `cell ${colors[state.grid[row][col]]}`; cell.animate([{ transform: 'scale(.82)' }, { transform: 'scale(1)' }], { duration: 150 }); }
}

async function handleCellPointer(event) {
  if (!dragging || !state || state.stage !== 1) return;
  const cell = cellPayload(event); if (!cell) return;
  const [row, col] = cell;
  if ((dragMode === 'place' && state.grid[row][col] === EMPTY) || (dragMode === 'erase' && state.grid[row][col] === WALL)) {
    await clickCell(row, col, dragMode);
  }
}
gridEl.addEventListener('pointerdown', async event => {
  const cell = cellPayload(event); if (!cell || locked) return;
  event.preventDefault(); dragging = true;
  const [row, col] = cell;
  if (state.stage === 1) { dragMode = state.grid[row][col] === WALL ? 'erase' : 'place'; await clickCell(row, col, dragMode); }
  else { dragging = false; await clickCell(row, col); }
});
gridEl.addEventListener('pointermove', event => {
  const cell = cellPayload(event);
  $('coordReadout').textContent = cell ? `ROW ${String(cell[0] + 1).padStart(2, '0')}   COL ${String(cell[1] + 1).padStart(2, '0')}` : 'ROW --   COL --';
  if (dragging && event.buttons) handleCellPointer(event);
});
gridEl.addEventListener('pointerover', handleCellPointer);
window.addEventListener('pointerup', () => { dragging = false; });
window.addEventListener('pointercancel', () => { dragging = false; });

$('nextBtn').onclick = async () => { state = await api('navigate', { action: 'next' }); render(); };
$('backBtn').onclick = async () => { state = await api('navigate', { action: 'back' }); render(); };
$('speedControl').onclick = async event => {
  if (!event.target.matches('button')) return;
  document.querySelectorAll('#speedControl button').forEach(button => button.classList.toggle('selected', button === event.target));
  state = await api('speed', { speed: event.target.dataset.speed });
};
$('algorithmBtn').onclick = () => {
  const note = $('algorithmNote'), open = note.hidden;
  note.hidden = !open; $('algorithmBtn').setAttribute('aria-expanded', String(open));
};
$('clearBtn').onclick = async () => { if (!locked) { state = await api('clear'); debugMode = false; render(); } };
$('resetBtn').onclick = async () => {
  clearTimeout(animationTimer); animationTimer = null; locked = false; animationEvents = []; animationIndex = 0;
  state = await api('reset'); render();
};

function finishAnimation() {
  clearTimeout(animationTimer); animationTimer = null;
  api('finish').then(result => {
    state = result; locked = false; render();
    if (state.stage === 5) showResultDialog();
  });
}
function showResultDialog() {
  const found = state.resultType === 'success';
  $('resultOverlay').className = `result-overlay ${found ? 'success' : 'failure'}`;
  $('dialogEyebrow').textContent = found ? 'ROUTE ANALYSIS COMPLETE' : 'ROUTE ANALYSIS FINISHED';
  $('dialogGlyph').textContent = found ? '✓' : '×';
  $('dialogTitle').textContent = found ? 'Evacuation route found' : 'No accessible exit found';
  $('dialogMessage').textContent = state.result;
  $('resultOverlay').hidden = false;
  requestAnimationFrame(() => $('resultOverlay').classList.add('visible'));
  $('dialogClose').focus();
}
function closeResultDialog() {
  const overlay = $('resultOverlay');
  overlay.classList.remove('visible');
  window.setTimeout(() => { overlay.hidden = true; }, 220);
}
async function resetFromDialog() {
  closeResultDialog();
  state = await api('reset'); render();
}
$('dialogClose').onclick = closeResultDialog;
$('dialogCloseIcon').onclick = closeResultDialog;
$('dialogReset').onclick = resetFromDialog;
$('resultOverlay').addEventListener('click', event => {
  if (event.target === $('resultOverlay')) closeResultDialog();
});
window.addEventListener('keydown', event => {
  if (event.key === 'Escape' && !$('resultOverlay').hidden) closeResultDialog();
});
function advanceAnimation() {
  if (animationIndex >= animationEvents.length) { finishAnimation(); return; }
  const [row, col, value] = animationEvents[animationIndex++];
  if (state.grid[row][col] !== START && state.grid[row][col] !== EXIT) paint(row, col, value);
  if (animationIndex >= animationEvents.length) { animationTimer = setTimeout(finishAnimation, animationDelay); return; }
  if (!debugMode) animationTimer = setTimeout(advanceAnimation, animationDelay);
}
$('startBtn').onclick = async () => {
  state = await api('start'); render(); if (state.stage !== 4) return;
  locked = true; animationIndex = 0; animationEvents = [];
  state.explored.forEach(([row, col]) => animationEvents.push([row, col, VISITED]));
  state.path.forEach(([row, col]) => animationEvents.push([row, col, PATH]));
  animationDelay = { Slow: 150, Normal: 60, Fast: 15 }[state.speed] || 60;
  if (!debugMode) animationTimer = setTimeout(advanceAnimation, animationDelay);
};
$('stepBtn').onclick = () => {
  if (state?.stage === 4 && debugMode) advanceAnimation();
  else {
    debugMode = !debugMode;
    if (debugMode) clearTimeout(animationTimer);
    else if (state?.stage === 4 && animationIndex < animationEvents.length) animationTimer = setTimeout(advanceAnimation, animationDelay);
    render();
  }
};
$('exportBtn').onclick = () => {
  if (!state?.path?.length) return;
  const data = { algorithm: 'Breadth-First Search', grid: { rows: GRID_SIZE.rows, columns: GRID_SIZE.cols }, start: state.start, exits: state.exits, path: state.path, steps: state.path.length - 1 };
  const link = document.createElement('a'); link.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
  link.download = 'smartevac-route.json'; link.click(); URL.revokeObjectURL(link.href);
};
sync().catch(error => { $('resultText').textContent = `Unable to connect to the planner: ${error.message}`; });
