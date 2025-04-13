const express = require('express');
const axios = require('axios');
const cookie = require('cookie');
const router = express.Router();

router.get('/login', (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    res.render('account/login', { title: 'Login', breadcrumbs });
});

router.get('/logout', (req, res) => {
    for (const cookie in req.cookies) {
        res.clearCookie(cookie);
    }
    if (req.session) {
        req.session.destroy(err => {
            if (err) {
                console.log('Session destruction error:', err);
            }
        });
    }
    res.redirect('/');
});


router.post('/login', async (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    const { username, password } = req.body;

    try {
        const response = await axios.post('http://localhost:8000/api/users/login/', {
            username,
            password
        });
        const { refresh } = response.data;
        fetch(`http://localhost:8000/api/users/search/${username}/`)
            .then(response => response.json())
            .then(data => {
                fetch(`http://localhost:8000/api/themes/${data.theme}/`)
                    .then(response => response.json())
                    .then(themeData => {
                        const cookies = [
                            cookie.serialize('refresh_token', refresh, { httpOnly: false, secure: process.env.NODE_ENV === 'production', sameSite: 'Strict', maxAge: 60 * 60 * 24 * 365, path: '/', }),
                            cookie.serialize('username', data.username, { httpOnly: false, path: '/' }),
                            cookie.serialize('themeDark', themeData.dark_theme, { httpOnly: false, path: '/' }),
                            cookie.serialize('theme', themeData.css, { httpOnly: false, path: '/' }),
                            cookie.serialize('brand-color', themeData.main_colour, { httpOnly: false, path: '/' }),
                            cookie.serialize('themeID', data.theme, { httpOnly: false, path: '/' }),
                        ];
                        res.setHeader('Set-Cookie', cookies);
                        console.log(cookies);
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
        //console.error('Login failed:', error.response?.data || error.message);
        res.render('account/login', { error: 'Login failed. Invalid credentials.', title: 'Login', breadcrumbs });
    }
});

router.get('/register', (req, res) => {
    const breadcrumbs = [{ name: 'Home', url: '/' }];
    res.render('account/register', { error: null, title: 'Register', breadcrumbs });
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
            res.render('account/register', { error: result.message, title: 'Register', breadcrumbs });
        }
    } catch (error) {
        res.render('account/register', { error: 'An error occurred, please try again.', title: 'Register', breadcrumbs });
    }
});

module.exports = router;