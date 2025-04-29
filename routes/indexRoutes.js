/**
    * @description      : 
    * @author           : Kai
    * @group            : 
    * @created          : 20/04/2025 - 21:48:24
    * 
    * MODIFICATION LOG
    * - Version         : 1.0.0
    * - Date            : 20/04/2025
    * - Author          : Kai
    * - Modification    : 
**/
const express = require('express');
const path = require('path');
const fs = require('fs').promises;
const axios = require('axios');
const router = express.Router();

router.get('/', async (req, res) => {
    try {
        const modData = await axios.get('http://localhost:8000/media/json/mod.json');
        const operators = await axios.get('http://localhost:8000/api/operators/');
        const regions = await axios.get('http://localhost:8000/api/regions/');
        const groups = await axios.get('http://localhost:8000/api/groups/');
        const messages = modData.data.messages;
        const randomMessage = messages[Math.floor(Math.random() * messages.length)];
        const breadcrumbs = [{ name: 'Home', url: '/' }];

        res.render('index', {
            title: 'Home',
            message: randomMessage,
            breadcrumbs,
            groups: groups.data,
            regions: regions.data,
            operators: operators.data,
            style: 'narrow'
        });
    } catch (error) {
        console.error('Error:', error);

        const breadcrumbs = [{ name: 'Home', url: '/' }];
        res.status(500).render('error/500', { title: '500 Internal Server Error', breadcrumbs });
    }
});

router.get('/rules', async (req, res) => {
    try {
        const breadcrumbs = [{ name: 'Home', url: '/' }];

        res.render('terms', {
            title: 'Rules',
            breadcrumbs,
            style: 'narrow'
        });
    } catch (error) {
        console.error('Error:', error);

        const breadcrumbs = [{ name: 'Rules', url: '/' }];
        res.status(500).render('error/500', { title: '500 Internal Server Error', breadcrumbs });
    }
});

router.get('/status', async (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    try {
        const response = await axios.get('http://localhost:8000/api/feature-toggles/');
        const featureToggles = response.data;

        res.render('feature-toggle-status', { 
            title: 'Feature Status', 
            breadcrumbs, 
            featureToggles,
            style: 'wide'
        });
    } catch (error) {
        console.error('Error fetching feature toggles:', error);
        res.render('feature-toggle-status', { 
            title: 'Feature Status', 
            featureToggles: {}, 
            breadcrumbs,
            style: 'wide'
        });
    }
});

router.get('/service-updates', async (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    try {
        const response = await axios.get('http://localhost:8000/api/service-updates/?live=true&order_by=-updated_at');
        let serviceUpdates = response.data;

        // Format each update's date
        serviceUpdates.forEach(update => {
            const date = new Date(update.updated_at);
            update.formattedDate = date.toLocaleDateString('en-GB', {
                hour: '2-digit',
                minute: '2-digit',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        });

        // Render the page with service updates
        res.render('service-updates', { 
            title: 'Service Updates', 
            breadcrumbs, 
            serviceUpdates,
            style: 'narrow'
        });
    } catch (error) {
        console.error('Error fetching service updates:', error);
        
        // If there's an error, render with an empty array for serviceUpdates
        res.render('service-updates', { 
            title: 'Service Updates', 
            breadcrumbs, 
            serviceUpdates: [], // Pass an empty array here
            style: 'narrow'
        });
    }
});



router.get('/search', async (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];

    const searchQuery = req.query.q;

    if (!searchQuery) {
        return res.render('search', { 
            users: [], 
            operators_name: [],
            operators_code: [],
            games: [],
            routes: [],
            query: '', 
            error: null, 
            title: searchQuery, 
            breadcrumbs,
            style: 'wide'
        });
    }

    try {
        const user_response = await axios.get(`http://localhost:8000/api/users/search/?username__icontains=${searchQuery}`);
        const operator_code_response = await axios.get(`http://localhost:8000/api/operators/?operator_code__icontains=${searchQuery}`);
        const operator_name_response = await axios.get(`http://localhost:8000/api/operators/?operator_name__icontains=${searchQuery}`);
        const game_name_response = await axios.get(`http://localhost:8000/api/game/?game_name__icontains=${searchQuery}`);
        const routes_response = await Promise.all([
            axios.get(`http://localhost:8000/api/routes/?route_num__icontains=${searchQuery}`),
            axios.get(`http://localhost:8000/api/routes/?route_num__icontains=${searchQuery}&inboud_destination__icontains=${searchQuery}`),
            axios.get(`http://localhost:8000/api/routes/?route_num__icontains=${searchQuery}&outboud_destination__icontains=${searchQuery}`)
        ]);
        const routes = [...routes_response[0].data, ...routes_response[1].data, ...routes_response[2].data].filter((route, index, self) =>
            index === self.findIndex((r) => r.id === route.id)
        );

        console.log(routes);
        
        res.render('search', { 
            users: user_response.data, 
            operators_name: operator_name_response.data, 
            operators_code: operator_code_response.data, 
            games: game_name_response.data, 
            routes: routes,
            query: searchQuery, 
            error: null, 
            title: searchQuery, 
            breadcrumbs,
            style: 'wide'
        });
    } catch (error) {
        console.error('Error fetching data from API:', error);
        res.render('search', { 
            users: [],
            operators_name: [],
            operators_code: [],
            games: [],
            routes: [],
            query: searchQuery, 
            error: 'Failed to fetch data', 
            title: searchQuery, 
            breadcrumbs,
            style: 'wide'
        });
    }
});

module.exports = router;