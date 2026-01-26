let fleetsData = [];

async function loadFleets() {
    const response = await fetch('/api/fleets');
    fleetsData = await response.json();
    
    const select = document.getElementById('simulationFleetId');
    select.innerHTML = '<option value="">Select a fleet...</option>' + 
        fleetsData.map(fleet => `<option value="${fleet.id}">${fleet.name} (${fleet.vehicle_count} vehicles)</option>`).join('');
}

async function loadSimulations() {
    const response = await fetch('/api/simulations');
    const simulations = await response.json();
    const tbody = document.querySelector('#simulationsTable tbody');
    tbody.innerHTML = simulations.map(sim => `
        <tr>
            <td>${sim.id}</td>
            <td>${sim.name}</td>
            <td>${sim.fleet ? sim.fleet.name : 'N/A'}</td>
            <td><span class="badge badge-${sim.status}">${sim.status}</span></td>
            <td>${sim.results || 'No results yet'}</td>
            <td>${new Date(sim.created_at).toLocaleDateString()}</td>
            <td class="actions">
                ${sim.status === 'pending' ? `<button class="btn btn-success" onclick="runSimulation(${sim.id})">Run</button>` : ''}
                <button class="btn" onclick="editSimulation(${sim.id})">Edit</button>
                <button class="btn btn-danger" onclick="deleteSimulation(${sim.id})">Delete</button>
            </td>
        </tr>
    `).join('');
}

function openModal() {
    document.getElementById('simulationModal').classList.add('active');
    document.getElementById('modalTitle').textContent = 'Create Simulation';
    document.getElementById('simulationForm').reset();
    document.getElementById('simulationId').value = '';
}

function closeModal() {
    document.getElementById('simulationModal').classList.remove('active');
}

async function editSimulation(id) {
    const response = await fetch(`/api/simulations/${id}`);
    const simulation = await response.json();
    document.getElementById('simulationId').value = simulation.id;
    document.getElementById('simulationName').value = simulation.name;
    document.getElementById('simulationFleetId').value = simulation.fleet_id;
    document.getElementById('modalTitle').textContent = 'Edit Simulation';
    document.getElementById('simulationModal').classList.add('active');
}

async function saveSimulation(event) {
    event.preventDefault();
    const id = document.getElementById('simulationId').value;
    const simulation = {
        name: document.getElementById('simulationName').value,
        fleet_id: parseInt(document.getElementById('simulationFleetId').value)
    };

    const url = id ? `/api/simulations/${id}` : '/api/simulations';
    const method = id ? 'PUT' : 'POST';

    await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(simulation)
    });

    closeModal();
    loadSimulations();
}

async function deleteSimulation(id) {
    if (!confirm('Are you sure you want to delete this simulation?')) return;
    await fetch(`/api/simulations/${id}`, { method: 'DELETE' });
    loadSimulations();
}

async function runSimulation(id) {
    if (!confirm('Start this simulation?')) return;
    await fetch(`/api/simulations/${id}/run`, { method: 'POST' });
    alert('Simulation started! Refresh in a few seconds to see results.');
    setTimeout(loadSimulations, 1000);
}

loadFleets();
loadSimulations();
setInterval(loadSimulations, 5000); // Auto-refresh every 5 seconds