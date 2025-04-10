const express = require('express');
const fs = require('fs').promises;
const path = require('path');
const axios = require('axios');
const router = express.Router();

router.get('/:username', async (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    const username = req.params.username;

    try {
        const user_response = await axios.get(`http://localhost:8000/api/users/search/${username}/`);
        const userData = user_response.data;

        if (!userData.badges || !Array.isArray(userData.badges)) {
            return res.status(404).send('Badges not found for the user');
        }

        if (userData.badges.length > 0) {
            const badgePromises = userData.badges.map(async (badgeId) => {
                try {
                    const badgeResponse = await axios.get(`http://localhost:8000/api/badges/${badgeId}`);
                    return badgeResponse.data;
                } catch (error) {
                    console.error(`Error fetching badge with ID ${badgeId}:`, error.message);
                    return null;
                }
            });

            const badgeResponses = await Promise.all(badgePromises);
            const badges = badgeResponses.filter(response => response !== null);

            if (badges.length > 0) {
                const extendedUserData = { ...userData, badges };

                return res.render('dashboard', {
                    title: `${username}`,
                    user: `${username}`,
                    userData: extendedUserData,
                    breadcrumbs
                });
            } else {
                console.error('No valid badge data received');
                return res.status(404).send('No valid badge data received');
            }
        } else {
            return res.render('dashboard', {
                title: `${username}`,
                user: `${username}`,
                userData,
                breadcrumbs
            });
        }
    } catch (error) {
        console.error('Error fetching user data:', error.response?.data || error.message);
        return res.status(404).send('User not found');
    }
});

module.exports = router;