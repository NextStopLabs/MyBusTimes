const express = require('express');
const axios = require('axios');
const cookie = require('cookie');
const router = express.Router();

router.get('/login', (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    res.render('login', { title: 'Login', breadcrumbs });
});

router.post('/login', async (req, res) => {
    const { username, password } = req.body;

    try {
        const response = await axios.post('http://localhost:8000/api/users/login/', {
            username,
            password
        });
        const { refresh } = response.data;
        const refreshTokenCookie = cookie.serialize('refresh_token', refresh, { httpOnly: false, secure: process.env.NODE_ENV === 'production', sameSite: 'Strict', maxAge: 60 * 60 * 24 * 365, path: '/', });
        fetch(`http://localhost:8000/api/users/search/${username}/`)
            .then(response => response.json())
            .then(data => {
                fetch(`http://localhost:8000/api/themes/${data.theme}/`)
                    .then(response => response.json())
                    .then(themeData => {
                        const serializedCookies = cookie.serialize('username', data.username, { httpOnly: false, path: '/' });
                        const themeCookie = cookie.serialize('themeDark', themeData.dark_theme, 'theme', themeData.css, 'brand-color', themeData.main_colour, 'themeID', data.theme, { httpOnly: false, path: '/' });
                        res.setHeader('Set-Cookie', [serializedCookies, themeCookie, refreshTokenCookie]);
                        console.log(refreshTokenCookie);
                        res.redirect(`/u/${data.username}`);
                    })
                    .catch(error => {
                        console.error('Error fetching user data:', error);
                        res.send('Error fetching user data.');
                    });
            })
            .catch(error => {
                console.error('Error fetching user data:', error);
                res.send('Error fetching user data.');
            });
    } catch (error) {
        console.error('Login failed:', error.response?.data || error.message);
        res.send('Login failed. Invalid credentials.');
    }
});

router.get('/register', (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    res.render('register', { error: null, title: 'Register', breadcrumbs });
});

router.post('/register', async (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    const { username, email, firstName, lastName, password } = req.body;

    const userData = {
        username,
        email,
        first_name: firstName,
        last_name: lastName,
        password
    };

    try {
        const response = await fetch('http://localhost:8000/api/users/register/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(userData),
        });

        const result = await response.json();

        if (result.success) {
            res.redirect('/login');
        } else {
            res.render('register', { error: result.message, title: 'Register', breadcrumbs });
        }
    } catch (error) {
        res.render('register', { error: 'An error occurred, please try again.', title: 'Register', breadcrumbs });
    }
});

module.exports = router;