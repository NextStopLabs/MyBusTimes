const express = require('express');
const router = express.Router();
const axios = require('axios');

router.get('/', async (req, res) => {
    res.redirect("/operator/");
});

router.get('/:game', async (req, res) => {
    try {
        const game = req.params.game;
        let showGameRoutes = false; // Use let instead of const
        const breadcrumbs = [
            { name: 'Home', url: '/' },
            { name: game, url: `/game/${game}`, className: 'default' }
        ];

        try {
            await axios.get(`http://localhost:8000/api/game/${game}/`);
            showGameRoutes = true;
        } catch (error) {
            showGameRoutes = false;
        }

        const operatorResponse = await axios.get(`http://localhost:8000/api/operators/?game=${game}`);
        const operatorData = operatorResponse.data;

        res.render('game/game', {
            title: 'Game',
            game,
            operatorData,
            breadcrumbs,
            showGameRoutes,
            style: 'wide'
        });

    } catch (error) {
        console.error('Error fetching operator data:', error.response?.data || error.message);
        res.status(404).send('Game not found');
    }
});



router.get('/:game/route/:route', (req, res) => {
    const game = req.params.game;
    const routeNum = req.params.route;

    // Define the API URL that fetches the JSON data
    const apiUrl = `http://localhost:8000/api/game/${game}/`;

    const breadcrumbs = [
        { name: 'Home', url: '/' },
        { name: game, url: `/game/${game}`, className: 'default' },
        { name: 'Routes', url: `/map/${game}/routes`, className: 'default' }
    ];

    // Add the route to the breadcrumbs
    breadcrumbs.push({ name: `${routeNum}`, url: `/game/${game}/route/${routeNum}`, className: 'active' });

    // Fetch the route data from the Django API
    axios.get(apiUrl)
        .then((response) => {
            const routesData = response.data;

            // Find the route with the matching "Route Num"
            const route = routesData.find(r => r['Route Num'] === routeNum);

            if (!route) {
                return res.status(404).send('Route not found');
            }

            // Render the route details page with the data
            res.render('game/gameRoute', {
                title: `Route ${routeNum} Details`,
                game,
                routeNum,
                route,
                breadcrumbs,
                style: 'wide'
            });
        })
        .catch((error) => {
            console.error('Error fetching data from API:', error);
            res.status(500).send('Error fetching data from API');
        });
});



module.exports = router;