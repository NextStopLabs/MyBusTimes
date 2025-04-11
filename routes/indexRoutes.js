const express = require('express');
const path = require('path');
const fs = require('fs').promises;
const axios = require('axios');
const router = express.Router();

router.get('/', async (req, res) => {
    try {
        const data = await fs.readFile(path.join(__dirname, '..', 'public', 'json', 'mod.json'), 'utf8');

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

router.get('/status', async (req, res) => {
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

module.exports = router;