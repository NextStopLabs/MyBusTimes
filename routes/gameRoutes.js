const express = require('express');
const axios = require('axios');
const router = express.Router();

router.get('/', async (req, res) => {
    res.redirect("/operator/");
});

router.get('/:game', async (req, res) => {
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

module.exports = router;