import express from 'express';
import { fetchSdsByNameSimple } from '../utils/scraper.js';
import { isValidName, isValidSize } from '../utils/validation.js';
import logger from '../utils/logger.js';

const router = express.Router();

router.post('/', async (req, res) => {
  const { name, size } = req.body ?? {};

  if (!isValidName(name)) {
    return res.status(400).json({ error: 'Invalid name' });
  }

  if (size && !isValidSize(size)) {
    return res.status(400).json({ error: 'Invalid size' });
  }

  try {
    logger.info({ name, size }, '[SDS-BY-NAME] Processing request');
    const { sdsUrl, topLinks } = await fetchSdsByNameSimple(name, size ?? undefined);
    res.json({
      sdsUrl,
      verified: Boolean(sdsUrl),
      topLinks,
    });
  } catch (err) {
    logger.error({ name, size, err: String(err) }, '[SDS-BY-NAME] Lookup failed');
    res.status(500).json({ error: 'FAILED_TO_FETCH_SDS' });
  }
});

export default router;
