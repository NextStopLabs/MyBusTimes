const express = require('express');
const axios = require('axios');
const router = express.Router();
const cookie = require('cookie');
const cookieParser = require('cookie-parser');

router.use(cookieParser());

let helperPermsData = ['none'];

async function getHelperPerms(operatorId, ownerId, userId) {
    if (ownerId !== userId) {
        try {
            const response = await axios.get(`http://localhost:8000/api/helper/?operator=${operatorId}&helper=${userId}`);
            return response.data.perms || ['none'];
        } catch (error) {
            console.error('Error fetching helper permissions:', error.message);
            return ['none'];
        }
    } else {
        return ['owner'];
    }
}

function customSort(routes) {
    return routes.sort((a, b) => {
        const parseRoute = (route) => {
            const num = route.route_num;

            if (typeof num !== 'string') return [Infinity, 3, ''];

            const normal = num.match(/^(\d+)$/);
            const prefix = num.match(/^([A-Za-z]+)(\d+)$/);
            const suffix = num.match(/^(\d+)([A-Za-z]+)$/);

            if (normal) {
                return [parseInt(normal[1]), 0, ''];
            } else if (prefix) {
                return [parseInt(prefix[2]), 1, prefix[1]];
            } else if (suffix) {
                return [parseInt(suffix[1]), 2, suffix[2]];
            } else {
                return [Infinity, 3, num];
            }
        };

        const aVal = parseRoute(a);
        const bVal = parseRoute(b);

        if (aVal[0] !== bVal[0]) return aVal[0] - bVal[0];
        if (aVal[1] !== bVal[1]) return aVal[1] - bVal[1];
        return aVal[2].localeCompare(bVal[2]);
    });
}

function getUniqueLinkedRoutes(routes) {
    const visited = new Set();
    const routeMap = new Map(routes.map(route => [route.id, route]));

    const adjacency = {};
    for (const route of routes) {
        if (!adjacency[route.id]) adjacency[route.id] = new Set();

        for (const linked of route.linked_route) {
            adjacency[route.id].add(linked.id);
            if (!adjacency[linked.id]) adjacency[linked.id] = new Set();
            adjacency[linked.id].add(route.id);
        }
    }

    const uniqueGroups = [];

    function dfs(id, group) {
        if (visited.has(id)) return;
        visited.add(id);
        group.push(routeMap.get(id));
        for (const neighbor of (adjacency[id] || [])) {
            dfs(neighbor, group);
        }
    }

    for (const route of routes) {
        if (!visited.has(route.id)) {
            const group = [];
            dfs(route.id, group);
            group.sort((a, b) => a.route_num.localeCompare(b.route_num));
            uniqueGroups.push(group[0]);
        }
    }

    return customSort(uniqueGroups);
}

router.get('/', async (req, res) => {
    try {
        const breadcrumbs = [{ name: 'Home', url: '/' }];

        const response = await axios.get(`http://localhost:8000/api/operators/`);
        const operatorData = response.data;
        res.render('operator/operators', { 
            title: 'Operators', 
            operatorData, 
            breadcrumbs,
            style: 'wide'
        });
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

        const route_response = await axios.get(`http://localhost:8000/api/routes/?route_operators=${operatorData.id}`);
        let routeData = route_response.data;
        const total_routes = route_response.data.length;
        
        routeData = getUniqueLinkedRoutes(routeData);

        const regionNames = operatorData.region.map(region => ({
            name: region.region_name,
            code: region.region_code,
            in_the: region.in_the
        }));
        
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
        res.render('operator/operator', { 
            title: `${operatorName}`, 
            operatorData, 
            routeData, 
            breadcrumbs, 
            regionNames,
            total_routes,
            style: 'wide'
        });
    } catch (error) {
        console.error('Error fetching operator data:', error.response?.data || error.message);
        res.status(404).send('Operator not found');
    }
});

