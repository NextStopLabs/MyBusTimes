async function loadFleets() {
    const response = await fetch('/api/fleets');
    const fleets = await response.json();
    const tbody = document.querySelector('#fleetsTable tbody');
    tbody.innerHTML = fleets.map(fleet => `
        <tr>
            <td>${fleet.id}</td>
            <td>${fleet.name}</td>
            <td>${fleet.vehicle_count}</td>
            <td><span class="badge ${fleet.status === 'active' ? 'badge-active' : 'badge-inactive'}">${fleet.status}</span></td>
            <td>${new Date(fleet.created_at).toLocaleDateString()}</td>
            <td class="actions">
                <button class="btn" onclick="editFleet(${fleet.id})">Edit</button>
                <button class="btn btn-danger" onclick="deleteFleet(${fleet.id})">Delete</button>
            </td>
        </tr>
    `).join('');
}

function openModal() {
    document.getElementById('fleetModal').classList.add('active');
    document.getElementById('modalTitle').textContent = 'Add Fleet';
    document.getElementById('fleetForm').reset();
    document.getElementById('fleetId').value = '';
}

function closeModal() {
    document.getElementById('fleetModal').classList.remove('active');
}

async function editFleet(id) {
    const response = await fetch(`/api/fleets/${id}`);
    const fleet = await response.json();
    document.getElementById('fleetId').value = fleet.id;
    document.getElementById('fleetName').value = fleet.name;
    document.getElementById('fleetVehicleCount').value = fleet.vehicle_count;
    document.getElementById('fleetStatus').value = fleet.status;
    document.getElementById('modalTitle').textContent = 'Edit Fleet';
    document.getElementById('fleetModal').classList.add('active');
}

async function saveFleet(event) {
    event.preventDefault();
    const id = document.getElementById('fleetId').value;
    const fleet = {
        name: document.getElementById('fleetName').value,
        vehicle_count: parseInt(document.getElementById('fleetVehicleCount').value),
        status: document.getElementById('fleetStatus').value
    };

    const url = id ? `/api/fleets/${id}` : '/api/fleets';
    const method = id ? 'PUT' : 'POST';

    await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(fleet)
    });

    closeModal();
    loadFleets();
}

async function deleteFleet(id) {
    if (!confirm('Are you sure you want to delete this fleet?')) return;
    await fetch(`/api/fleets/${id}`, { method: 'DELETE' });
    loadFleets();
}

loadFleets();