const API_BASE = (new URLSearchParams(window.location.search).get('api') || window.location.origin).replace(/\/$/, '');
const $ = (id) => document.getElementById(id);
let lastResult = null;

function setStatus(message, kind = '') {
  $('result-status').className = 'result-status' + (kind ? ' ' + kind : '');
  $('status-text').textContent = message;
}

function syncControls() {
  $('qubits-value').textContent = $('qubits').value;
  $('depth-value').textContent = $('depth').value;
  $('field-value').textContent = Number($('field').value).toFixed(2);
  $('shots-value').textContent = Number($('shots').value).toLocaleString();
  const disabled = !$('noise-enabled').checked;
  $('noise-inputs').classList.toggle('disabled', disabled);
  $('noise-inputs').querySelectorAll('input').forEach((input) => { input.disabled = disabled; });
  $('zz-mode').disabled = $('algorithm').value === 'random-ry';
  $('algorithm-help').textContent = $('algorithm').value === 'hva-vqe'
    ? 'Optimizes a shared-parameter HVA against the open-chain TFIM.'
    : 'Builds a reproducible RY circuit with alternating nearest-neighbor CX layers.';
}

function svgNode(name, attributes = {}, text = null) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', name);
  Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, String(value)));
  if (text !== null) node.textContent = text;
  return node;
}

function renderDistribution(probabilities) {
  const svg = $('distribution-chart');
  svg.replaceChildren();
  const entries = Object.entries(probabilities || {}).sort((a, b) => b[1] - a[1]).slice(0, 24);
  if (!entries.length) return;
  const width = 980;
  const height = 240;
  const pad = { left: 42, right: 10, top: 10, bottom: 48 };
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const maxValue = Math.max(...entries.map((entry) => entry[1]), 0.001);
  const slot = plotWidth / entries.length;
  svg.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
  svg.appendChild(svgNode('line', { x1: pad.left, y1: pad.top + plotHeight, x2: width - pad.right, y2: pad.top + plotHeight, stroke: '#344a5e', 'stroke-width': 1 }));
  [0, 0.5, 1].forEach((fraction) => {
    const y = pad.top + plotHeight * (1 - fraction);
    svg.appendChild(svgNode('line', { x1: pad.left, y1: y, x2: width - pad.right, y2: y, stroke: '#26394b', 'stroke-width': 1, 'stroke-dasharray': fraction === 0 ? '' : '3 5' }));
    svg.appendChild(svgNode('text', { x: pad.left - 8, y: y + 3, fill: '#71879a', 'font-size': 9, 'text-anchor': 'end', 'font-family': 'DM Mono, monospace' }, (fraction * maxValue).toFixed(2)));
  });
  entries.forEach(([bitstring, probability], index) => {
    const barWidth = Math.max(2, slot * 0.66);
    const barHeight = (probability / maxValue) * plotHeight;
    const x = pad.left + index * slot + (slot - barWidth) / 2;
    const y = pad.top + plotHeight - barHeight;
    const bar = svgNode('rect', { x, y, width: barWidth, height: barHeight, rx: 2, fill: index === 0 ? '#8bd7ff' : '#4d9ac6', opacity: index === 0 ? 1 : 0.78 });
    const title = svgNode('title', {}, bitstring + ': ' + (probability * 100).toFixed(2) + '%');
    bar.appendChild(title);
    svg.appendChild(bar);
    svg.appendChild(svgNode('text', { x: x + barWidth / 2, y: pad.top + plotHeight + 17, fill: '#8196a9', 'font-size': 8, 'text-anchor': 'end', transform: 'rotate(-45 ' + (x + barWidth / 2) + ' ' + (pad.top + plotHeight + 17) + ')', 'font-family': 'DM Mono, monospace' }, bitstring));
  });
}

function renderConvergence(history, exactEnergy) {
  const svg = $('convergence-chart');
  svg.replaceChildren();
  const values = (history || []).map(Number).filter(Number.isFinite);
  if (!values.length) return;
  const width = 760;
  const height = 240;
  const pad = { left: 48, right: 13, top: 12, bottom: 33 };
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  let min = Math.min(...values, Number(exactEnergy));
  let max = Math.max(...values, Number(exactEnergy));
  if (max - min < 1e-8) { min -= 0.01; max += 0.01; }
  const extra = (max - min) * 0.12;
  min -= extra;
  max += extra;
  const xAt = (index) => pad.left + (values.length < 2 ? plotWidth / 2 : index * plotWidth / (values.length - 1));
  const yAt = (value) => pad.top + ((max - value) / (max - min)) * plotHeight;
  svg.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
  [0, 0.5, 1].forEach((fraction) => {
    const y = pad.top + plotHeight * fraction;
    const value = max - (max - min) * fraction;
    svg.appendChild(svgNode('line', { x1: pad.left, y1: y, x2: width - pad.right, y2: y, stroke: '#26394b', 'stroke-width': 1, 'stroke-dasharray': fraction === 1 ? '' : '3 5' }));
    svg.appendChild(svgNode('text', { x: pad.left - 8, y: y + 3, fill: '#71879a', 'font-size': 9, 'text-anchor': 'end', 'font-family': 'DM Mono, monospace' }, value.toFixed(2)));
  });
  if (Number.isFinite(Number(exactEnergy))) {
    const exactY = yAt(Number(exactEnergy));
    svg.appendChild(svgNode('line', { x1: pad.left, y1: exactY, x2: width - pad.right, y2: exactY, stroke: '#75d5ae', 'stroke-width': 1, 'stroke-dasharray': '5 5', opacity: 0.8 }));
  }
  const path = values.map((value, index) => (index ? 'L' : 'M') + xAt(index).toFixed(1) + ' ' + yAt(value).toFixed(1)).join(' ');
  svg.appendChild(svgNode('path', { d: path, fill: 'none', stroke: '#f3a76b', 'stroke-width': 2.5, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }));
  values.forEach((value, index) => svg.appendChild(svgNode('circle', { cx: xAt(index), cy: yAt(value), r: 3, fill: '#ffc18c', stroke: '#162332', 'stroke-width': 1.2 })));
}

