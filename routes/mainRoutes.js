const express = require('express');
const fs = require('fs').promises;
const path = require('path');
const axios = require('axios');
const router = express.Router();

router.get('/', async (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    try {
        const data = await fs.readFile(path.join(__dirname, '..', 'public', 'json', 'mod.json'), 'utf8');
        const messages = JSON.parse(data).messages;
        const randomMessage = messages[Math.floor(Math.random() * messages.length)];

        const operators = await axios.get('http://localhost:8000/api/operators/');
        const regions = await axios.get('http://localhost:8000/api/regions/');
        const groups = await axios.get('http://localhost:8000/api/groups/');

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
        res.status(500).render('error/500', { title: '500 Internal Server Error', breadcrumbs });
    }
});

router.get('/feature-toggles/status', async (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    try {
        const response = await axios.get('http://localhost:8000/api/feature-toggles/');
        const featureToggles = response.data;

        res.render('feature-toggle-status', { title: 'Feature Status', breadcrumbs, featureToggles });
    } catch (error) {
        console.error('Error fetching feature toggles:', error);
        res.render('feature-toggle-status', { title: 'Feature Status', featureToggles: {}, breadcrumbs });
    }
});

router.get('/search', async (req, res) => {
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

router.get('/login', (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    res.render('login', { title: 'Login', breadcrumbs });
});

router.get('/register', (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    res.render('register', { error: null, title: 'Register', breadcrumbs });
});

router.post('/register', async (req, res) => {
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

module.exports = router;