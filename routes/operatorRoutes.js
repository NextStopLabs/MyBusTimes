const express = require('express');
const axios = require('axios');
const router = express.Router();
const cookieParser = require('cookie-parser');

router.use(cookieParser());

router.get('/', async (req, res) => {
    try {
        const breadcrumbs = [{ name: 'Home', url: '/' }];

        const response = await axios.get(`http://localhost:8000/api/operators/`);
        const operatorData = response.data;
        res.render('operator/operators', { title: 'Operators', operatorData, breadcrumbs });
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
        res.render('operator/operator', { title: `${operatorName}`, operatorData, routeData, breadcrumbs, regionNames });
    } catch (error) {
        console.error('Error fetching operator data:', error.response?.data || error.message);
        res.status(404).send('Operator not found');
    }
});

router.get('/:name/vehicle', async (req, res) => {
    try {
        const operatorName = req.params.name;
        const breadcrumbs = [{ name: 'Home', url: '/' }];

        const operatorResponse = await axios.get(`http://localhost:8000/api/operators/${operatorName}`);
        const operatorData = operatorResponse.data;

        const [fleetResponse, fleetLoanResponse] = await Promise.all([
            axios.get(`http://localhost:8000/api/fleet/?operator=${operatorData.id}`),
            axios.get(`http://localhost:8000/api/fleet/?loan_operator=${operatorData.id}`)
        ]);
        
        const fleetData = [...fleetResponse.data, ...fleetLoanResponse.data];
        
        const regionsResponse = await axios.get(`http://localhost:8000/api/regions/`);
        const regionsData = regionsResponse.data;

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
        res.render('operator/fleet', { title: `${operatorName}`, operatorData, fleetData, breadcrumbs, regionNames });
    } catch (error) {
        console.error('Error fetching operator data:', error.response?.data || error.message);
        res.status(404).send('Operator not found');
    }
});

router.get("/:name/vehicle/:id", async (req, res) => {
    try {
        const operatorName = req.params.name;
        const vehicleID = req.params.id;
        const breadcrumbs = [{ name: 'Home', url: '/' }];
        breadcrumbs.push({ name: operatorName, url: `/operator/${encodeURIComponent(operatorName)}` });
        breadcrumbs.push({ name: operatorName, url: `/operator/${encodeURIComponent(operatorName)}` });

        const operatorDetailResponse = await axios.get(`http://localhost:8000/api/operators/${operatorName}`);
        const operatorDetailData = operatorDetailResponse.data;

        const fleetResponse = await axios.get(`http://localhost:8000/api/fleet/${vehicleID}`);
        const fleetData = fleetResponse.data;

        res.render("operator/fleet-edit", { title: `${operatorDetailData.operator_code} - ${fleetData.fleet_number}`, fleetData, breadcrumbs });
    } catch (error) {
        console.error(error.message);
        res.status(500).send("Fleet not found or server error");
    }
});

router.get("/:name/vehicle/edit/:id", async (req, res) => {
    try {
        const operatorName = req.params.name;
        const vehicleID = req.params.id;
        const breadcrumbs = [{ name: 'Home', url: '/' }];

        const operatorDetailResponse = await axios.get(`http://localhost:8000/api/operators/${operatorName}`);
        const operatorDetailData = operatorDetailResponse.data;

        const username = req.cookies.username;
        if (!username) {
            return res.status(400).send('Username cookie not found');
        }

        const userResponse = await axios.get(`http://localhost:8000/api/users/search/?username=${username}`);
        const userData = userResponse.data;

        const operatorResponse = await axios.get(`http://localhost:8000/api/operators/?owner=${userData[0].id}`);
        const operatorData = operatorResponse.data;

        const fleetResponse = await axios.get(`http://localhost:8000/api/fleet/${vehicleID}`);
        const fleetData = fleetResponse.data;

        const liveryResponse = await axios.get(`http://localhost:8000/api/liveries/`);
        const liveryData = liveryResponse.data;

        const typeResponse = await axios.get(`http://localhost:8000/api/type/`);
        const typeData = typeResponse.data;

        res.render("operator/fleet-edit", { title: `${operatorDetailData.operator_code} - ${fleetData.fleet_number}`, fleetData, typeData, liveryData, operatorData, breadcrumbs });
    } catch (error) {
        console.error(error.message);
        res.status(500).send("Fleet not found or server error");
    }
});

module.exports = router;