const express = require('express');
const cookieParser = require('cookie-parser');

const router = express.Router();

const breadcrumbs = [{ name: 'Home', url: '/' }];
const title = 'Under Development'

router.get('/', async (req, res) => {
    res.status(700).render('error/700', {
        error: 'Under Development',
        breadcrumbs,
        title,
        style: 'narrow'
    });
});

router.get('/operator/:name', async (req, res) => {
    res.status(700).render('error/700', {
        error: 'Under Development',
        operatorName: req.params.name,
        breadcrumbs,
        title,
        style: 'narrow'
    });
});

router.get('/vehicle/:id', async (req, res) => {
    res.status(700).render('error/700', {
        error: 'Under Development',
        vehicleId: req.params.id,
        breadcrumbs,
        title,
        style: 'narrow'
    });
});

router.get('/user/:username_id', async (req, res) => {
    res.status(700).render('error/700', {
        error: 'Under Development',
        usernameId: req.params.username_id,
        breadcrumbs,
        title,
        style: 'narrow'
    });
});

module.exports = router;