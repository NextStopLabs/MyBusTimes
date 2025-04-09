document.addEventListener('DOMContentLoaded', () => {
    let username = document.cookie.split('; ').find(row => row.startsWith('username='))?.split('=')[1];

    if (username) {
        document.getElementById("login-profile").textContent = 'My Profile';
        document.getElementById("login-profile").href = '/u/' + username;
    } else {
        document.getElementById("login-profile").textContent = 'Login';
        document.getElementById("login-profile").href = '/login';
    }

    let themeCSS = document.cookie.split('; ').find(row => row.startsWith('theme='))?.split('=')[1];
    let themeID = document.cookie.split('; ').find(row => row.startsWith('themeID='))?.split('=')[1];
    let themeDark = document.cookie.split('; ').find(row => row.startsWith('themeDark='))?.split('=')[1];

    if (!themeID) {
        themeCSS = 'Light.CSS';
        themeID = 1;
        themeDark = 'false';
    }

    applyTheme(themeID);

    function applyTheme(themeID) {
        if (themeDark === 'false') {
            document.getElementById('logo').src = '/src/icons/MBT-Logo-Black.png';
            document.getElementById('menu').src = '/src/icons/Burger-Menu-Black.png';
        } else {
            document.getElementById('logo').src = '/src/icons/MBT-Logo-White.png';
            document.getElementById('menu').src = '/src/icons/Burger-Menu-White.png';
        }
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
            window.location.reload();
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

                // Set cookies
                document.cookie = `theme=${data.css}; path=/;`;
                document.cookie = `themeDark=${data.dark_theme}; path=/;`;
                document.cookie = `themeID=${data.id}; path=/;`;
                document.cookie = `brand-color=${data.main_colour}; path=/;`;

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

    (function (w, d, s, l, i) {
        w[l] = w[l] || [];
        w[l].push({
            'gtm.start': new Date().getTime(),
            event: 'gtm.js'
        });
        var f = d.getElementsByTagName(s)[0],
            j = d.createElement(s),
            dl = l != 'dataLayer' ? '&l=' + l : '';
        j.async = true;
        j.src = 'https://www.googletagmanager.com/gtm.js?id=' + i + dl;
        f.parentNode.insertBefore(j, f);
    })(window, document, 'script', 'dataLayer', 'GTM-PN8ZVKWT');
});