# ChemFetch Backend API - Agent Instructions

## Project Overview
Node.js/Express API server serving the ChemFetch platform with integrated Python OCR microservice.
Core responsibilities: product discovery, web scraping, SDS management, and chemical data processing.

## Setup Commands
- Install dependencies: `npm install`
- Start development server: `npm run dev` (uses tsx for TypeScript execution)
- Build for production: `npm run build`
- Start production: `npm start`
- Run tests: `npm test`
- Process existing SDS files: `npm run process-existing-sds`

## Development Environment
- **Runtime**: Node.js with Express 5
- **TypeScript**: Strict mode with ES modules
- **Database**: Supabase PostgreSQL client
- **OCR Service**: Python Flask microservice (port 5000)
- **Web Scraping**: Puppeteer with stealth plugin
- **Logging**: Pino with structured JSON logging

## Project Structure
```
server/
├── index.ts          # Main application entry point
├── app.ts           # Express app configuration
├── routes/          # API endpoint handlers
│   ├── verifySds.ts    # SDS verification proxy
│   ├── parseSds.ts     # SDS parsing with metadata
│   ├── parseSDSEnhanced.ts # Enhanced SDS processing
│   └── [other routes]
└── utils/           # Shared utilities

ocr_service/         # Python microservice
├── ocr_service.py   # Flask app with PDF processing
├── parse_sds.py     # CLI parser for metadata extraction
├── quick_parser.py  # Lightweight regex-based parser
└── sds_parser_new/  # Primary SDS extraction system
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
1. **Verification**: `/verify-sds` endpoint checks if PDF is valid SDS
2. **Text Extraction**: Multi-method approach (direct text, OCR fallback)
3. **Parsing**: Layered parsing system with primary/fallback parsers
4. **Metadata Extraction**: Chemical properties, hazard classifications
5. **Database Storage**: Structured SDS data with user associations

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
