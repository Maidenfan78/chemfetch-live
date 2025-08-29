# 🧪 ChemFetch Platform

**Complete chemical safety management solution** for businesses, laboratories, and industrial facilities. ChemFetch provides barcode scanning, OCR recognition, Safety Data Sheet management, and regulatory compliance tools across mobile, web, and backend services.

The platform streamlines chemical inventory management, automates SDS discovery and parsing, and ensures compliance with workplace safety regulations through an integrated suite of applications.

---

## 🏗️ Platform Architecture

ChemFetch is built as a modern microservices architecture with separate frontend clients connecting to a unified backend API and database:

```
┌─────────────────┬─────────────────┬─────────────────┐
│   Mobile App    │  Web Dashboard  │  Web Dashboard  │
│  (React Native) │   (Development) │   (Production)  │
│                 │   (Next.js)     │  (chemfetch.com)│
├─────────────────┴─────────────────┴─────────────────┤
│              Backend API (Node.js + Express)        │
├─────────────────┬─────────────────┬─────────────────┤
│  OCR Service    │   Database      │   External APIs │
│  (Python)       │   (Supabase)    │   (Google, etc) │
└─────────────────┴─────────────────┴─────────────────┘
```

---

## 📁 Project Structure

### [`chemfetch-mobile-live/`](./chemfetch-mobile-live)
**React Native mobile app** for field workers and safety personnel (**Currently in Android closed testing**)
- **Technology**: Expo 53, React Native 0.79, TypeScript
- **Features**: Barcode scanning, manual entry, chemical register access
- **Platforms**: Android (closed testing), Web (via Expo) - iOS version planned for future release
- **Access**: Contact support@chemfetch.com for testing program invitation
- **Key Capabilities**: 
  - Multi-format barcode scanning (EAN, UPC, ITF-14, Code128)
  - GTIN normalization and validation
  - Duplicate detection for user watchlists
  - Offline-ready workflows with sync capabilities

### [`chemfetch-client-hub-live/`](./chemfetch-client-hub-live)
**Next.js web dashboard** for chemical safety officers and facility managers
- **Technology**: Next.js 15, React 19, TypeScript, Tailwind CSS 4
- **Features**: Chemical register management, SDS viewing, compliance reporting
- **Target Users**: Safety officers, facility managers, compliance teams
- **Key Capabilities**:
  - Comprehensive chemical inventory management
  - Inline editing of chemical data
  - SDS status tracking with expiration alerts
  - Dangerous goods classification descriptions

### [`chemfetch-backend-live/`](./chemfetch-backend-live)
**Node.js API server** with integrated Python OCR microservice
- **Technology**: Node.js, Express 5, TypeScript, Puppeteer, Python
- **Features**: Product discovery, web scraping, SDS parsing, OCR processing
- **Architecture**: RESTful API with Python microservice integration
- **Key Capabilities**:
  - Australian-focused web scraping for product data
  - Intelligent SDS discovery and verification
  - Automated SDS metadata extraction and parsing
  - Rate limiting and security protections

### [`chemfetch-supabase-live/`](./chemfetch-supabase-live)
**Database schema and migrations** for the ChemFetch platform
- **Technology**: PostgreSQL via Supabase, SQL migrations, TypeScript types
- **Features**: Multi-tenant database design with Row Level Security
- **Core Tables**: Products, user watchlists, SDS metadata, authentication
- **Key Capabilities**:
  - Comprehensive chemical data modeling
  - User-isolated data with RLS policies
  - Structured SDS metadata storage
  - Performance-optimized indexing

### [`chemfetch.com/`](./chemfetch.com)
**Production website** hosting the ChemFetch Client Hub
- **Technology**: [To be documented - check folder contents]
- **Purpose**: Production deployment of the web dashboard for end users
- **Target Users**: Chemical safety officers, facility managers, compliance teams
- **Features**: Same as chemfetch-client-hub-live but deployed for production use

---

## 🚀 Getting Started

### Quick Start (Full Stack)

1. **Set up the database**:
   ```bash
   cd chemfetch-supabase-live
   npm install
   supabase init
   supabase link --project-ref your-project-ref
   supabase db push
   ```

2. **Start the backend**:
   ```bash
   cd chemfetch-backend-live
   npm install
   npm run dev
   # Backend runs on http://localhost:3001
   ```

3. **Start the web client (development)**:
   ```bash
   cd chemfetch-client-hub-live
   npm install
   npm run dev
   # Development dashboard runs on http://localhost:3001
   ```

   *Note: For production, users access the same dashboard via chemfetch.com*

4. **Start the mobile app**:
   ```bash
   cd chemfetch-mobile-live
   npm install
   npx expo start
   # Scan QR code with Expo Go or run in simulator
   ```

### Environment Configuration

Each service requires its own environment configuration:

- **Database**: Supabase project URL and service keys
- **Backend**: Database credentials, Google API keys for search
- **Web Client**: Supabase credentials, backend API URL
- **Mobile App**: Supabase credentials, backend API URL with smart host detection

