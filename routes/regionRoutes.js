const express = require('express');
const axios = require('axios');
const router = express.Router();

router.get('/:code', async (req, res) => {
    try {
        const code = req.params.code;
        const breadcrumbs = [{ name: 'Home', url: '/' }];

        const regionResponse = await axios.get(`http://localhost:8000/api/regions/${code}/`);
        const regionData = regionResponse.data;

        breadcrumbs.push({ name: `${regionData.region_name}`, url: `/region/${regionData.region_code}` });

        const operatorResponse = await axios.get(`http://localhost:8000/api/operators/?region=${regionData.id}`);
        const operatorData = operatorResponse.data;

        res.render('region/region', { title: `Region ${regionData.region_name}`, regionData, operatorData, breadcrumbs });
    } catch (error) {
        console.error('Error fetching operator data:', error.response?.data || error.message);
        res.status(404).send('Operators not found');
    }
});

module.exports = router;