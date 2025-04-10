const express = require('express');
const axios = require('axios');
const router = express.Router();

router.get("/edit/:id", async (req, res) => {
    try {
        const id = req.params.id;
        const breadcrumbs = [{ name: 'Home', url: '/' }];
        const fleetResponse = await axios.get(`http://localhost:8000/api/fleet/${id}`);
        const fleetData = fleetResponse.data;

        res.render("edit-fleet", { fleetData, title: 'Edit', breadcrumbs });
    } catch (error) {
        console.error(error.message);
        res.status(500).send("Fleet not found or server error");
    }
});

router.post("/edit/:id", async (req, res) => {
    try {
        const { fleet_number, operator_code, reg, depot, branding } = req.body;

        const response = await fetch(`${Fleet_API_URL}/${req.params.id}`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                fleet_number,
                operator_code,
                reg,
                depot,
                branding,
            }),
        });

        if (!response.ok) {
            console.error(`API response: ${response.statusText}`);
            throw new Error("Failed to update fleet data");
        }

        res.redirect("/fleet/list");
    } catch (error) {
        console.error(error.message);
        res.status(500).send("Failed to update fleet data");
    }
});

router.get('/:name', async (req, res) => {
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
        res.render('fleet', { title: `${operatorName}`, operatorData, fleetData, breadcrumbs, regionNames });
    } catch (error) {
        console.error('Error fetching operator data:', error.response?.data || error.message);
        res.status(404).send('Operator not found');
    }
});

module.exports = router;