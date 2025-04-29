/**
    * @description      : 
    * @author           : Kai
    * @group            : 
    * @created          : 27/04/2025 - 14:03:18
    * 
    * MODIFICATION LOG
    * - Version         : 1.0.0
    * - Date            : 27/04/2025
    * - Author          : Kai
    * - Modification    : 
**/
const express = require('express');
const axios = require('axios');
const router = express.Router();

router.get('/:username', async (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    const username = req.params.username;

    try {
        const user_response = await axios.get(`http://localhost:8000/api/users/search/${username}/`);
        const userData = user_response.data;

        const operator_response = await axios.get(`http://localhost:8000/api/operators/?owner=${userData.id}`);
        const operatorData = operator_response.data;

        const helper_operator_response = await axios.get(`http://localhost:8000/api/helper/?helper=${userData.id}`);
        const helper_operatorData = helper_operator_response.data;

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

                res.render('u/dashboard', {
                    title: `${username}`,
                    user: `${username}`,
                    userData: extendedUserData,
                    operatorData,
                    helper_operatorData,
                    breadcrumbs,
                    style: 'narrow'
                });
            } else {
                console.error('No valid badge data received');
                res.status(404).send('No valid badge data received');
            }
        } else {
            res.render('u/dashboard', {
                title: `${username}`,
                user: `${username}`,
                userData,
                operatorData,
                helper_operatorData,
                breadcrumbs,
                style: 'wide'
            });
        }
    } catch (error) {
        console.error('Error fetching user data:', error.response?.data || error.message);
        res.status(404).send('User not found');
    }
});

module.exports = router;