// Add this to your main JavaScript file or include it on pages that need auth
async function checkAuthentication() {
    try {
        const response = await fetch('/api/auth/user');
        if (response.ok) {
            const data = await response.json();
            return data;
        }
        return null;
    } catch (error) {
        console.error('Auth check failed:', error);
        return null;
    }
}

async function logout() {
    try {
        const response = await fetch('/api/auth/logout', {
            method: 'POST'
        });
        if (response.ok) {
            window.location.href = '/';
        }
    } catch (error) {
        console.error('Logout failed:', error);
    }
}

// Update navigation based on auth status
async function updateNavigation() {
    const user = await checkAuthentication();
    const navMenu = document.getElementById('nav-menu');
    
    if (!navMenu) return;
    
    if (user && user.authenticated) {
        // User is logged in
        const authLinks = `
            <li><a href="/profile">Profile</a></li>
            <li><a href="#" id="logout-link">Logout (${user.username})</a></li>
        `;
        
        // Remove login/register links if they exist
        const existingAuth = navMenu.querySelectorAll('.auth-link');
        existingAuth.forEach(link => link.remove());
        
        // Add logged-in links
        navMenu.insertAdjacentHTML('beforeend', authLinks);
        
        document.getElementById('logout-link').addEventListener('click', (e) => {
            e.preventDefault();
            logout();
        });
    } else {
        // User is not logged in
        const authLinks = `
            <li class="auth-link"><a href="/login">Login</a></li>
            <li class="auth-link"><a href="/register">Register</a></li>
        `;
        
        // Remove profile/logout links if they exist
        const profileLink = navMenu.querySelector('a[href="/profile"]');
        const logoutLink = navMenu.querySelector('#logout-link');
        if (profileLink) profileLink.parentElement.remove();
        if (logoutLink) logoutLink.parentElement.remove();
        
        // Add login/register links if not already present
        if (!navMenu.querySelector('.auth-link')) {
            navMenu.insertAdjacentHTML('beforeend', authLinks);
        }
    }
}

// Call on page load
document.addEventListener('DOMContentLoaded', updateNavigation);