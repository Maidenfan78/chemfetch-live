# ChemFetch Backend API - Agent Instructions

## Project Overview

Node.js/Express API server for the ChemFetch platform with an integrated Python OCR microservice.
Core responsibilities: barcode/manual scanning, product discovery, SDS verification/parsing, and chemical data processing persisted to Supabase.

## Setup Commands

- Install dependencies: `npm install`
- Start development server: `npm run dev` (tsx + ESM)
- Build for production: `npm run build`
- Start production: `npm start`
- Run tests: `npm test`
- Process existing SDS files: `npm run process-existing-sds`

## Development Environment

- **Runtime**: Node.js with Express 5
- **TypeScript**: Strict mode with ES modules
- **Database**: Supabase PostgreSQL client
- **OCR Service**: Python Flask microservice (default port 5001)
- **Web Scraping**: Puppeteer with stealth plugin
- **Logging**: Pino with structured JSON logging

## Project Structure

```
server/
├── index.ts              # Server bootstrap + health endpoints
├── app.ts                # Express app config and route registration
├── routes/               # API endpoint handlers
│   ├── health.ts         # Basic health check
│   ├── scan.ts           # Barcode/URL scanning
│   ├── manualScan.ts     # Manual entry scanning
│   ├── sdsTrigger.ts     # Triggers SDS processing for products
│   ├── sdsByName.ts      # SDS lookup by name
│   ├── confirm.ts        # Confirmation flows for client
│   ├── verifySds.ts      # Proxy: forwards to Python /verify-sds
│   ├── parseSds.ts       # Parsing pipeline (verification/quick/primary)
│   ├── parseSDSEnhanced.ts # Enhanced SDS processing
│   └── batchSds.ts       # Batch SDS processing
└── utils/                # Logger and helpers

ocr_service/              # Python microservice
├── ocr_service.py        # Flask app + endpoints (/health, /verify-sds, /parse-sds, /parse-pdf-direct)
├── parse_sds.py          # CLI/primary parser wrapper
├── quick_parser.py       # Lightweight regex-based parser
└── sds_parser_new/       # Advanced SDS extraction system
```

## API Design Patterns

- **RESTful Endpoints**: Standard HTTP methods with meaningful URLs
- **Error Handling**: Consistent error responses with proper status codes
- **Rate Limiting**: Express rate limiter for API protection
- **CORS Configuration**: Proper cross-origin headers for frontend clients
- **Proxy Pattern**: Node.js proxying to Python OCR service
- **Timeout Management**: Request timeouts to prevent hanging operations

## Key Technologies

- **Express 5**: Latest Express with improved error handling
- **Supabase Client**: Type-safe database operations with RLS
- **Puppeteer**: Automated web scraping with stealth mode
- **Pino**: High-performance structured logging
- **Sharp**: Image processing for OCR optimization
- **Axios**: HTTP client for external API calls

## SDS Processing Workflow

1. **Verification**: `/verify-sds` proxies to Python to verify SDS and extract text
2. **Text Extraction**: Multi-method approach (direct text, OCR fallback)
3. **Parsing**: Layered parsing system with primary/fallback parsers
4. **Metadata Extraction**: Chemical properties, hazard classifications
5. **Database Storage**: Structured SDS data with user associations

## HTTP Endpoints (Express)

- `GET /health`: Backend health info
- `GET /ocr/health`: Quick check of OCR proxy target
- `POST /scan`: Scan a product/barcode to discover SDS
- `POST /manual-scan`: Manual entry scanning
- `POST /sds-trigger`: Trigger SDS acquisition/parsing for a product
- `POST /confirm`: Client confirmation flow
- `GET /sds-by-name`: Search SDS by name
- `POST /verify-sds`: Forwards to Python OCR service `/verify-sds`
- `POST /parse-sds`: Parsing pipeline (verification → quick → primary)
- `POST /parse-sds-enhanced`: Enhanced parsing route
- `POST /batch-sds`: Batch SDS processing

## Web Scraping Guidelines

- **Australian Focus**: Prioritize Australian retailers and suppliers
- **Rate Limiting**: Respect website robots.txt and rate limits
- **Stealth Mode**: Use puppeteer-extra-plugin-stealth
- **Error Recovery**: Graceful handling of failed scraping attempts
- **Data Validation**: Verify scraped product data before storage

