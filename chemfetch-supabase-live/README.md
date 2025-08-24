# 🗄️ ChemFetch Supabase Schema

Database schema, migrations, and configuration for the ChemFetch chemical management platform. This
repository contains all SQL migrations, Row Level Security policies, and database type definitions.

---

## 🛠️ Development Setup

**For detailed development setup, linting, and code quality information, see
[DEVELOPMENT.md](./DEVELOPMENT.md)**

### Quick Start

```bash
# Install dependencies
npm install

# Run all quality checks
npm run check-all

# Fix formatting and linting issues
npm run fix-all
```

### Code Quality Tools

This project includes comprehensive linting and formatting:

- **ESLint** with TypeScript support
- **Prettier** for code formatting
- **Husky** git hooks
- **lint-staged** for pre-commit checks

---

## 📊 Database Overview

The ChemFetch platform uses PostgreSQL via Supabase to store chemical product information, user
inventories, and parsed Safety Data Sheet metadata. The schema is designed for multi-tenant usage
with strong data isolation and compliance features.

### Core Tables

- **`product`**: Master catalog of chemical products with barcode references
- **`user_chemical_watch_list`**: Per-user chemical inventories with safety information
- **`sds_metadata`**: Parsed Safety Data Sheet information with vendor and hazard data
- **`auth.users`**: Supabase managed user authentication

---

## 🏗️ Database Schema

### Products Table

```sql
CREATE TABLE product (
  id SERIAL PRIMARY KEY,
  barcode TEXT NOT NULL,
  product TEXT,
  contents_size_weight TEXT,
  sds_url TEXT,
  created_at TIMESTAMPTZ DEFAULT timezone('utc', now()),
  CONSTRAINT unique_barcode UNIQUE (barcode)
);
```

### User Chemical Watch List

```sql
CREATE TABLE user_chemical_watch_list (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  product_id INTEGER REFERENCES product(id) ON DELETE CASCADE,
  quantity_on_hand INTEGER,
  location TEXT,
  sds_available BOOLEAN,
  sds_issue_date DATE,
  hazardous_substance BOOLEAN,
  dangerous_good BOOLEAN,
  dangerous_goods_class TEXT,
  description TEXT,
  packing_group TEXT,
  subsidiary_risks TEXT,
  consequence TEXT,
  likelihood TEXT,
  risk_rating TEXT,
  swp_required BOOLEAN,
  comments_swp TEXT,
  created_at TIMESTAMPTZ DEFAULT timezone('utc', now()),

  -- Data validation constraints
  CONSTRAINT check_risk_rating CHECK (risk_rating IN ('Extreme', 'High', 'Medium', 'Low') OR risk_rating IS NULL),
  CONSTRAINT check_consequence CHECK (consequence IN ('Catastrophic', 'Major', 'Moderate', 'Minor', 'Insignificant') OR consequence IS NULL),
  CONSTRAINT check_likelihood CHECK (likelihood IN ('Almost Certain', 'Likely', 'Possible', 'Unlikely', 'Rare') OR likelihood IS NULL),
  CONSTRAINT check_packing_group CHECK (packing_group IN ('I', 'II', 'III') OR packing_group IS NULL)
);
```

### SDS Metadata Table

```sql
CREATE TABLE sds_metadata (
  product_id INTEGER PRIMARY KEY REFERENCES product(id) ON DELETE CASCADE,
  vendor TEXT,
  issue_date DATE,
  hazardous_substance BOOLEAN,
  dangerous_good BOOLEAN,
  dangerous_goods_class TEXT,
  description TEXT,
  packing_group TEXT,
  subsidiary_risks TEXT,
  raw_json JSONB,
  created_at TIMESTAMPTZ DEFAULT timezone('utc', now())
);
```

---

## 🔒 Row Level Security (RLS)

### Security Policies

```sql
-- Enable RLS
ALTER TABLE user_chemical_watch_list ENABLE ROW LEVEL SECURITY;

-- Users can view their own chemical records
CREATE POLICY "select_own_rows"
  ON user_chemical_watch_list FOR SELECT
  USING (auth.uid() = user_id);

-- Users can modify their own records
CREATE POLICY "modify_own_rows"
  ON user_chemical_watch_list FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Service role bypass for backend operations
CREATE POLICY "admin_access"
  ON user_chemical_watch_list FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
```

