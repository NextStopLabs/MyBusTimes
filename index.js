const express = require('express');
const path = require('path');
const fs = require('fs').promises;
const axios = require('axios');
const ejsLayouts = require('express-ejs-layouts');
const cookieParser = require('cookie-parser');
const cookie = require('cookie');

const app = express();
const Fleet_API_URL = "http://localhost:8000/api/fleet";

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

app.use(ejsLayouts);

app.use(express.urlencoded({ extended: true }));
app.use(cookieParser());

app.use(express.static(path.join(__dirname, 'public')));

app.use((req, res, next) => {
    res.locals.brandColor = req.cookies['brand-color'] || '8cb9d5';
    next();
});

app.get('/', async (req, res) => {
    try {
        // Using fs.promises.readFile to read the file asynchronously
        const data = await fs.readFile(path.join(__dirname, 'public', 'json', 'mod.json'), 'utf8');

        const operators = await axios.get('http://localhost:8000/api/operators/');
        const regions = await axios.get('http://localhost:8000/api/regions/');
        const groups = await axios.get('http://localhost:8000/api/groups/');

        const messages = JSON.parse(data).messages;
        const randomMessage = messages[Math.floor(Math.random() * messages.length)];

        const breadcrumbs = [{ name: 'Home', url: '/' }];

        res.render('index', { 
            title: 'Home', 
            message: randomMessage, 
            breadcrumbs, 
            groups: groups.data, 
            regions: regions.data, 
            operators: operators.data 
        });
    } catch (error) {
        console.error('Error:', error);

        const breadcrumbs = [{ name: 'Home', url: '/' }];
        res.status(500).render('error/500', { title: '500 Internal Server Error', breadcrumbs });
    }
});

app.get('/search', async (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];

    const searchQuery = req.query.q;

    if (!searchQuery) {
        return res.render('search', { users: [], query: '', error: null, title: searchQuery, breadcrumbs });
    }

    try {
        const user_response = await axios.get(`http://localhost:8000/api/users/search/?username__icontains=${searchQuery}`);
        const operator_code_response = await axios.get(`http://localhost:8000/api/operators/?operator_name__icontains=&operator_code__icontains=${searchQuery}`);
        const operator_name_response = await axios.get(`http://localhost:8000/api/operators/?operator_name__icontains=&operator_name__icontains=${searchQuery}`);

        res.render('search', { users: user_response.data, operators_name: operator_name_response.data, operators_code: operator_code_response.data, query: searchQuery, error: null, title: searchQuery, breadcrumbs });
    } catch (error) {
        console.error('Error fetching data from API:', error);
        res.render('search', { users: [], query: searchQuery, error: 'Failed to fetch data', title: searchQuery, breadcrumbs });
    }
});

app.get('/login', (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    res.render('login', { title: 'Login', breadcrumbs });
});

app.get('/register', (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    res.render('register', { error: null, title: 'Register', breadcrumbs });
});

app.post('/register', async (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    const { username, email, firstName, lastName, password } = req.body;

    const userData = {
        username,
        email,
        first_name: firstName,
        last_name: lastName,
        password
    };

    try {
        const response = await fetch('http://localhost:8000/api/users/register/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(userData),
        });

        const result = await response.json();

        if (result.success) {
            res.redirect('/login');
        } else {
            res.render('register', { error: result.message, title: 'Register', breadcrumbs });
        }
    } catch (error) {
        res.render('register', { error: 'An error occurred, please try again.', title: 'Register', breadcrumbs });
    }
});

app.get('/u/:username', async (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    const username = req.params.username;

    try {
        const user_response = await axios.get(`http://localhost:8000/api/users/search/${username}/`);
        const userData = user_response.data;

        if (!userData.badges || !Array.isArray(userData.badges)) {
            return res.status(404).send('Badges not found for the user');
        }

        if (userData.badges.length > 0) {
            const badgePromises = userData.badges.map(async (badgeId) => {
                try {
                    const badgeResponse = await axios.get(`http://localhost:8000/api/badges/${badgeId}`);
                    return badgeResponse.data;
                } catch (error) {
                    console.error(`Error fetching badge with ID ${badgeId}:`, error.message);
                    return null;
                }
            });

            const badgeResponses = await Promise.all(badgePromises);
            const badges = badgeResponses.filter(response => response !== null);

            if (badges.length > 0) {
                const extendedUserData = { ...userData, badges };

                res.render('dashboard', {
                    title: `${username}`,
                    user: `${username}`,
                    userData: extendedUserData,
                    breadcrumbs
                });
            } else {
                console.error('No valid badge data received');
                res.status(404).send('No valid badge data received');
            }
        } else {
            res.render('dashboard', {
                title: `${username}`,
                user: `${username}`,
                userData,
                breadcrumbs
            });
        }
    } catch (error) {
        console.error('Error fetching user data:', error.response?.data || error.message);
        res.status(404).send('User not found');
    }
});

app.get('/game/', async (req, res) => {
    res.redirect("/operator/");
});

