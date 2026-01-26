async function loadUsers() {
    const response = await fetch('/api/users');
    const users = await response.json();
    const tbody = document.querySelector('#usersTable tbody');
    tbody.innerHTML = users.map(user => `
        <tr>
            <td>${user.id}</td>
            <td>${user.name}</td>
            <td>${user.email}</td>
            <td><span class="badge ${user.is_admin ? 'badge-admin' : 'badge-user'}">${user.is_admin ? 'Admin' : 'User'}</span></td>
            <td>${new Date(user.created_at).toLocaleDateString()}</td>
            <td class="actions">
                <button class="btn" onclick="editUser(${user.id})">Edit</button>
                <button class="btn btn-danger" onclick="deleteUser(${user.id})">Delete</button>
            </td>
        </tr>
    `).join('');
}

function openModal() {
    document.getElementById('userModal').classList.add('active');
    document.getElementById('modalTitle').textContent = 'Add User';
    document.getElementById('userForm').reset();
    document.getElementById('userId').value = '';
}

function closeModal() {
    document.getElementById('userModal').classList.remove('active');
}

async function editUser(id) {
    const response = await fetch(`/api/users/${id}`);
    const user = await response.json();
    document.getElementById('userId').value = user.id;
    document.getElementById('userName').value = user.name;
    document.getElementById('userEmail').value = user.email;
    document.getElementById('userRole').value = user.is_admin;
    document.getElementById('modalTitle').textContent = 'Edit User';
    document.getElementById('userModal').classList.add('active');
}

async function saveUser(event) {
    event.preventDefault();
    const id = document.getElementById('userId').value;
    const user = {
        name: document.getElementById('userName').value,
        email: document.getElementById('userEmail').value,
        is_admin: document.getElementById('userRole').value === 'true'
    };

    const url = id ? `/api/users/${id}` : '/api/users';
    const method = id ? 'PUT' : 'POST';

    await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(user)
    });

    closeModal();
    loadUsers();
}

async function deleteUser(id) {
    if (!confirm('Are you sure you want to delete this user?')) return;
    await fetch(`/api/users/${id}`, { method: 'DELETE' });
    loadUsers();
}

loadUsers();