## Database Integration

- **Type Safety**: Use generated TypeScript types from Supabase
- **RLS Policies**: Respect Row Level Security in all queries
- **Error Handling**: Proper error handling for database operations
- **Performance**: Optimize queries with appropriate indexes
- **Transactions**: Use database transactions for multi-table operations

## Testing Approach

- **Unit Tests**: Jest for individual functions and utilities
- **Integration Tests**: Supertest for API endpoint testing
- **OCR Testing**: Python scripts for SDS parsing validation
- **Performance Tests**: Measure SDS processing times (<5s target)
- **Manual Testing**: Use provided test scripts for validation

## Error Handling Standards

- **Structured Errors**: Consistent error response format
- **Logging**: Comprehensive error logging with context
- **Graceful Degradation**: Fallback mechanisms for external services
- **Timeout Protection**: Prevent hanging operations
- **User-Friendly Messages**: Clear error messages for frontend

## Performance Considerations

- **Concurrent Processing**: Handle multiple SDS parsing requests
- **Memory Management**: Efficient PDF processing to avoid OOM
- **Caching**: Cache web scraping results to reduce redundant requests
- **Database Optimization**: Efficient queries and connection pooling
- **OCR Service**: Optimize Python service memory usage (<512MB)

## Deployment Configuration

- **Environment Variables**: Proper .env configuration for all environments
- **Docker Support**: Containerized deployment with docker-compose
- **Health Checks**: Service health monitoring endpoints
- **Process Management**: PM2 or equivalent for production
- **Log Management**: Structured logging for production monitoring

Key env vars (backend):
- `PORT` (default 3001)
- `OCR_SERVICE_URL` (default `http://localhost:5001`)
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`

## Security Best Practices

- **Input Validation**: Validate all user inputs and file uploads
- **Rate Limiting**: Protect against abuse and DoS attacks
- **CORS**: Proper cross-origin configuration
- **Authentication**: Validate Supabase auth tokens
- **File Handling**: Secure PDF processing without arbitrary code execution

## Common Tasks

- **Add New API Route**: Create in `server/routes/`, update app.ts
- **Modify SDS Parser**: Update `ocr_service/sds_parser_new/`
- **Web Scraping**: Extend Puppeteer scripts in appropriate route files
- **Database Changes**: Update types and queries after schema changes
- **OCR Improvements**: Modify Python service in `ocr_service/`

## Documentation Update Policy

When code changes, update the accompanying docs/readme/instructions in the same PR to keep behavior in sync.

Primary documentation locations for this service:
- Backend overview: `chemfetch-backend-live/README.md`
- Backend agent guide (this file): `chemfetch-backend-live/AGENTS.md`
- Server specifics: `chemfetch-backend-live/server/AGENTS.md`
- OCR service docs: `chemfetch-backend-live/ocr_service/README.md`
- OCR agent guide: `chemfetch-backend-live/ocr_service/AGENTS.md`
- SDS parser guide: `chemfetch-backend-live/ocr_service/sds_parser_new/AGENTS.md`
- Deployment notes: `chemfetch-backend-live/fix_deployment.md`, `chemfetch-backend-live/render.yaml`
- Improvements summary: `chemfetch-backend-live/IMPROVEMENT_SUMMARY.md`
- OCR fix notes: `chemfetch-backend-live/OCR_FIX_APPLIED.md`
- Test data/results: `chemfetch-backend-live/test-data/`, `chemfetch-backend-live/test-data/sds_test_results.txt`

Cross‑service references you may also need to update:
- Root overview: `README.md`
- Database: `chemfetch-supabase-live/` (schema/migrations and docs within)
- Web client: `chemfetch-client-hub-live/README.md`
- Mobile app: `chemfetch-mobile-live/README.md`

## Conventions

- TypeScript strict: keep types accurate; avoid `any`.
- Linting: `npm run lint` (auto-fix: `npm run lint:fix`).
- Formatting: `npm run format:check` / `npm run format`.
- Type checks: `npm run type-check` before pushing.
- Logging: use `pino`/`pino-http` for structured logs; avoid `console.log` in routes and prefer the shared logger.
