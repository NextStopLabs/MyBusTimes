/**
    * @description      : 
    * @author           : Kai
    * @group            : 
    * @created          : 21/04/2025 - 15:56:58
    * 
    * MODIFICATION LOG
    * - Version         : 1.0.0
    * - Date            : 21/04/2025
    * - Author          : Kai
    * - Modification    : 
**/
const express = require('express');
const router = express.Router();
const axios = require('axios');

// GET route for feature toggles page
router.get('/feature_toggles', async (req, res) => {
    const breadcrumbs = [
        { name: 'Home', url: '/' },
        { name: 'Admin', url: '/admin' },
        { name: 'Feature Toggles', url: '/admin/feature_toggles', className: 'default' }
    ];

    let toggleData;
    try {
        const response = await axios.get('http://localhost:8000/api/feature-toggles/');
        toggleData = response.data;
    } catch (error) {
        console.error('Error fetching feature toggles:', error.response?.data || error.message);
        toggleData = [];
    }
    res.render('admin/feature_toggles', {
        title: 'Feature Toggles - Admin ',
        breadcrumbs,
        style: 'narrow',
        featureToggles: toggleData
    });
});

// POST route to update feature toggles
router.post('/feature_toggles/update', async (req, res) => {
    try {
        const { toggle, enabled } = req.body;
        
        // Get refresh token from cookies
        const refreshToken = req.cookies.refresh;
        
        // Get new access token using refresh token
        const refreshResponse = await axios.post('http://localhost:8000/api/users/refresh/', {
            refresh: refreshToken
        });
        const accessToken = refreshResponse.data.access;

        // Make feature toggle request with new access token
        const response = await axios.post('http://localhost:8000/api/feature-toggles/', {
            toggle,
            enabled
        }, {
            headers: {
                'Authorization': `Bearer ${accessToken}`
            }
        });
        
        res.json({ success: true, data: response.data });
    } catch (error) {
        console.error('Error updating feature toggle:', error.response?.data || error.message);
        res.status(500).json({ 
            success: false, 
            error: error.response?.data || error.message 
        });
    }
});

module.exports = router;
