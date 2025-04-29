/**
    * @description      : 
    * @author           : Kai
    * @group            : 
    * @created          : 27/04/2025 - 14:57:49
    * 
    * MODIFICATION LOG
    * - Version         : 1.0.0
    * - Date            : 27/04/2025
    * - Author          : Kai
    * - Modification    : 
**/
const express = require('express');
const cookieParser = require('cookie-parser');
const axios = require('axios');

const router = express.Router();

const breadcrumbs = [{ name: 'Home', url: '/' }];
const title = 'Under Development'

router.get('/', async (req, res) => {
    const vehicleID = req.query.vehicle;
    const username = req.query.user;
    const operatorID = req.query.operator;
    const approved = req.query.approved;
    const pending = req.query.pending;
    const disapproved = req.query.disapproved;
    let userID = null;

    const breadcrumbs = [{ name: 'Home', url: '/' }];
    const title = 'Vehicle History'; // Assuming title is required but missing in your code

    if (username) {
        try {
            const user_response = await axios.get(`http://localhost:8000/api/users/search/${username}/`);
            
            if (user_response.status === 404) {
                userID = null;
            } else {
                const userData = user_response.data;
                userID = userData.id;
            }
        } catch (error) {
            if (error.response && error.response.status === 404) {
                return res.render('history/history', {
                    breadcrumbs,
                    title,
                    style: 'narrow',
                    error: 'User not found',
                    vehicleHistory: [],
                    vehicleID,
                    username,
                    operatorID,
                    approved,
                    pending,
                    disapproved
                });
            } else {
                return res.render('history/history', {
                    breadcrumbs,
                    title,
                    style: 'narrow',
                    error: 'An error occurred',
                    vehicleHistory: [],
                    vehicleID,
                    username,
                    operatorID,
                    approved,
                    pending,
                    disapproved
                });
            }
        }
    }

    let queryParams = [];
    if (vehicleID) queryParams.push(`vehicle=${vehicleID}`);
    if (userID) queryParams.push(`user=${userID}`);
    if (operatorID) queryParams.push(`operator=${operatorID}`);
    if (approved) queryParams.push(`approved=${approved}`);
    if (pending) queryParams.push(`pending=${pending}`);
    if (disapproved) queryParams.push(`disapproved=${disapproved}`);

    queryParams.push('order_by=-create_at');

    const queryString = queryParams.join('&');

    try {
        let vehicleHistory_response = await axios.get(`http://localhost:8000/api/history/?${queryString}`);
        const vehicleHistory = vehicleHistory_response.data;

        res.render('history/history', {
            breadcrumbs,
            title,
            style: 'narrow',
            error: '',
            vehicleHistory,
            vehicleID,
            username,
            operatorID,
            approved,
            pending,
            disapproved
        });
    } catch (error) {
        res.render('history/history', {
            breadcrumbs,
            title,
            style: 'narrow',
            error,
            vehicleHistory: [],
            vehicleID,
            username,
            operatorID,
            approved,
            pending,
            disapproved
        });
    }
});


module.exports = router;