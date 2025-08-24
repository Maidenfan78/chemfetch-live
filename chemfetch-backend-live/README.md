# 🚀 ChemFetch Backend

**Node.js + Express API server** with integrated Python OCR microservice for the ChemFetch chemical management platform.

This backend powers the mobile app (barcode scanning & OCR) and web client hub (chemical register management). It handles product discovery, web scraping, SDS parsing, and OCR processing through a combination of Node.js APIs and Python microservices.

---

## 🚀 Tech Stack

### Backend Framework

- **Node.js** with **Express 5** for API server
- **TypeScript** for type safety and development experience
- **ES Modules** for modern JavaScript module system

### Database & Authentication

- **Supabase** for PostgreSQL database and authentication
- **Row Level Security** for multi-tenant data isolation
- **Service Role** for backend database operations

### External Services Integration

- **Puppeteer** with Stealth plugin for web scraping
- **Cheerio** for HTML parsing and data extraction
- **Sharp** for image processing
- **Axios** for HTTP requests

### Development & Quality

- **ESLint 9** for code linting
- **Prettier** for code formatting
- **Jest** with ts-jest for testing
- **TSX** for TypeScript execution
- **Pino** for structured logging

### Security & Performance

- **CORS** configuration for cross-origin requests
- **Express Rate Limit** for API protection
- **Security Headers** (XSS, content-type, frame options)
- **Request timeout handling** for long-running operations

### Python Microservice

- **Python OCR Service** for text extraction and SDS parsing
- **Docker Compose** for multi-service orchestration
- **HTTP Proxy Middleware** for seamless OCR integration

---

## ⚙️ Setup & Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Server Configuration
PORT=3001

# Supabase Configuration
SB_URL=https://your-project.supabase.co
SB_SERVICE_KEY=your-service-role-key

# OCR Service Configuration
EXPO_PUBLIC_OCR_API_URL=http://127.0.0.1:5001

# Google Search API (for SDS discovery)
GOOGLE_SEARCH_API_KEY=your-google-api-key
GOOGLE_SEARCH_ENGINE_ID=your-search-engine-id
```

### Installation & Development

```bash
# Install dependencies
npm install

# Development server
npm run dev

# Production build
npm run build
npm start

# Utility scripts
npm run process-existing-sds    # Process pending SDS documents
npm run reprocess-all-sds      # Force reprocess all SDS
npm run force-reprocess-sds    # Force reprocess specific SDS
npm run collect-logs           # Collect application logs
npm run view-logs              # View collected logs

# Code quality
npm run lint
npm run lint:fix
npm run format
npm run format:check
npm run type-check

# Testing
npm test
```

### Docker Development

```bash
# Build and run both backend and OCR service
docker-compose up --build

# Backend will be available on port 3001
# OCR service runs internally on port 5001
```

---

## 🎯 Core Features

### API Endpoints

| Endpoint                | Method | Purpose                                            | Response Time   |
| ----------------------- | ------ | -------------------------------------------------- | --------------- |
| `/scan`                 | POST   | Barcode lookup with web scraping fallback          | ~2-5 seconds    |
| `/manual-scan`          | POST   | Direct product entry with name, size, and barcode  | ~1-3 seconds    |
| `/confirm`              | POST   | Save OCR-confirmed product data                    | ~200ms          |
| `/sds-by-name`          | POST   | Find Safety Data Sheet URLs via intelligent search | ~3-8 seconds    |
| `/parse-sds`            | POST   | Extract structured metadata from SDS PDFs          | ~30-120 seconds |
| `/parse-sds/batch`      | POST   | Batch process multiple SDS documents               | Variable        |
| `/parse-sds/status/:id` | GET    | Check SDS parsing status for a product             | ~100ms          |
| `/verify-sds`           | POST   | Validate SDS document relevance                    | ~30 seconds     |
| `/ocr`                  | POST   | Process images for text extraction (proxied)       | ~2-5 seconds    |
| `/health`               | GET    | API health check                                   | ~50ms           |
| `/sds-trigger`          | POST   | Trigger SDS processing for products                | ~200ms          |

### Key Capabilities

- **Australian-Focused Scraping**: Prioritizes `.com.au` domains and local retailers
- **Intelligent SDS Discovery**: Multiple search strategies including blob storage detection
- **Manual Entry Support**: Direct product entry without requiring web scraping
- **Duplicate Detection**: Prevents duplicate watchlist entries for users
- **Auto-SDS Parsing**: Automatic background SDS processing for new products
- **Race Condition Protection**: Robust handling of long-running processes
- **Rate Limiting**: Prevents abuse with configurable limits (60 requests/hour)
- **Timeout Management**: Graceful handling of slow external services (5-minute SDS timeout)
- **Structured Logging**: Comprehensive request/response logging with Pino
- **OCR Proxy**: Seamless integration with Python OCR microservice
- **Batch Processing**: Sequential SDS processing to avoid system overload

---

## 🔍 API Documentation

### Barcode Scanning

**POST /scan** - Traditional barcode lookup

```http
POST /scan
Content-Type: application/json

