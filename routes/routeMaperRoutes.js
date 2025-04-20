const express = require('express');
const axios = require('axios');
const router = express.Router();

router.get('/:name', async (req, res) => {
    try {
        const operatorName = req.params.name;
        const breadcrumbs = [{ name: 'Home', url: '/' }];

        breadcrumbs.push({ name: operatorName, url: `/operator/${encodeURIComponent(operatorName)}` });

        const username = req.cookies.username;
        if (!username) {
            return res.status(400).send('Username cookie not found');
        }

        const userResponse = await axios.get(`http://localhost:8000/api/users/search/?username=${username}`);
        const userData = userResponse.data;

        const operatorResponse = await axios.get(`http://localhost:8000/api/operators/?owner=${userData[0].id}`);
        const operatorData = operatorResponse.data;

        res.render('routeMaper/maper', {
            title: 'Route Maker',
            operatorData,
            breadcrumbs,
            style: 'wide',
            bustimesStopsApiUrl: 'https://bustimes.org/api/stops/'
        });
    } catch (error) {
        console.error('Error fetching operator data:', error.response?.data || error.message);
        res.status(404).send('Operators not found');
    }
});

module.exports = router;