---

## ⚙️ Setup Instructions

### Prerequisites

- Supabase CLI installed: `npm install -g supabase`
- Supabase project created at [supabase.com](https://supabase.com)
- Database access credentials

### 1. Initialize Local Development

```bash
# Clone repository
git clone <repository-url>
cd chemfetch-supabase-live

# Install development dependencies
npm install

# Initialize Supabase
supabase init

# Link to your Supabase project
supabase link --project-ref your-project-ref
```

### 2. Apply Migrations

```bash
# Apply all migrations to remote database
supabase db push

# Or apply to local development database
supabase start
supabase db reset
```

### 3. Generate TypeScript Types

```bash
# Generate types from remote database
supabase gen types typescript --project-id your-project-id > supabase/database.types.ts

# Or generate from local database
supabase gen types typescript --local > supabase/database.types.ts
```

---

## 📈 Common Queries

### User Chemical Inventory

```sql
-- Get user's complete chemical inventory with SDS data
SELECT
  w.*,
  p.product as product_name,
  p.barcode,
  p.sds_url,
  s.vendor,
  s.issue_date,
  s.hazardous_substance,
  s.dangerous_good,
  s.dangerous_goods_class
FROM user_chemical_watch_list w
JOIN product p ON w.product_id = p.id
LEFT JOIN sds_metadata s ON p.id = s.product_id
WHERE w.user_id = $1;
```

### Hazardous Chemicals Report

```sql
-- Get all hazardous chemicals for compliance reporting
SELECT
  p.product,
  w.location,
  w.quantity_on_hand,
  s.dangerous_goods_class,
  s.packing_group,
  s.issue_date
FROM user_chemical_watch_list w
JOIN product p ON w.product_id = p.id
JOIN sds_metadata s ON p.id = s.product_id
WHERE w.user_id = $1
  AND (w.hazardous_substance = true OR w.dangerous_good = true)
ORDER BY s.dangerous_goods_class, p.product;
```

---

## 🔧 Configuration

### Environment Variables

```env
# Required for client applications
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# Required for backend services
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Local development
SUPABASE_LOCAL_URL=http://localhost:54321
SUPABASE_LOCAL_ANON_KEY=your-local-anon-key
```

---

## 🔄 Recent Updates

### Version 2024.12

**Schema Changes:**

- ✅ **Added SDS Metadata Table**: Structured storage for parsed Safety Data Sheet information
- ✅ **Vendor Field**: Added vendor tracking to SDS metadata
- ✅ **Enhanced Indexing**: Improved query performance with strategic indexes
- ✅ **RLS Policies**: Comprehensive Row Level Security implementation
- ✅ **JSON Support**: JSONB storage for complete SDS parsed data

**Development Improvements:**

- ✅ **Linting Setup**: ESLint with TypeScript support
- ✅ **Code Formatting**: Prettier with SQL support
- ✅ **Git Hooks**: Pre-commit linting and formatting
- ✅ **CI/CD**: GitHub Actions for quality checks
- ✅ **VS Code Integration**: Workspace settings and extensions

**Performance Improvements:**

- ⚡ **Optimized Queries**: Efficient joins for watchlist data retrieval
- ⚡ **Index Strategy**: Strategic indexing for common query patterns
- ⚡ **Connection Pooling**: Better database connection management

---

## 📄 License

This project is proprietary software. All rights reserved.

---

## 👥 Support

**Database Issues:**

- Check Supabase dashboard for error logs
- Verify RLS policies are correctly configured
- Test queries in SQL editor before implementing

**Migration Problems:**

- Always test migrations on staging environment first
- Keep backups before applying production migrations
- Use transaction blocks for complex schema changes

**Development Issues:**

- Run `npm run check-all` to identify problems
- Use `npm run fix-all` to auto-fix formatting and linting
- Check [DEVELOPMENT.md](./DEVELOPMENT.md) for detailed setup instructions

---

## 🗺️ Roadmap

### Q1 2025

- **Audit Tables**: Complete audit trail for all data changes
- **Partitioning**: Table partitioning for large-scale deployments
- **Advanced RLS**: More granular permission models

### Q2 2025

- **Multi-tenant Enhancements**: Organization-level data isolation
- **Reporting Views**: Materialized views for complex reporting
- **Data Validation**: Enhanced constraints and validation rules
