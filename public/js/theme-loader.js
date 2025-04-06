document.addEventListener('DOMContentLoaded', () => {
    let username = document.cookie.split('; ').find(row => row.startsWith('username='))?.split('=')[1];

    if (username) {
        document.getElementById("login-profile").textContent = 'My Profile';
        document.getElementById("login-profile").href = '/u/' + username;
    } else {
        document.getElementById("login-profile").textContent = 'Login';
        document.getElementById("login-profile").href = '/login';
    }

    let themeID = document.cookie.split('; ').find(row => row.startsWith('theme='))?.split('=')[1];

    if (!themeID) {
        themeID = 1;
    }

    applyTheme(themeID);

    function applyTheme(id) {
        fetch(`http://localhost:8000/api/themes/${id}`)
            .then(response => response.json())
            .then(data => {
                const themeCSS = data.css;
                const dark = data.dark_theme;

                if (dark === false) {
                    document.getElementById('logo').src = '/src/icons/MBT-Logo-Black.png';
                    document.getElementById('menu').src = '/src/icons/Burger-Menu-Black.png';
                } else if (dark === true) {
                    document.getElementById('logo').src = '/src/icons/MBT-Logo-White.png';
                    document.getElementById('menu').src = '/src/icons/Burger-Menu-White.png';
                } else {
                    document.getElementById('logo').src = '/src/icons/MBT-Logo-Black.png';
                    document.getElementById('menu').src = '/src/icons/Burger-Menu-Black.png';
                }

                const root = document.documentElement;
                root.style.cssText = themeCSS;
            })
            .catch(error => {
                console.error('Error fetching themes:', error);
            });
    }
    fetch('http://localhost:8000/api/themes/')
        .then(response => response.json())
        .then(data => {
            const themeSelect = document.getElementById('theme-selector');
            data.forEach(theme => {
                const option = document.createElement('option');
                option.value = theme.id;
                option.textContent = theme.theme_name;
                themeSelect.appendChild(option);
            });

            themeSelect.value = themeID;
        })
        .catch(error => {
            console.error('Error fetching themes:', error);
        });

    function getCookie(name) {
        let matches = document.cookie.match(new RegExp(
            "(?:^|; )" + name.replace(/([\.$?*|{}\(\)\[\]\\\/\+\-])/g, '\\$1') + "=([^;]*)"
        ));
        return matches ? decodeURIComponent(matches[1]) : undefined;
    }

    function refreshAccessToken() {
        const refreshToken = getCookie('refresh_token'); // Get the refresh token from the cookie

        if (!refreshToken) {
            console.error('No refresh token found');
            return;
        }

        fetch('http://localhost:8000/api/users/refresh/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                refresh: refreshToken // Pass the refresh token correctly
            }),
            credentials: 'same-origin', // Send cookies along with the request
        })
            .then(response => response.json())
            .then(data => {
                if (data.access) {
                    document.cookie = `access_token=${data.access}; path=/; secure; sameSite=Strict`;
                    sendPostRequest(); // Retry the original request
                } else {
                    console.error('Failed to refresh token:', data);
                }
            })
            .catch(error => console.error('Error refreshing token:', error));
    }

    function sendPostRequest() {
        const selectedThemeID = document.getElementById('theme-selector').value;
        const accessToken = getCookie('access_token');

        if (!accessToken) {
            refreshAccessToken(); // Attempt to refresh the token
            return;
        }

        fetch('http://localhost:8000/api/users/profile/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`, // Use access token here
            },
            body: JSON.stringify({
                theme_id: selectedThemeID
            })
        })
            .then(response => {
                if (response.status === 401) {
                    refreshAccessToken(); // Token may have expired, refresh it
                } else {
                    return response.json();
                }
            })
            .then(data => {
                window.location.reload(); // Reload the page after successful update
            })
            .catch(error => console.error('Error:', error));
    }


    document.getElementById('theme-selector').addEventListener('change', function (event) {
        const selectedThemeID = event.target.value;

        fetch(`http://localhost:8000/api/themes/${selectedThemeID}`)
            .then(response => response.json())
            .then(data => {
                const themeCSS = data.css;

                // Match and extract brand color from CSS
                const match = themeCSS.match(/--brand-color:\s*(#[0-9a-fA-F]{6})/);
                const brandColor = match ? match[1].slice(1) : null;

                // Set cookies
                document.cookie = `theme=${selectedThemeID}; path=/;`;
                document.cookie = `brand-color=${brandColor}; path=/;`;

                // Optionally update selector value (redundant unless doing something special)
                document.getElementById('theme-selector').value = selectedThemeID;

                // Trigger post request
                sendPostRequest();
            })
            .catch(error => {
                console.error('Error fetching themes:', error);
            });
    });
});

document.addEventListener('DOMContentLoaded', () => {
    const menuButton = document.getElementById('menu-toggle');
    const navMenu = document.getElementById('nav-menu');

    menuButton.addEventListener('click', () => {
        navMenu.classList.toggle('active');
    });
});