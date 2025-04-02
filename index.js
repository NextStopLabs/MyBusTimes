const express = require('express');
const path = require('path');
const fs = require('fs')
const axios = require('axios');
const ejsLayouts = require('express-ejs-layouts');
const cookieParser = require('cookie-parser');

const app = express();

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
        
        // Render the page after the random message is selected
        res.render('index', { title: 'Home', message: randomMessage });
    });
});

// Handle the search route
app.get('/search', async (req, res) => {
    const searchQuery = req.query.q; // Get the 'q' parameter from the URL

    if (!searchQuery) {
        return res.render('search', { users: [], query: '', error: null }); // Add error: null
    }

    try {
        // Make a request to the external API to search for users
        const response = await axios.get(`https://new.mybustimes.cc/api/users/search/?username__icontains=${searchQuery}`);
        
        // Render the search results to the search.ejs view
        res.render('search', { users: response.data, query: searchQuery, error: null, title: searchQuery  });
    } catch (error) {
        console.error('Error fetching data from API:', error);
        res.render('search', { users: [], query: searchQuery, error: 'Failed to fetch data', title: searchQuery });
    }
});


// Login page route
app.get('/login', (req, res) => {
    res.render('login', { title: 'Login' });
});

// Route to display the registration form
app.get('/register', (req, res) => {
    res.render('register', { error: null, title: 'Register' });
});

// Route to handle the registration form submission
app.post('/register', async (req, res) => {
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
        const response = await fetch('https://new.mybustimes.cc/api/users/register/', {
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
            res.render('register', { error: result.message, title: 'Register' }); // Show error if registration fails
        }
    } catch (error) {
        res.render('register', { error: 'An error occurred, please try again.', title: 'Register' });
    }
});

// User profile route based on the username
app.get('/u/:username', async (req, res) => {
    const username = req.params.username; // Get username from URL

    try {
        // Fetch public user data from the API (No Auth Required)
        const response = await axios.get(`http://localhost:8000/api/users/public/${username}/`);

        // Extract user data from response
        const userData = response.data;

        res.render('dashboard', { title: `${username}`, user: `${username}`, userData });
    } catch (error) {
        console.error('Error fetching user data:', error.response?.data || error.message);
        res.status(404).send('User not found');
    }
});

// Handle the login form submission
app.post('/login', async (req, res) => {
    const { username, password } = req.body;

    try {
        // Send login request to Django API using Axios
        const response = await axios.post('http://localhost:8000/api/users/login/', {
            username,
            password
        });

        // Extract access and refresh tokens
        const { access, refresh } = response.data;

        // Store tokens in cookies
        res.cookie('access_token', access, { httpOnly: true });
        res.cookie('refresh_token', refresh, { httpOnly: true });

        // Fetch user data using the access token
        const userResponse = await axios.get(`http://localhost:8000/api/users/public/${username}/`);

        // Store the username in a cookie
        res.cookie('username', userResponse.data.username, { httpOnly: false });
        res.cookie('theme', userResponse.data.theme_id, { httpOnly: false });

        // Redirect to the user's profile
        res.redirect(`/u/${userResponse.data.username}`);
    } catch (error) {
        console.error('Login failed:', error.response?.data || error.message);
        res.send('Login failed. Invalid credentials.');
    }
});

// Start the server
const port = 3000;
app.listen(port, () => {
    console.log(`Server running on http://localhost:${port}`);
});
