import request from 'supertest';

process.env.SB_URL = 'http://localhost';
process.env.SB_SERVICE_KEY = 'key';

jest.mock('../server/utils/supabaseClient', () => ({ supabase: { from: jest.fn() } }));
jest.mock('../server/utils/scraper');

function setupSupabase(responses: Array<{ data: any; error: any }>) {
  const { supabase } = require('../server/utils/supabaseClient');
  const chain: any = {};
  chain.select = jest.fn(() => chain);
  chain.eq = jest.fn(() => chain);
  chain.update = jest.fn(() => chain);
  chain.insert = jest.fn(() => chain);
  chain.upsert = jest.fn(() => chain);
  chain.maybeSingle = jest.fn(() => Promise.resolve(responses.shift()));
  (supabase.from as jest.Mock).mockReturnValue(chain);
}

afterEach(() => {
  jest.clearAllMocks();
});

describe('Manual Scan Endpoint', () => {
  test('POST /manual-scan validates all required fields', async () => {
    const app = (await import('../server/app')).default;

    // Missing barcode
    let res = await request(app).post('/manual-scan').send({ name: 'Test', size: '500ml' });
    expect(res.status).toBe(403);
    expect(res.body.error).toBe('Invalid barcode');

    // Missing name
    res = await request(app).post('/manual-scan').send({ code: '123', size: '500ml' });
    expect(res.status).toBe(403);
    expect(res.body.error).toBe('Invalid name');

    // Missing size
    res = await request(app).post('/manual-scan').send({ code: '123', name: 'Test' });
    expect(res.status).toBe(403);
    expect(res.body.error).toBe('Invalid size');
  });

  test('POST /manual-scan creates new product successfully', async () => {
    setupSupabase([
      { data: null, error: null }, // No existing product
      {
        data: {
          id: 1,
          barcode: '123456789012',
          name: 'Cleaning Solution',
          contents_size_weight: '500ml',
          sds_url: 'http://example.com/sds.pdf',
        },
        error: null,
      },
    ]);

    const { searchWithManualData } = require('../server/utils/scraper');
    (searchWithManualData as jest.Mock).mockResolvedValue({
      name: 'Cleaning Solution',
      contents_size_weight: '500ml',
      sdsUrl: 'http://example.com/sds.pdf',
    });

    const app = (await import('../server/app')).default;
    const res = await request(app).post('/manual-scan').send({
      code: '123456789012',
      name: 'Cleaning Solution',
      size: '500ml',
    });

    expect(res.status).toBe(200);
    expect(res.body.isManualEntry).toBe(true);
    expect(res.body.product.name).toBe('Cleaning Solution');
    expect(res.body.product.contents_size_weight).toBe('500ml');
    expect(res.body.product.sds_url).toBe('http://example.com/sds.pdf');
    expect(res.body.message).toBe('Product created from manual entry');
  });

  test('POST /manual-scan updates existing incomplete product', async () => {
    setupSupabase([
      {
        data: {
          id: 1,
          barcode: '123456789012',
          name: null,
          contents_size_weight: null,
          sds_url: null,
        },
        error: null,
      },
      {
        data: {
          id: 1,
          barcode: '123456789012',
          name: 'Updated Product',
          contents_size_weight: '750ml',
          sds_url: 'http://example.com/updated-sds.pdf',
        },
        error: null,
      },
    ]);

    const { searchWithManualData } = require('../server/utils/scraper');
    (searchWithManualData as jest.Mock).mockResolvedValue({
      name: 'Updated Product',
      contents_size_weight: '750ml',
      sdsUrl: 'http://example.com/updated-sds.pdf',
    });

    const app = (await import('../server/app')).default;
    const res = await request(app).post('/manual-scan').send({
      code: '123456789012',
      name: 'Updated Product',
      size: '750ml',
    });

    expect(res.status).toBe(200);
    expect(res.body.updated).toBe(true);
    expect(res.body.existingInDatabase).toBe(true);
    expect(res.body.message).toBe('Product updated with manual entry data');
  });

  test('POST /manual-scan handles existing complete product', async () => {
    setupSupabase([
      {
        data: {
          id: 1,
          barcode: '123456789012',
          name: 'Complete Product',
          contents_size_weight: '1L',
          sds_url: 'http://example.com/existing-sds.pdf',
        },
        error: null,
      },
    ]);

    const app = (await import('../server/app')).default;
    const res = await request(app).post('/manual-scan').send({
      code: '123456789012',
      name: 'Manual Product',
      size: '500ml',
    });

    expect(res.status).toBe(200);
    expect(res.body.existingInDatabase).toBe(true);
    expect(res.body.message).toBe('Product found in database');
    // Should return existing product data, not manual input
    expect(res.body.product.name).toBe('Complete Product');
    expect(res.body.product.contents_size_weight).toBe('1L');
  });

  test('POST /manual-scan handles watchlist check for existing user', async () => {
    setupSupabase([
      {
        data: {
          id: 1,
          name: 'Test Product',
        },
        error: null,
      },
      {
        data: {
          id: 1,
          created_at: '2025-01-01T00:00:00Z',
        },
        error: null,
      },
    ]);

    const app = (await import('../server/app')).default;
    const res = await request(app).post('/manual-scan').send({
      code: '123456789012',
      name: 'Test Product',
      size: '500ml',
      userId: 'user123',
    });

    expect(res.status).toBe(200);
    expect(res.body.alreadyInWatchlist).toBe(true);
    expect(res.body.message).toBe('"Test Product" is already in your chemical register list');
  });
});
