ChemFetch OCR Service

Purpose: Flask-based microservice that verifies and parses Safety Data Sheets (SDS) and exposes HTTP endpoints consumed by the Node backend.

Endpoints

- `/health`: Service status and environment info
- `/verify-sds` (POST): Verifies a PDF is an SDS; extracts text with multi-method fallback (OCR optional)
- `/parse-sds` (POST): Unified SDS parsing with layered fallbacks (primary parser → verification-based extraction → quick regex parser)
- `/parse-pdf-direct` (POST): Uses the new `sds_parser_new` extractor directly

Active Files

- `ocr_service.py`: Flask app, PDF text extraction utilities, endpoints
- `parse_sds.py`: CLI/parser used by Node route `server/routes/parseSds.ts`
- `quick_parser.py`: Lightweight regex-based enrichment used as a fallback
- `sds_parser_new/sds_extractor.py`: Primary extractor for direct parsing
- `requirements.txt`: Dependencies for Render/local installs
- `__init__.py`: Package marker

Removed Legacy Artifacts (clean-up)

- Alternative parsers and patch stubs: `simple_parser.py`, `working_parser.py`, `parse_sds_fixed.py`, `sds_parser_fixed.py`
- Duplicate Docker/requirements variants: `Dockerfile.ocr`, `Dockerfile.lightweight`, `requirements-*.txt`
- Redundant `render.yaml` (service is defined at `chemfetch-backend-live/render.yaml`)
- Compiled caches under `__pycache__/`

How Backend Uses This Service

- Proxy: `server/routes/verifySds.ts` forwards to `/verify-sds`
- Enhanced parsing: `server/routes/parseSDSEnhanced.ts` calls `/parse-pdf-direct` (default) or `/parse-sds`
- CLI integration: `server/routes/parseSds.ts` spawns `python ocr_service/parse_sds.py` for metadata generation

Deployment

- Render pserv builds from this folder using `requirements.txt` and starts with `gunicorn` as configured in `chemfetch-backend-live/render.yaml`.
