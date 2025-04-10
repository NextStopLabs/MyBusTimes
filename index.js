const express = require('express');
const path = require('path');
const fs = require('fs').promises;
const axios = require('axios');
const ejsLayouts = require('express-ejs-layouts');
const cookieParser = require('cookie-parser');
const cookie = require('cookie');
const userRoutes = require('./routes/userRoutes');
const fleetRoutes = require('./routes/fleetRoutes');
const operatorRoutes = require('./routes/operatorRoutes');
const regionRoutes = require('./routes/regionRoutes');
const mainRoutes = require('./routes/mainRoutes');
const gameRoutes = require('./routes/gameRoutes');
const featureTogglesMiddleware = require('./middleware/featureToggles');
const app = express();

const Fleet_API_URL = "http://localhost:8000/api/fleet";

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

app.use(ejsLayouts);
app.use(express.urlencoded({ extended: true }));
app.use(cookieParser());
app.use(express.static(path.join(__dirname, 'public')));

// Middlewares
app.use((req, res, next) => {
    res.locals.brandColor = req.cookies['brand-color'] || '8cb9d5';
    next();
});

app.use(featureTogglesMiddleware);

// Routes
app.use('/', mainRoutes);
app.use('/game', gameRoutes);
app.use('/u', userRoutes);
app.use('/vehicles', fleetRoutes);
app.use('/operator', operatorRoutes);
app.use('/region', regionRoutes);

// 404 Error handling
app.use((req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    res.status(404).render('error/404', { title: '404 Page Not Found', breadcrumbs });
});

const port = 3000;
app.listen(port, () => {
    console.log(`Server running on http://localhost:${port}`);
});