{
  "code": "044600069913"
}
```

**POST /manual-scan** - Direct product entry (bypasses web scraping)

```http
POST /manual-scan
Content-Type: application/json

{
  "code": "044600069913",
  "name": "Isocol Rubbing Alcohol",
  "size": "75mL",
  "userId": "optional-user-id"
}
```

**Response (scan endpoint):**

```json
{
  "code": "044600069913",
  "product": {
    "id": 123,
    "barcode": "044600069913",
    "name": "Isocol Rubbing Alcohol",
    "contents_size_weight": "75mL",
    "sds_url": "https://example.com/sds.pdf"
  },
  "scraped": [
    {
      "url": "https://example.com/product-page",
      "name": "Isocol Rubbing Alcohol",
      "size": "75mL",
      "sdsUrl": "https://example.com/sds.pdf"
    }
  ],
  "existingInDatabase": false,
  "message": "Product found via web search"
}
```

**Response (manual-scan endpoint):**

```json
{
  "code": "044600069913",
  "product": {
    "id": 123,
    "barcode": "044600069913",
    "name": "Isocol Rubbing Alcohol",
    "contents_size_weight": "75mL",
    "sds_url": "https://example.com/sds.pdf"
  },
  "isManualEntry": true,
  "message": "Product created from manual entry"
}
```

**Key Differences:**

- `/scan`: Requires only barcode, performs web scraping to find product details
- `/manual-scan`: Requires barcode, name, and size; skips web scraping and uses provided data directly
- `/manual-scan`: Optimized for manual entry workflow where user already knows product details
- Both endpoints support `userId` parameter for watchlist management
- Both endpoints include duplicate detection to prevent duplicate watchlist entries
- Auto-triggers SDS parsing when SDS URLs are found

### Additional API Features

**POST /confirm** - Save OCR-confirmed product data

```json
{
  "code": "1234567890",
  "name": "Chemical Name",
  "size": "500mL"
}
```

**POST /sds-trigger** - Trigger SDS processing

```json
{
  "product_id": 123
}
```

**GET /parse-sds/status/:product_id** - Check parsing status

```json
{
  "success": true,
  "product_id": 123,
  "has_metadata": true,
  "metadata": { ... }
}
```

---

## 📚 API Rate Limits

**Global Rate Limit**: 60 requests per minute (applied to all endpoints)

| Endpoint       | Additional Limits | Notes                     |
| -------------- | ----------------- | ------------------------- |
| `/scan`        | None              | Protected by global limit |
| `/manual-scan` | None              | Protected by global limit |
| `/parse-sds`   | 5-minute timeout  | Resource intensive        |
| `/ocr`         | Proxied to Python | Dependent on OCR service  |
| `/verify-sds`  | 5-minute timeout  | External requests         |
| `/health`      | None              | Monitoring endpoint       |

---

## 🔄 Recent Updates

### Version 2025.01

**New Features:**

- ✅ Manual product entry endpoint (`/manual-scan`)
- ✅ Enhanced mobile app manual entry workflow
- ✅ Direct SDS search for manual entries
- ✅ Improved validation for name and size fields
- ✅ Comprehensive test coverage for manual entry

### Version 2024.12

**New Features:**

- ✅ SDS metadata parsing with vendor information
- ✅ Batch SDS processing capabilities
- ✅ Enhanced PDF verification with size limits
- ✅ Timeout protection for long-running operations
- ✅ Race condition fixes for concurrent requests

**Performance Improvements:**

- 🚀 SDS verification reduced from 6+ minutes to ~30 seconds
- 🚀 Stream processing for large PDF files
- 🚀 Smart caching for repeated scraping requests
- 🚀 Australian-focused search optimization

**Bug Fixes:**

- 🔧 Fixed "ERR_HTTP_HEADERS_SENT" race conditions
- 🔧 Improved client disconnect handling
- 🔧 Enhanced error messages for timeout scenarios
- 🔧 Better memory management for PDF processing
