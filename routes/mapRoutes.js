/**
 * @description      :
 * @author           : Kai
 * @group            :
 * @created          : 22/04/2025 - 00:08:30
 *
 * MODIFICATION LOG
 * - Version         : 1.0.0
 * - Date            : 22/04/2025
 * - Author          : Kai
 * - Modification    :
 **/
const express = require("express");
const path = require("path");
const router = express.Router();
const axios = require("axios");

function customSort(routes) {
  return routes.sort((a, b) => {
    const parseRoute = (route) => {
      const num = route["Route Num"];

      if (typeof num !== "string") return [Infinity, 3, ""];

      const normal = num.match(/^(\d+)$/);
      const prefix = num.match(/^([A-Za-z]+)(\d+)$/);
      const suffix = num.match(/^(\d+)([A-Za-z]+)$/);

      if (normal) {
        return [parseInt(normal[1]), 0, ""];
      } else if (prefix) {
        const prefixStr = prefix[1];
        const prefixLengthCategory = prefixStr.length > 1 ? 4 : 1;
        return [parseInt(prefix[2]), prefixLengthCategory, prefixStr];
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


router.get("/", (req, res) => {
  const breadcrumbs = [{ name: "Home", url: "/" }];

  // Make a GET request to the updated API
  axios
    .get("http://localhost:8000/api/game/")
    .then((response) => {
      const games = response.data;

      res.render("map/gameList", {
        title: "Select Game",
        breadcrumbs,
        games,
        style: "narrow",
      });
    })
    .catch((err) => {
      console.error(err);
      res.status(500).send("Error fetching game routes from the API");
    });
});

router.get("/:game/", async (req, res) => {
  const game = req.params.game;
  const routesApiUrl = `http://localhost:8000/api/game/${game}/`;
  const breadcrumbs = [{ name: "Home", url: "/" }];
  breadcrumbs.push({ name: game, url: `/game/${game}`, className: "default" });

  try {
    // Fetch the routes data from the API
    const response = await axios.get(routesApiUrl);
    const routes = response.data;

    // Collect all unique destinations from both Inbound and Outbound directions
    const allDestinations = [
      ...new Set(
        routes.flatMap((route) => [
          route.Inbound["In Dest"],
          route.Inbound["Out Dest"],
          route.Outbound["In Dest"],
          route.Outbound["Out Dest"],
        ])
      ),
    ].sort((a, b) => a.localeCompare(b));

    res.render("map/gameMap", {
      title: "Find Routes",
      breadcrumbs,
      startPoint: "null",
      endPoint: "null",
      allDestinations,
      game,
      routes: [],
      style: "narrow",
    });
  } catch (error) {
    console.error("Error fetching routes:", error);
    res.status(500).send("Error fetching routes from the API");
  }
});

router.get("/:game/map", async (req, res) => {
  const game = req.params.game;
  const routesApiUrl = `https://new.mybustimes.cc/api/game/${game}`; // API endpoint for routes
  const destsApiUrl = `https://new.mybustimes.cc/api/game/${game}/Dests`; // API endpoint for destinations
  const breadcrumbs = [{ name: "Home", url: "/" }];
  breadcrumbs.push({ name: game, url: `/game/${game}`, className: "default" });

  try {
    // Fetch the routes and destinations data from the API
    const routesResponse = await axios.get(routesApiUrl);
    const destsResponse = await axios.get(destsApiUrl);

    if (routesResponse.status !== 200 || destsResponse.status !== 200) {
      console.error(
        `API responded with status: ${routesResponse.status} and ${destsResponse.status}`
      );
      return res
        .status(500)
        .send("Error fetching routes or destinations from the API");
    }

    const routes = routesResponse.data;
    const destinations = destsResponse.data;

    res.render("map/networkMap", {
      title: `${game} Network Map`,
      breadcrumbs,
      game,
      routes,
      destinations,
      style: "full",
    });
  } catch (error) {
    console.error("Error fetching data from the API:", error);
    res.status(500).send("Error fetching data from the API");
  }
});

router.get("/:game/routes", async (req, res) => {
  const game = req.params.game;
  const routesApiUrl = `http://localhost:8000/api/game/${game}`; // Replace with your actual API endpoint
  const breadcrumbs = [{ name: "Home", url: "/" }];
  breadcrumbs.push({ name: game, url: `/game/${game}`, className: "default" });
  breadcrumbs.push({
    name: "Routes",
    url: `/map/${game}/routes`,
    className: "default",
  });

  try {
    // Fetch the routes data from the API
    const response = await axios.get(routesApiUrl);

    if (response.status !== 200) {
      console.error(`API responded with status: ${response.status}`);
      return res.status(500).send("Error fetching routes from the API");
    }

    const routes = customSort(response.data);

    res.render("map/gameRoutes", {
      title: `${game} Routes`,
      breadcrumbs,
      game,
      routes,
      style: "wide",
    });
  } catch (error) {
    console.error("Error fetching routes from the API:", error);
    res.status(500).send("Error fetching routes from the API");
  }
});

router.get("/:game/findRoute", async (req, res) => {
  const game = req.params.game;
  const routesApiUrl = `http://localhost:8000/api/game/${game}`; // Replace with your actual API endpoint
  const breadcrumbs = [{ name: "Home", url: "/" }];
  const { startPoint, endPoint } = req.query;
  breadcrumbs.push({ name: game, url: `/game/${game}`, className: "default" });

  if (!startPoint || !endPoint) {
    return res
      .status(400)
      .send("Both startPoint and endPoint must be provided");
  }

  try {
    // Fetch the routes data from the API
    const response = await axios.get(routesApiUrl);

    if (response.status !== 200) {
      console.error(`API responded with status: ${response.status}`);
      return res.status(500).send("Error fetching routes from the API");
    }

    const routes = response.data;
    const resultOutput = [];

    const allDestinations = [
      ...new Set(
        routes.flatMap((route) => [
          route.Inbound["In Dest"],
          route.Inbound["Out Dest"],
          route.Outbound["In Dest"],
          route.Outbound["Out Dest"],
        ])
      ),
    ].sort((a, b) => a.localeCompare(b));

    const formatRoute = (num, from, to) => ({
      label: num,
      from,
      to,
      display: `Route ${num} from ${from} to ${to}`,
    });

    // Build a list of route segments
    const routeSegments = [];
    routes.forEach((route) => {
      routeSegments.push({
        num: route["Route Num"],
        from: route.Inbound["In Dest"],
        to: route.Inbound["Out Dest"],
      });
      routeSegments.push({
        num: route["Route Num"],
        from: route.Outbound["In Dest"],
        to: route.Outbound["Out Dest"],
      });
    });

    const maxDepth = 5;

    function dfs(currentPoint, path = [], depth = 0, visited = new Set()) {
      if (depth > maxDepth) return;
      if (currentPoint === endPoint && path.length > 0) {
        resultOutput.push(
          path.map((seg) => formatRoute(seg.num, seg.from, seg.to))
        );
        return;
      }

      routeSegments.forEach((segment) => {
        if (
          segment.from === currentPoint &&
          !visited.has(segment.from + segment.to)
        ) {
          visited.add(segment.from + segment.to);
          dfs(segment.to, [...path, segment], depth + 1, new Set(visited));
        }
      });
    }

    dfs(startPoint);

    if (resultOutput.length === 0) {
      resultOutput.push(["No routes found between the specified points."]);
    }

    res.render("map/gameMap", {
      title: "Find Routes",
      breadcrumbs,
      allDestinations,
      game,
      startPoint,
      endPoint,
      routes: resultOutput,
      style: "narrow",
    });
  } catch (error) {
    console.error("Error fetching routes from the API:", error);
    res.status(500).send("Error fetching routes from the API");
  }
});

module.exports = router;
