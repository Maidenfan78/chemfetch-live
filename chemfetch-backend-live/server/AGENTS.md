# ChemFetch Server - Agent Instructions

## Server Overview
Core Node.js/Express server module within the ChemFetch backend. Houses the main application logic, routing, and Express app configuration for the chemical safety management API.

## Setup Commands
- Start server: `npm run dev` (from parent backend directory)
- Build: `npm run build` (from parent backend directory) 
- Production: `npm start` (from parent backend directory)
- Test routes: Use provided test scripts in parent directory
- Type check: `npm run type-check` (from parent backend directory)

## Module Structure
```
server/
├── index.ts         # Application entry point and server startup
├── app.ts          # Express app configuration, middleware, routes
├── routes/         # API route handlers
│   ├── verifySds.ts      # SDS verification endpoint
│   ├── parseSds.ts       # SDS parsing with metadata
│   ├── parseSDSEnhanced.ts # Enhanced SDS processing
│   ├── productRoutes.ts  # Product CRUD operations
│   ├── userRoutes.ts     # User management endpoints
│   └── [additional routes]
└── utils/          # Server utilities and helpers
    ├── supabase.ts       # Database client configuration
    ├── logger.ts         # Pino logging setup
    └── [utility modules]
```

## Express App Configuration
- **Express 5**: Latest version with improved async support
- **Middleware Stack**: CORS, rate limiting, request parsing, logging
- **Error Handling**: Centralized error handling middleware
- **Security**: Rate limiting, input validation, CORS configuration
- **Logging**: Pino HTTP logger with request/response logging
- **Health Checks**: Service status endpoints for monitoring

## Routing Patterns
- **Modular Routes**: Separate route files by feature/resource
- **RESTful Design**: Standard HTTP methods and resource naming
- **Middleware Composition**: Reusable middleware for common functionality
- **Error Boundaries**: Consistent error handling across all routes
- **Input Validation**: Validate request parameters and body data
- **Response Standards**: Consistent JSON response structure

## Database Integration  
```typescript
// Supabase client with proper typing
import { createClient } from '@supabase/supabase-js'
import type { Database } from '../../../database.types'

const supabase = createClient<Database>(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)
```

## Key Route Categories

### SDS Processing Routes
- **`/verify-sds`**: Proxy to Python OCR service for SDS verification
- **`/parse-sds`**: CLI-based SDS parsing with metadata extraction  
- **`/parse-sds-enhanced`**: Advanced parsing using direct OCR service calls
- **Error Handling**: Timeout management, fallback parsing methods
- **Response Format**: Structured JSON with confidence scores

### Product Management Routes  
- **`/products`**: CRUD operations for chemical products
- **`/products/search`**: Product search with filtering capabilities
- **`/products/barcode/:code`**: Barcode-based product lookup
- **Web Scraping**: Integration with Puppeteer for product discovery
- **Data Validation**: Ensure data integrity before database storage

### User & Authentication Routes
- **Authentication**: Integration with Supabase Auth
- **User Profiles**: User preference and profile management
- **Watchlists**: User-specific chemical watchlist management
- **RLS Integration**: Respect Row Level Security policies

## Middleware Configuration
```typescript
// Standard middleware stack
app.use(cors(corsOptions))
app.use(rateLimit(rateLimitOptions))
app.use(express.json({ limit: '10mb' }))
app.use(express.urlencoded({ extended: true }))
app.use(pinoHttp(loggerOptions))
```

## Error Handling Strategy
- **Centralized Handler**: Express error handling middleware
- **Structured Errors**: Consistent error response format
- **Status Codes**: Appropriate HTTP status codes for different errors
- **Logging**: Comprehensive error logging with stack traces
- **User Messages**: Clean error messages for frontend applications
- **Graceful Degradation**: Fallback mechanisms when services are unavailable

## Performance Considerations
- **Async/Await**: Proper async handling for all database and external API calls
- **Connection Pooling**: Efficient database connection management
- **Request Timeouts**: Prevent hanging requests with appropriate timeouts
- **Memory Management**: Efficient handling of large file uploads and processing
- **Caching**: Strategic caching of frequently accessed data

## OCR Service Integration
- **Proxy Pattern**: Route requests to Python Flask OCR service
- **Health Monitoring**: Check OCR service availability before routing
- **Timeout Management**: Handle OCR service timeouts gracefully
- **Error Translation**: Convert Python service errors to consistent API responses
- **Load Balancing**: Distribute OCR requests efficiently

## Web Scraping Implementation
- **Puppeteer Configuration**: Headless browser automation for product discovery
- **Stealth Mode**: Use stealth plugin to avoid bot detection
- **Rate Limiting**: Respect target website rate limits and robots.txt
- **Data Extraction**: Robust selectors and fallback strategies
- **Error Recovery**: Handle failed scraping attempts gracefully

## Security Implementation
- **Input Validation**: Sanitize all user inputs and file uploads
- **Authentication**: Validate Supabase JWT tokens on protected routes
- **Authorization**: Check user permissions with RLS policies
- **Rate Limiting**: Protect against abuse with configurable limits
- **CORS Policy**: Proper cross-origin resource sharing configuration

## Logging & Monitoring
```typescript
// Structured logging with Pino
import pino from 'pino'

const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  transport: {
    target: 'pino-pretty',
    options: { colorize: true }
  }
})
```

## Environment Configuration
- **Database**: Supabase URL and service role key
- **OCR Service**: Python service URL and health check endpoint
- **Google APIs**: Search API key for enhanced product discovery
- **Rate Limits**: Configurable request limits per IP/user
- **CORS**: Allowed origins for frontend applications

## Development Workflow
1. **Route Creation**: Add new route file in `routes/` directory
2. **Middleware Setup**: Configure route-specific middleware as needed
3. **Database Integration**: Use typed Supabase client for data operations
4. **Error Handling**: Implement proper error handling and logging
5. **Testing**: Test endpoints with provided scripts and tools
6. **Documentation**: Update API documentation for new endpoints

## Common Patterns
```typescript
// Standard route structure
export default async (req: Request, res: Response) => {
  try {
    // Input validation
    const { param1, param2 } = req.body
    if (!param1) {
      return res.status(400).json({ error: 'Missing required parameter' })
    }

    // Business logic
    const result = await processData(param1, param2)

    // Success response
    res.json({ success: true, data: result })
  } catch (error) {
    logger.error({ error, route: req.path }, 'Route error')
    res.status(500).json({ error: 'Internal server error' })
  }
}
```

## Database Query Patterns
```typescript
// Type-safe Supabase queries
const { data, error } = await supabase
  .from('products')
  .select('*')
  .eq('user_id', userId)
  .order('created_at', { ascending: false })

if (error) {
  throw new Error(`Database error: ${error.message}`)
}
```

## Testing Guidelines
- **Unit Tests**: Test individual route handlers with mocked dependencies
- **Integration Tests**: Test full request/response cycle with test database
- **API Tests**: Use supertest for HTTP endpoint testing
- **Error Scenarios**: Test error handling and edge cases
- **Performance Tests**: Measure response times under load

## Deployment Considerations
- **Process Management**: Use PM2 or similar for production deployment
- **Health Checks**: Implement health check endpoints for monitoring
- **Graceful Shutdown**: Handle SIGTERM signals for clean shutdowns
- **Environment Validation**: Validate required environment variables at startup
- **Docker Support**: Container-ready configuration for deployment
