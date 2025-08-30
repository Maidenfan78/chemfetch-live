# ChemFetch Platform - Agent Instructions

## Project Overview
ChemFetch is a comprehensive chemical safety management platform with microservices architecture:
- **Frontend**: Next.js web dashboard and React Native mobile app  
- **Backend**: Node.js/Express API server with Python OCR microservice
- **Database**: PostgreSQL via Supabase with Row Level Security
- **Key Features**: Barcode scanning, SDS parsing/management, regulatory compliance

## Setup Commands
- Install root dependencies: `npm install` (if package.json exists in project root)
- Set up database: `cd chemfetch-supabase-live && npm install && supabase db push`
- Start backend: `cd chemfetch-backend-live && npm install && npm run dev`
- Start web client: `cd chemfetch-client-hub-live && npm install && npm run dev`
- Start mobile app: `cd chemfetch-mobile-live && npm install && npx expo start`

## Architecture Patterns
- **Microservices**: Separate Node.js API and Python OCR service
- **Multi-tenant**: Database design with Row Level Security policies
- **Type Safety**: TypeScript across all JavaScript/Node.js components
- **Error Handling**: Comprehensive logging with Pino, timeout management
- **API Design**: RESTful endpoints with Express.js routing

## Code Style & Standards
- **TypeScript**: Strict mode enabled across all TS/JS projects
- **Linting**: ESLint with consistent configuration
- **Formatting**: Prettier with shared configuration
- **Python**: PEP 8 standards for OCR service components
- **Database**: SQL with type-safe operations via Supabase client
- **Naming**: camelCase for JS/TS, snake_case for Python and database

## Environment & Configuration  
- Each service requires separate `.env` configuration
- Database: Supabase project URL, service keys, RLS policies
- Backend: Google API keys, rate limiting, CORS settings
- Frontend: Supabase credentials, API URLs with environment detection
- OCR Service: Flask configuration, PDF processing libraries

## Testing Strategy
- **Unit Tests**: Jest for JavaScript/TypeScript components  
- **Integration**: API endpoint testing with supertest
- **Manual Testing**: Python scripts for OCR service validation
- **E2E**: Mobile app testing through Expo development build
- **Performance**: SDS parsing accuracy and processing speed benchmarks

## Development Workflow
1. **Database First**: Update schema and migrations in `chemfetch-supabase-live/`
2. **Backend API**: Implement endpoints in `chemfetch-backend-live/server/routes/`
3. **OCR Processing**: Python services in `chemfetch-backend-live/ocr_service/`
4. **Frontend**: Web dashboard features in `chemfetch-client-hub-live/src/`
5. **Mobile**: React Native features in `chemfetch-mobile-live/`
6. **Testing**: Validate across all layers before committing

## Security Considerations
- **Authentication**: Supabase Auth with RLS policies
- **API Security**: Rate limiting, input validation, CORS
- **Data Privacy**: User data isolation, audit trails
- **OCR Security**: Sandboxed Python service, file validation

## Performance Optimization
- **SDS Processing**: <5 second target for parsing and extraction
- **Database**: Optimized indexing, query performance monitoring
- **API**: Request caching, concurrent processing support
- **Mobile**: Offline capabilities, efficient barcode scanning

## Key Files to Understand
- `README.md`: Platform overview and getting started guide
- `chemfetch-supabase-live/`: Database schema and migrations
- `chemfetch-backend-live/server/`: API routes and business logic
- `chemfetch-backend-live/ocr_service/`: SDS parsing and OCR processing
- `chemfetch-client-hub-live/src/`: Web dashboard components
