const express = require('express');
const router = express.Router();
const axios = require('axios');

router.get('/stops', async (req, res) => {
  const { ymax, ymin, xmax, xmin } = req.query;

  if (!ymax || !ymin || !xmax || !xmin) {
    return res.status(400).json({ error: 'Missing bounding box parameters' });
  }

  const url = `https://bustimes.org/stops.json?ymax=${ymax}&ymin=${ymin}&xmax=${xmax}&xmin=${xmin}`;

  try {
    const response = await axios.get(url);
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching stops:', error.message);
    res.status(500).json({ error: 'Failed to fetch stops' });
  }
});

module.exports = router;
