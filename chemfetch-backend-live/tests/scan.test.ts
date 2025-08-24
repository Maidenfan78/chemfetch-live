import request from 'supertest';
import * as scraper from '../server/utils/scraper';

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
  test('POST /manual-scan returns 403 without name', async () => {
    const app = (await import('../server/app')).default;
    const res = await request(app).post('/manual-scan').send({ code: '123', size: '500ml' });
    expect(res.status).toBe(403);
    expect(res.body.error).toBe('Invalid name');
  });

  test('POST /manual-scan returns 403 without size', async () => {
    const app = (await import('../server/app')).default;
    const res = await request(app).post('/manual-scan').send({ code: '123', name: 'Test Product' });
    expect(res.status).toBe(403);
    expect(res.body.error).toBe('Invalid size');
  });

  test('POST /manual-scan returns 403 without code', async () => {
    const app = (await import('../server/app')).default;
    const res = await request(app)
      .post('/manual-scan')
      .send({ name: 'Test Product', size: '500ml' });
    expect(res.status).toBe(403);
    expect(res.body.error).toBe('Invalid barcode');
  });

  test('POST /manual-scan creates new product with manual data', async () => {
    setupSupabase([
      { data: null, error: null }, // No existing product
      {
        data: {
          id: 1,
          barcode: '123',
          name: 'Test Product',
          contents_size_weight: '500ml',
          sds_url: 'http://sds.com/test.pdf',
        },
        error: null,
      },
    ]);

    const { searchWithManualData } = require('../server/utils/scraper');
    (searchWithManualData as jest.Mock).mockResolvedValue({
      name: 'Test Product',
      contents_size_weight: '500ml',
      sdsUrl: 'http://sds.com/test.pdf',
    });

    const app = (await import('../server/app')).default;
    const res = await request(app).post('/manual-scan').send({
      code: '123',
      name: 'Test Product',
      size: '500ml',
    });

    expect(res.status).toBe(200);
    expect(res.body.isManualEntry).toBe(true);
    expect(res.body.product.name).toBe('Test Product');
    expect(res.body.product.contents_size_weight).toBe('500ml');
    expect(res.body.message).toBe('Product created from manual entry');
  });

  test('POST /manual-scan updates existing product with manual data', async () => {
    setupSupabase([
      {
        data: {
          id: 1,
          barcode: '123',
          name: null,
          contents_size_weight: null,
          sds_url: null,
        },
        error: null,
      },
      {
        data: {
          id: 1,
          barcode: '123',
          name: 'Test Product',
          contents_size_weight: '500ml',
          sds_url: 'http://sds.com/test.pdf',
        },
        error: null,
      },
    ]);

    const { searchWithManualData } = require('../server/utils/scraper');
    (searchWithManualData as jest.Mock).mockResolvedValue({
      name: 'Test Product',
      contents_size_weight: '500ml',
      sdsUrl: 'http://sds.com/test.pdf',
    });

    const app = (await import('../server/app')).default;
    const res = await request(app).post('/manual-scan').send({
      code: '123',
      name: 'Test Product',
      size: '500ml',
    });

    expect(res.status).toBe(200);
    expect(res.body.updated).toBe(true);
    expect(res.body.message).toBe('Product updated with manual entry data');
  });
});

describe('Original Scan Endpoint', () => {
  test('POST /scan returns 403 without code', async () => {
    const app = (await import('../server/app')).default;
    const res = await request(app).post('/scan').send({});
    expect(res.status).toBe(403);
  });

  test('POST /scan with manual data uses provided name and size', async () => {
    setupSupabase([
      { data: null, error: null }, // No existing product
      {
        data: {
          id: 1,
          barcode: '123',
          name: 'Manual Product',
          contents_size_weight: '250ml',
          sds_url: 'http://sds.com/manual.pdf',
        },
        error: null,
      },
    ]);

    const { searchWithManualData } = require('../server/utils/scraper');
    (searchWithManualData as jest.Mock).mockResolvedValue({
      name: 'Manual Product',
      contents_size_weight: '250ml',
      sdsUrl: 'http://sds.com/manual.pdf',
    });

    const app = (await import('../server/app')).default;
    const res = await request(app).post('/scan').send({
      code: '123',
      name: 'Manual Product',
      size: '250ml',
    });

    expect(res.status).toBe(200);
    expect(res.body.isManualEntry).toBe(true);
    expect(res.body.product.name).toBe('Manual Product');
    expect(res.body.message).toBe('Product created from manual entry');
  });

  test('POST /scan returns existing product and updates SDS', async () => {
    setupSupabase([
      {
        data: { barcode: '123', name: 'Test', contents_size_weight: '50ml', sds_url: null },
        error: null,
      },
      {
        data: {
          barcode: '123',
          name: 'Test',
          contents_size_weight: '50ml',
          sds_url: 'http://sds.com/test.pdf',
        },
        error: null,
      },
    ]);
    const { fetchSdsByName } = require('../server/utils/scraper');
    (fetchSdsByName as jest.Mock).mockResolvedValue({
      sdsUrl: 'http://sds.com/test.pdf',
      topLinks: [],
    });
    const app = (await import('../server/app')).default;

    const res = await request(app).post('/scan').send({ code: '123' });

    expect(res.status).toBe(200);
    expect(res.body.product.sds_url).toBe('http://sds.com/test.pdf');
    expect(res.body.message).toBe('Product found in database');
  });

  test('POST /scan stores SDS when only PDF is found', async () => {
    setupSupabase([
      { data: null, error: null },
      {
        data: {
          id: 1,
          barcode: '123',
          name: null,
          contents_size_weight: null,
          sds_url: 'http://example.com/sds.pdf',
        },
        error: null,
      },
    ]);
    const { fetchBingLinks, scrapeProductInfo } = require('../server/utils/scraper');
    (fetchBingLinks as jest.Mock).mockResolvedValue(['http://example.com/sds.pdf']);
    (scrapeProductInfo as jest.Mock).mockResolvedValue({
      url: 'http://example.com/sds.pdf',
      name: '',
      contents_size_weight: '',
      sdsUrl: 'http://example.com/sds.pdf',
    });
    const app = (await import('../server/app')).default;
    const res = await request(app).post('/scan').send({ code: '123' });
    expect(res.status).toBe(200);
    expect(res.body.product.sds_url).toBe('http://example.com/sds.pdf');
    expect(res.body.product.name).toBeNull();
  });
});