router.get('/:name/route/:id', async (req, res) => {
    try {
        const breadcrumbs = [{ name: 'Home', url: '/' }];
        const operatorName = req.params.name;
        const routeId = req.params.id;

        const route_response = await axios.get(`http://localhost:8000/api/routes/?id=${routeId}`);
        const routeData = route_response.data[0];

        const operatorResponse = await axios.get(`http://localhost:8000/api/operators/${operatorName}`);
        const operatorData = operatorResponse.data;

        const regionNames = operatorData.region.map(region => ({
            name: region.region_name,
            code: region.region_code,
            in_the: region.in_the
        }));
        
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
        
        if (routeData.linked_route) {
            breadcrumbs.push({ className: 'region', name: routeData.route_num, url: `/operator/${encodeURIComponent(operatorName)}/route/${routeData.id}` });
            routeData.linked_route.forEach((linkedRoute, index) => {
                breadcrumbs.push({ 
                    name: linkedRoute.route_num, 
                    url: `/operator/${encodeURIComponent(operatorName)}/route/${linkedRoute.id}`,
                    className: index === routeData.linked_route.length - 1 ? 'default' : 'region'
                });
            });
        } else {
            breadcrumbs.push({ name: routeData.route_num, url: `/operator/${encodeURIComponent(operatorName)}/route/${routeData.id}` });
        }

        res.render('operator/route', { 
            title: `${operatorName}`, 
            operatorName,
            operatorData,
            routeData, 
            breadcrumbs, 
            style: 'full'
        });
    } catch (error) {
        console.error('Error fetching operator data:', error.response?.data || error.message);
        res.status(404).send('Route not found');
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

        const regionNames = operatorData.region.map(region => ({
            name: region.region_name,
            code: region.region_code,
            in_the: region.in_the
        }));
        
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

        const username = req.cookies.username;

        const userResponse = await axios.get(`http://localhost:8000/api/users/search/?username=${username}`);
        const userData = userResponse.data;
        const user = userData[0].id;

        helperPermsData = await getHelperPerms(operatorData.id, operatorData.owner, user);

        breadcrumbs.push({ name: operatorName, url: `/operator/${encodeURIComponent(operatorName)}` });
        res.render('operator/fleet', { 
            title: `${operatorName}`, 
            operatorData, 
            fleetData, 
            breadcrumbs, 
            helperPermsData,
            regionNames,
            useFont: true,
            style: 'full'
        });
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
        const operatorDetailResponse = await axios.get(`http://localhost:8000/api/operators/${operatorName}`);
        const operatorDetailData = operatorDetailResponse.data;

        const fleetResponse = await axios.get(`http://localhost:8000/api/fleet/${vehicleID}`);
        const fleetData = fleetResponse.data;

        if (fleetData.operator.operator_name !== operatorName) {
            return res.redirect(`/operator/${fleetData.operator.operator_name}/vehicle/${vehicleID}`);
        }

        const regionNames =  operatorDetailData.region.map(region => ({
            name: region.region_name,
            code: region.region_code,
            in_the: region.in_the
        }));
        
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

        const username = req.cookies.username;

        const userResponse = await axios.get(`http://localhost:8000/api/users/search/?username=${username}`);
        const userData = userResponse.data;
        const user = userData[0].id;

        helperPermsData = await getHelperPerms(operatorDetailData.id, operatorDetailData.owner, user);

        breadcrumbs.push({ name: 'Vehicles', url: `/operator/${encodeURIComponent(operatorName)}/vehicle/#${fleetData.fleet_number} - ${fleetData.operator.operator_code}` });
        breadcrumbs.push({ name: `${fleetData.fleet_number} - ${fleetData.reg}`, url: `/operator/${encodeURIComponent(operatorName)}/vehicle/${vehicleID}` });

        res.render("operator/vehicle", { 
            title: `${operatorDetailData.operator_code} - ${fleetData.fleet_number}`, 
            fleetData, 
            helperPermsData, 
            breadcrumbs,
            useFont: true,
            style: 'narrow'
        });
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

        breadcrumbs.push({ name: operatorName, url: `/operator/${encodeURIComponent(operatorName)}` });

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

        breadcrumbs.push({ name: 'Vehicles', url: `/operator/${encodeURIComponent(operatorName)}/vehicle/#${fleetData.fleet_number} - ${fleetData.operator.operator_code}` });
        breadcrumbs.push({ name: `${fleetData.fleet_number} - ${fleetData.reg}`, url: `/operator/${encodeURIComponent(operatorName)}/vehicle/${vehicleID}` });

        res.render("operator/edit", { 
            title: `${operatorDetailData.operator_code} - ${fleetData.fleet_number}`, 
            fleetData, 
            typeData, 
            liveryData, 
            userData, 
            operatorData, 
            breadcrumbs,
            style: 'narrow'
        });
    } catch (error) {
        console.error(error.message);
        res.status(500).send("Fleet not found or server error");
    }
});

router.post("/update-bus/:id", async (req, res) => {
    try {
        const vehicleID = req.params.id;
        const refreshToken = req.cookies.refresh_token;

        if (!refreshToken) {
            return res.status(401).send("Refresh token not found.");
        }

        const tokenResponse = await axios.post("http://localhost:8000/api/users/refresh/", {
            refresh: refreshToken
        });

        cookie.serialize('refresh_token', tokenResponse.data.refresh, { httpOnly: false, secure: process.env.NODE_ENV === 'production', sameSite: 'Strict', maxAge: 60 * 60 * 24 * 365, path: '/', }),
            res.setHeader('Set-Cookie', cookie);

        const accessToken = tokenResponse.data.access;

        const inService = req.body.in_service === 'on';
        const preserved = req.body.preserved === 'on';
        const openTop = req.body.open_top === 'on';

        const updatedVehicleData = {
            last_modified_by: req.body.user,
            fleet_number: req.body.fleet_number,
            reg: req.body.reg,
            operator_id: parseInt(req.body.operator),
            loan_operator_id: req.body.loan_operator !== "null" ? parseInt(req.body.loan_operator) : null,
            vehicle_type_data_id: parseInt(req.body.type),
            type_details: req.body.type_details,
            length: req.body.length,
            open_top: openTop,
            livery_id: parseInt(req.body.livery),
            colour: req.body.colour,
            branding: req.body.branding,
            prev_reg: req.body.prev_reg,
            depot: req.body.depot,
            name: req.body.name,
            features: req.body.features,
            notes: req.body.notes,
            in_service: inService,
            preserved: preserved
        };
        
        await axios.patch(
            `http://localhost:8000/api/fleet/${vehicleID}/update/`,
            updatedVehicleData,
            {
                headers: {
                    Authorization: `Bearer ${accessToken}`
                }
            }
        );

        const fleetResponse = await axios.get(`http://localhost:8000/api/fleet/${vehicleID}`);
        const fleetData = fleetResponse.data;

        res.redirect(`/operator/${fleetData.operator.operator_name}/vehicle/${vehicleID}`);
    } catch (error) {
        //console.error(error.response?.data || error.message);
        res.status(500).send(error.response?.data);
    }
});

module.exports = router;