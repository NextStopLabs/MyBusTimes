const express = require('express');
const path = require('path');
const fs = require('fs').promises;
const axios = require('axios');
const ejsLayouts = require('express-ejs-layouts');
const cookieParser = require('cookie-parser');
const cookie = require('cookie');

const app = express();

const indexRoutes = require('./routes/indexRoutes');
const accountRoutes = require('./routes/accountRoutes');
const gameRoutes = require('./routes/gameRoutes');
const operatorRoutes = require('./routes/operatorRoutes');
const regionRoutes = require('./routes/regionRoutes');
const userRoutes = require('./routes/userRoutes');
const mapRoutes = require('./routes/mapRoutes');
const historyRoutes = require('./routes/historyRoutes');
const routeMaperRoutes = require('./routes/routeMaperRoutes');

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

app.use(ejsLayouts);
app.use('/bustimesApi', require('./routes/apiProxy'));

app.use(express.urlencoded({ extended: true }));
app.use(cookieParser());

app.use(express.static(path.join(__dirname, 'public')));

app.use((req, res, next) => {
    res.locals.brandColor = req.cookies['brand-color'] || '8cb9d5';
    next();
});

app.use(async (req, res, next) => {
    try {
        const response = await axios.get('http://localhost:8000/api/feature-toggles/');
        const featureToggles = response.data;
        res.locals.featureToggles = featureToggles;
    } catch (error) {
        console.error('Error fetching feature toggles:', error);
        res.locals.featureToggles = {};
    }
    next();
});

app.use('/', indexRoutes);
app.use('/account', accountRoutes);
app.use('/game', gameRoutes);
app.use('/operator', operatorRoutes);
app.use('/region', regionRoutes);
app.use('/u', userRoutes);
app.use('/map', mapRoutes);
app.use('/history', historyRoutes);
app.use('/routeMaper', routeMaperRoutes);

app.use((req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    res.status(404).render('error/404', { 
        title: '404 Page Not Found', 
        breadcrumbs,
        style: 'narrow'
    });
});

const port = 3000;
app.listen(port, () => {
    console.log(`Server running on http://localhost:${port}`);
});