app.get('/game/:game', async (req, res) => {
    try {
        const breadcrumbs = [{ name: 'Home', url: '/' }];
        const game = req.params.game;

        const response = await axios.get(`http://localhost:8000/api/operators/?game=${game}`);
        const operatorData = response.data;
        res.render('game', { title: 'Game', game, operatorData, breadcrumbs });
    } catch (error) {
        console.error('Error fetching operator data:', error.response?.data || error.message);
        res.status(404).send('Game not found');
    }
});

app.get('/operator/', async (req, res) => {
    try {
        const breadcrumbs = [{ name: 'Home', url: '/' }];

        const response = await axios.get(`http://localhost:8000/api/operators/`);
        const operatorData = response.data;
        res.render('operator', { title: 'Operators', operatorData, breadcrumbs });
    } catch (error) {
        console.error('Error fetching operator data:', error.response?.data || error.message);
        res.status(404).send('Operators not found');
    }
});

app.get('/operator/:name', async (req, res) => {
    try {
        const operatorName = req.params.name;
        const breadcrumbs = [{ name: 'Home', url: '/' }];

        const operatorResponse = await axios.get(`http://localhost:8000/api/operators/${operatorName}`);
        const operatorData = operatorResponse.data;

        const regionsResponse = await axios.get(`http://localhost:8000/api/regions/`);
        const regionsData = regionsResponse.data;

        const route_response = await axios.get(`http://localhost:8000/api/routes/?route_operator=${operatorData.id}`);
        const routeData = route_response.data;

        const regionNames = operatorData.region.map(regionId => {
            const region = regionsData.find(r => r.id === regionId);
            return region ? { name: region.region_name, code: region.region_code, in_the: region.in_the } : null;
        }).filter(region => region);
        const regionBreadcrumb = regionNames.map(region => region.name).join(' / ');
        if (regionBreadcrumb) {
            regionNames.forEach((region, index) => {
                breadcrumbs.push({
                    name: region.name,
                    inThe: region.in_the,
                    url: `/region/${region.code}`,
                    className: index === regionNames.length - 1 ? 'default' : 'region'
                });
            });
        }

        breadcrumbs.push({ name: operatorName, url: `/operator/${encodeURIComponent(operatorName)}` });
        res.render('operators', { title: `${operatorName}`, operatorData, routeData, breadcrumbs, regionNames });
    } catch (error) {
        console.error('Error fetching operator data:', error.response?.data || error.message);
        res.status(404).send('Operator not found');
    }
});

app.post('/login', async (req, res) => {
    const { username, password } = req.body;

    try {
        const response = await axios.post('http://localhost:8000/api/users/login/', {
            username,
            password
        });
        const { refresh } = response.data;
        const refreshTokenCookie = cookie.serialize('refresh_token', refresh, { httpOnly: false, secure: process.env.NODE_ENV === 'production', sameSite: 'Strict', maxAge: 60 * 60 * 24 * 365, path: '/', });
        fetch(`http://localhost:8000/api/users/search/${username}/`)
            .then(response => response.json())
            .then(data => {
                const serializedCookies = cookie.serialize('username', data.username, { httpOnly: false, path: '/' });
                const themeCookie = cookie.serialize('theme', data.theme, { httpOnly: false, path: '/' });
                res.setHeader('Set-Cookie', [serializedCookies, themeCookie, refreshTokenCookie]);
                res.redirect(`/u/${data.username}`);
            })
            .catch(error => {
                console.error('Error fetching user data:', error);
                res.send('Error fetching user data.');
            });
    } catch (error) {
        console.error('Login failed:', error.response?.data || error.message);
        res.send('Login failed. Invalid credentials.');
    }
});

app.get("/fleet/edit/:id", async (req, res) => {
    try {
        const response = await fetch(`${Fleet_API_URL}/${req.params.id}`);
        if (!response.ok) {
            console.error(`API response: ${response.statusText}`);
            throw new Error("Fleet not found");
        }
        const fleet = await response.json();
        res.render("edit-fleet", { fleet, title: 'Edit' });
    } catch (error) {
        console.error(error.message);
        res.status(500).send("Fleet not found or server error");
    }
});

app.post("/fleet/edit/:id", async (req, res) => {
    try {
        const { fleet_number, operator_code, reg, depot, branding } = req.body;

        const response = await fetch(`${Fleet_API_URL}/${req.params.id}`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                fleet_number,
                operator_code,
                reg,
                depot,
                branding,
            }),
        });

        if (!response.ok) {
            console.error(`API response: ${response.statusText}`);
            throw new Error("Failed to update fleet data");
        }

        res.redirect("/fleet/list");
    } catch (error) {
        console.error(error.message);
        res.status(500).send("Failed to update fleet data");
    }
});

app.use((req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    res.status(404).render('error/404', { title: '404 Page Not Found', breadcrumbs });
});

const port = 3000;
app.listen(port, () => {
    console.log(`Server running on http://localhost:${port}`);
});