See individual README files for detailed environment setup instructions.

---

## 🎯 Core User Workflows

### For Field Workers (Mobile App)
1. **Scan barcode** of chemical product using mobile camera
2. **Confirm product details** from web-scraped or manual entry data
3. **Auto-discover SDS** through intelligent search algorithms
4. **Add to register** with automatic watchlist management

### For Safety Officers (Web Dashboard - chemfetch.com)
1. **View chemical register** with comprehensive product information
2. **Manage SDS documents** with status tracking and expiration alerts
3. **Edit chemical data** using inline editing for quantities and locations
4. **Monitor compliance** with dangerous goods classifications and risk assessments

### For System Administrators (Backend)
1. **Batch process SDS** documents for multiple products
2. **Monitor API performance** through structured logging
3. **Manage product database** with automated web scraping
4. **Configure rate limits** and security policies

---

## 🔧 Technology Highlights

### Database Design
- **Multi-tenant architecture** with Row Level Security
- **Comprehensive chemical modeling** including hazard classifications
- **Optimized indexing** for fast queries and data retrieval
- **Type-safe operations** with generated TypeScript types

### Backend Services
- **Microservice architecture** with Node.js API and Python OCR service
- **Intelligent web scraping** prioritizing Australian retailers and suppliers
- **Robust error handling** with timeout management and race condition protection
- **Comprehensive logging** with Pino for production monitoring

### Frontend Applications
- **Mobile-first design** optimized for industrial environments
- **Real-time updates** with Supabase subscriptions
- **Android platform support** (iOS version planned for future release)
- **Modern UI frameworks** with Tailwind CSS and shadcn/ui components

---

## 📊 Platform Capabilities

### Chemical Management
- **Product Discovery**: Automated web scraping for Australian chemical products
- **Barcode Support**: EAN-8/13, UPC-A/E, ITF-14, Code128/39/93 formats
- **SDS Integration**: Intelligent Safety Data Sheet discovery and parsing
- **Inventory Tracking**: Multi-location chemical register management

### Safety & Compliance
- **Hazard Classification**: Dangerous goods class descriptions and requirements
- **Risk Assessment**: Consequence, likelihood, and risk rating management
- **SDS Monitoring**: Issue date tracking with expiration alerts
- **Regulatory Support**: Australian workplace safety compliance features

### Performance & Scale
- **Sub-5 second scanning**: Optimized barcode processing and product lookup
- **95%+ OCR accuracy**: Advanced text recognition for product labels
- **Concurrent processing**: Batch SDS parsing with queue management
- **Smart caching**: Reduced redundant web scraping and API calls

---

## 🛠️ Development

### Prerequisites
- **Node.js 18+** for all JavaScript/TypeScript services
- **Python 3.8+** for OCR and SDS parsing services
- **Supabase account** for database and authentication
- **Google API credentials** for enhanced product search

### Code Quality
All projects include comprehensive development tooling:
- **ESLint** for code linting with TypeScript support
- **Prettier** for consistent code formatting
- **TypeScript** for type safety across the platform
- **Jest** for unit testing (where applicable)
- **Husky** for git hooks and pre-commit checks

### Development Workflow
1. Set up database schema and migrations
2. Start backend API server with OCR service
3. Launch web client for dashboard access
4. Run mobile app for field testing
5. Use integrated logging for debugging and monitoring

---

## 🔐 Security & Privacy

### Data Protection
- **Row Level Security** ensures users only access their own data
- **Service role isolation** for backend operations
- **Encrypted authentication** with Supabase Auth
- **Secure API endpoints** with rate limiting and input validation

### Compliance Features
- **GDPR considerations** for user data handling
- **Workplace safety standards** compliance tools
- **Audit trails** for chemical register changes
- **Data export capabilities** for regulatory reporting

---

## 📄 License

This project is proprietary software. All rights reserved.

---

## 👥 Support & Documentation

### Getting Help
- **Technical Issues**: Check individual project README files for troubleshooting
- **API Documentation**: Refer to backend README for endpoint specifications
- **Database Schema**: See Supabase README for table structures and queries
- **Mobile Development**: Check mobile README for Expo and React Native setup

### Additional Resources
- `GOOGLE_SEARCH_SETUP.md` - Google API configuration for SDS discovery
- `LOGGING_SETUP.md` - Production logging configuration
- `DEVELOPMENT.md` - Detailed development environment setup
- `PRIVACY_POLICY.md` - Privacy policy for mobile app distribution

---

## 🗺️ Roadmap

### Q1 2025
- **Enhanced mobile features** with push notifications and bulk scanning
- **Advanced web reporting** with analytics dashboard
- **Database optimizations** with audit tables and partitioning
- **API improvements** with enhanced rate limiting and caching

### Q2 2025
- **iOS mobile app release** with full feature parity
- **Multi-organization support** with enterprise features
- **International expansion** with localization for different markets
- **AR integration** for mobile chemical identification
- **Advanced analytics** with reporting and compliance dashboards

---

*ChemFetch Platform - Streamlining chemical safety management for the modern workplace*
