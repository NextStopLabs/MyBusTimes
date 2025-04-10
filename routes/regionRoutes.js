const express = require('express');
const axios = require('axios');
const router = express.Router();

router.get('/:code', async (req, res) => {
    const code = req.params.code;
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    try {
        const regionResponse = await axios.get(`http://localhost:8000/api/regions/${code}/`);
        const regionData = regionResponse.data;

        breadcrumbs.push({ name: `${regionData.region_name}`, url: `/region/${regionData.region_code}` });

        const operatorResponse = await axios.get(`http://localhost:8000/api/operators/?region=${regionData.id}`);
        const operatorData = operatorResponse.data;

        res.render('region', { title: `Region ${regionData.region_name}`, regionData, operatorData, breadcrumbs });
    } catch (error) {
        console.error('Error fetching region data:', error);
        res.status(404).send('Region not found');
    }
});

module.exports = router;