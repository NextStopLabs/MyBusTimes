const axios = require('axios');

module.exports = async (req, res, next) => {
    try {
        const response = await axios.get('http://localhost:8000/api/feature-toggles/');
        const featureToggles = response.data;
        res.locals.featureToggles = featureToggles;
    } catch (error) {
        console.error('Error fetching feature toggles:', error);
        res.locals.featureToggles = {};
    }
    next();
};