function formatMetric(value, digits = 6) {
  return value === null || value === undefined || !Number.isFinite(Number(value)) ? '—' : Number(value).toFixed(digits);
}

function showResult(result) {
  lastResult = result;
  $('metric-energy').textContent = formatMetric(result.ideal_energy);
  $('metric-fidelity').textContent = result.ideal_ground_fidelity === null ? '—' : (Number(result.ideal_ground_fidelity) * 100).toFixed(2) + '%';
  $('metric-noisy-fidelity').textContent = result.noisy_ground_fidelity === null ? '—' : (Number(result.noisy_ground_fidelity) * 100).toFixed(2) + '%';
  $('metric-depth').textContent = result.depth_compiled;
  $('metric-twoq').textContent = result.two_qubit_gates;
  $('observable-mx').textContent = formatMetric(result.ideal_observables.mx, 4);
  $('observable-czz').textContent = formatMetric(result.ideal_observables.czz_nn, 4);
  $('observable-mz2').textContent = formatMetric(result.ideal_observables.mz2, 4);
  $('observable-mx-noisy').textContent = result.noisy_observables ? formatMetric(result.noisy_observables.mx, 4) : '—';
  $('observable-czz-noisy').textContent = result.noisy_observables ? formatMetric(result.noisy_observables.czz_nn, 4) : '—';
  $('observable-mz2-noisy').textContent = result.noisy_observables ? formatMetric(result.noisy_observables.mz2, 4) : '—';
  $('distribution-subtitle').textContent = result.qubits + ' qubits · ' + result.algorithm + ' · highest-probability bitstrings';
  $('shots-caption').textContent = Number(result.shots).toLocaleString() + ' shots';
  $('convergence-subtitle').textContent = result.optimizer
    ? (result.optimizer_success ? 'Optimizer converged · ' : 'Optimizer stopped · ') + result.optimizer_message
    : 'Random circuit energy · no optimizer used.';
  $('optimizer-caption').textContent = result.optimizer_iterations + ' optimizer iterations';
  $('circuit-meta').textContent = result.depth_compiled + ' compiled depth · ' + result.two_qubit_gates + ' two-qubit gates · ' + result.parameter_count + ' trainable parameters';
  $('circuit-view').textContent = result.circuit_text || 'Circuit text is unavailable.';
  $('qasm-view').textContent = result.openqasm3 || result.openqasm3_error || 'OpenQASM 3 export is unavailable.';
  $('statevector-view').textContent = JSON.stringify(result.ideal_statevector, null, 2);
  $('copy-qasm').disabled = !result.openqasm3;
  $('download-json').disabled = false;
  renderDistribution(result.probabilities);
  renderConvergence(result.energy_history, result.exact_ground_energy);
  setStatus('Simulation complete · ' + result.run_kind, '');
}

async function checkHealth() {
  try {
    const response = await fetch(API_BASE + '/api/health');
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const health = await response.json();
    setStatus('Engine ready · ' + health.engine + ' · ' + health.mode);
  } catch (error) {
    setStatus('API unavailable · start the local backend to run a circuit.', 'offline');
  }
}

async function runSimulation(event) {
  event.preventDefault();
  const button = $('run-button');
  const originalText = button.querySelector('span:nth-child(2)').textContent;
  button.disabled = true;
  button.querySelector('span:nth-child(2)').textContent = 'Running on local Aer…';
  setStatus('Building, transpiling, and simulating the circuit…', 'running');
  const request = {
    algorithm: $('algorithm').value,
    qubits: Number($('qubits').value),
    depth: Number($('depth').value),
    g: Number($('field').value),
    shots: Number($('shots').value),
    seed: Number($('seed').value),
    zz_mode: $('zz-mode').value,
    noise_enabled: $('noise-enabled').checked,
    noise: {
      p1: Number($('p1').value),
      p2: Number($('p2').value),
      p_readout: Number($('preadout').value),
    },
  };
  try {
    const response = await fetch(API_BASE + '/api/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || 'Simulation request failed.');
    showResult(payload);
  } catch (error) {
    setStatus(error.message || 'Simulation failed.', 'offline');
  } finally {
    button.disabled = false;
    button.querySelector('span:nth-child(2)').textContent = originalText;
  }
}

document.querySelectorAll('#qubits, #depth, #field, #shots, #noise-enabled, #algorithm').forEach((control) => control.addEventListener('input', syncControls));
$('simulation-form').addEventListener('submit', runSimulation);
$('copy-qasm').addEventListener('click', async () => {
  if (!lastResult || !lastResult.openqasm3) return;
  try {
    await navigator.clipboard.writeText(lastResult.openqasm3);
    $('copy-qasm').textContent = 'Copied';
    window.setTimeout(() => { $('copy-qasm').textContent = 'Copy QASM'; }, 1400);
  } catch (error) {
    setStatus('Clipboard access was blocked by the browser. Select the QASM text to copy it.', 'offline');
  }
});
$('download-json').addEventListener('click', () => {
  if (!lastResult) return;
  const blob = new Blob([JSON.stringify(lastResult, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'qff-simulation-result.json';
  link.click();
  URL.revokeObjectURL(url);
});

syncControls();
checkHealth();
