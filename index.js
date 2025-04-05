const express = require('express');
const path = require('path');
const fs = require('fs')
const axios = require('axios');
const ejsLayouts = require('express-ejs-layouts');
const cookieParser = require('cookie-parser');
const cookie = require('cookie');

const app = express();
const Fleet_API_URL = "http://localhost:8000/api/fleet";

// Set up EJS as the templating engine
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Use express-ejs-layouts for layout handling
app.use(ejsLayouts);

// Middleware to parse form data and cookies
app.use(express.urlencoded({ extended: true }));
app.use(cookieParser());

// Serve static files (CSS, JS)
app.use(express.static(path.join(__dirname, 'public')));

// Home page route
app.get('/', (req, res) => {
    fs.readFile(path.join(__dirname, 'public', 'json', 'mod.json'), 'utf8', (err, data) => {
        if (err) {
            return res.status(500).send('Error reading JSON file');
        }
        const messages = JSON.parse(data).messages;
        const randomMessage = messages[Math.floor(Math.random() * messages.length)];

        const breadcrumbs = [{ name: 'Home', url: '/' }];

        // Render the page after the random message is selected
        res.render('index', { title: 'Home', message: randomMessage, breadcrumbs });
    });
});

// Handle the search route
app.get('/search', async (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];

    const searchQuery = req.query.q; // Get the 'q' parameter from the URL

    if (!searchQuery) {
        return res.render('search', { users: [], query: '', error: null, title: searchQuery, breadcrumbs }); // Add error: null
    }

    try {
        // Make a request to the external API to search for users
        const user_response = await axios.get(`http://localhost:8000/api/users/search/?username__icontains=${searchQuery}`);
        const operator_code_response = await axios.get(`http://localhost:8000/api/operators/?operator_name__icontains=&operator_code__icontains=${searchQuery}`);
        const operator_name_response = await axios.get(`http://localhost:8000/api/operators/?operator_name__icontains=&operator_name__icontains=${searchQuery}`);

        // Render the search results to the search.ejs view
        res.render('search', { users: user_response.data, operators_name: operator_name_response.data, operators_code: operator_code_response.data, query: searchQuery, error: null, title: searchQuery, breadcrumbs });
    } catch (error) {
        console.error('Error fetching data from API:', error);
        res.render('search', { users: [], query: searchQuery, error: 'Failed to fetch data', title: searchQuery, breadcrumbs });
    }
});


// Login page route
app.get('/login', (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    res.render('login', { title: 'Login', breadcrumbs });
});

// Route to display the registration form
app.get('/register', (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    res.render('register', { error: null, title: 'Register', breadcrumbs });
});

// Route to handle the registration form submission
app.post('/register', async (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    const { username, email, firstName, lastName, password } = req.body;

    // Construct the data for the API request
    const userData = {
        username,
        email,
        first_name: firstName,
        last_name: lastName,
        password
    };

    try {
        // Send POST request to the API
        const response = await fetch('http://localhost:8000/api/users/register/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(userData),
        });

        const result = await response.json();

        // Handle API response (for example, success or error)
        if (result.success) {
            res.redirect('/login'); // Redirect to login on success
        } else {
            res.render('register', { error: result.message, title: 'Register', breadcrumbs }); // Show error if registration fails
        }
    } catch (error) {
        res.render('register', { error: 'An error occurred, please try again.', title: 'Register', breadcrumbs });
    }
});

// User profile route based on the username
app.get('/u/:username', async (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    const username = req.params.username;

    try {

        const response = await axios.get(`http://localhost:8000/api/users/search/${username}/`);


        const userData = response.data;

        res.render('dashboard', { title: `${username}`, user: `${username}`, userData, breadcrumbs });
    } catch (error) {
        console.error('Error fetching user data:', error.response?.data || error.message);
        res.status(404).send('User not found');
    }
});

// Route for displaying all operators
app.get('/game/', async (req, res) => {
    res.redirect("/operator/");
});

// Route for displaying all operators in a game
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

// Route for displaying all operators
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
        const operatorName = req.params.name; // Get the operator name from the URL parameter
        const breadcrumbs = [{ name: 'Home', url: '/' }];

        // Fetch data for the specific operator
        const operatorResponse = await axios.get(`http://localhost:8000/api/operators/${operatorName}`);
        const operatorData = operatorResponse.data;

        const regionsResponse = await axios.get(`http://localhost:8000/api/regions/`);
        const regionsData = regionsResponse.data;

        const route_response = await axios.get(`http://localhost:8000/api/routes/?route_operator=${operatorData.id}`);
        const routeData = route_response.data;

        // Get the region names corresponding to the region IDs in operatorData.region
        const regionNames = operatorData.region.map(regionId => {
            const region = regionsData.find(r => r.id === regionId);
            return region ? { name: region.region_name, code: region.region_code, in_the: region.in_the } : null;  // Add region name and code or null if not found
        }).filter(region => region);  // Remove null values if any region ID does not match

        // Join region names with a slash (e.g., "East Mids / West Mids")
        const regionBreadcrumb = regionNames.map(region => region.name).join(' / ');

        // Add operator name and region to breadcrumbs
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

        // Render the operator page with operator data and breadcrumbs
        res.render('operators', { title: `${operatorName}`, operatorData, routeData, breadcrumbs, regionNames });
    } catch (error) {
        console.error('Error fetching operator data:', error.response?.data || error.message);
        res.status(404).send('Operator not found');
    }
});


app.post('/login', async (req, res) => {
    const { username, password } = req.body;

    try {
        // Send login request to Django API using Axios
        const response = await axios.post('http://localhost:8000/api/users/login/', {
            username,
            password
        });

        // Extract access and refresh tokens
        const { refresh } = response.data;

        // Store tokens in cookies
        const refreshTokenCookie = cookie.serialize('refresh_token', refresh, { httpOnly: false, secure: process.env.NODE_ENV === 'production', sameSite: 'Strict', maxAge: 60 * 60 * 24 * 365, path: '/',});

        console.log('Set-Cookie:', refreshTokenCookie);

        // Fetch user data using the access token
        fetch(`http://localhost:8000/api/users/search/${username}/`)
            .then(response => response.json())
            .then(data => {
                // Store the username in a cookie
                const serializedCookies = cookie.serialize('username', data.username, { httpOnly: false, path: '/' });
                const themeCookie = cookie.serialize('theme', data.theme, { httpOnly: false, path: '/' });

                // Set cookies in the response headers
                res.setHeader('Set-Cookie', [serializedCookies, themeCookie, refreshTokenCookie]);

                console.log('Set-Cookie:', serializedCookies);
                console.log('Set-Cookie:', themeCookie);

                console.log(data.theme);
                console.log(data.username);

                // Now redirect after the cookies have been set
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

// Edit Fleet Page
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
        console.error(error.message);  // Log the error message
        res.status(500).send("Fleet not found or server error");
    }
});

// Handle Edit Submission - Send Updated Data to API
app.post("/fleet/edit/:id", async (req, res) => {
    try {
        const { fleet_number, operator_code, reg, depot, branding } = req.body;

        const response = await fetch(`${Fleet_API_URL}/${req.params.id}`, {
            method: "PUT", // Use PUT to update data
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

        res.redirect("/fleet/list"); // Redirect after update
    } catch (error) {
        console.error(error.message);  // Log the error message
        res.status(500).send("Failed to update fleet data");
    }
});

// Start the server
const port = 3000;
app.listen(port, () => {
    console.log(`Server running on http://localhost:${port}`);
});
