# ChemFetch To-Do List

## 🌐 Client Hub
- [ ] Add download link for the app (Google Play)
- [ ] Add “Contact Support” option
- [ ] Show item size/contents in product description

## 🌍 ChemFetch.com (Website)
- [ ] Fix email link (use proper mailto:)
- [ ] Fix “Contact Us” page (use forms)
- [ ] Fix links to other ChemFetch platforms

## ⚙️ Backend

### OCR
- [ ] Improve SDS parser
- [ ] Add parsing for scanned pdf documents

### SDS Handling
- [ ] **Keep links as source of truth** (no default downloads)
- [ ] **Add offline cache (opt-in)**
  - [ ] Mobile: cache SDS when opened, allow “Pin for offline”
  - [ ] Web: use Service Worker for cached SDS
- [ ] **Freshness control**
  - [ ] Store metadata (version, ETag, date)
  - [ ] Check for updates on open or daily
- [ ] **Storage policy**
  - [ ] Limit cache size, auto-purge old items
  - [ ] Add “Clear cache” option in settings
- [ ] **Versioning & audit**
  - [ ] Immutable file paths per version
  - [ ] Log who accessed which version (online/offline)
- [ ] **Export pack**
  - [ ] One-click “Export SDS Pack” (zip + index.csv)
- [ ] **Security**
  - [ ] Cache inside sandbox, optional encryption
  - [ ] Clear naming convention if manual save 
