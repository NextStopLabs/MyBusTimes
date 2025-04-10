const express = require('express');
const axios = require('axios');
const router = express.Router();

// Example for the operator-related routes
router.get('/', async (req, res) => {
    try {
        const breadcrumbs = [{ name: 'Home', url: '/' }];

        const response = await axios.get(`http://localhost:8000/api/operators/`);
        const operatorData = response.data;
        res.render('operator', { title: 'Operators', operatorData, breadcrumbs });
    } catch (error) {
        console.error('Error fetching operator data:', error.response?.data || error.message);
        res.status(404).send('Operators not found');
    }
});

router.get('/:name', async (req, res) => {
    try {
        const operatorName = req.params.name;
        const breadcrumbs = [{ name: 'Home', url: '/' }];

        const operatorResponse = await axios.get(`http://localhost:8000/api/operators/${operatorName}`);
        const operatorData = operatorResponse.data;

        const regionsResponse = await axios.get(`http://localhost:8000/api/regions/`);
        const regionsData = regionsResponse.data;

        const route_response = await axios.get(`http://localhost:8000/api/routes/?route_operator=${operatorData.id}`);
        const routeData = route_response.data;

        const regionNames = operatorData.region.map(regionId => {
            const region = regionsData.find(r => r.id === regionId);
            return region ? { name: region.region_name, code: region.region_code, in_the: region.in_the } : null;
        }).filter(region => region);
        const regionBreadcrumb = regionNames.map(region => region.name).join(' / ');
        if (regionBreadcrumb) {
            regionNames.forEach((region, index) => {
                breadcrumbs.push({
                    name: region.name,
                    inThe: region.in_the,
                    url: `/region/${region.code}`,
                    className: index === regionNames.length - 1 ? 'default' : 'region'
                });
            });
        }

        breadcrumbs.push({ name: operatorName, url: `/operator/${encodeURIComponent(operatorName)}` });
        res.render('operators', { title: `${operatorName}`, operatorData, routeData, breadcrumbs, regionNames });
    } catch (error) {
        console.error('Error fetching operator data:', error.response?.data || error.message);
        res.status(404).send('Operator not found');
    }
});

module.exports = router;