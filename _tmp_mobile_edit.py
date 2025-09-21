from pathlib import Path

path = Path(chemfetch-mobile-live/app/barcode.tsx)
text = path.read_text()

old =           const requestTime = Date.now() - requestStart;\n          mobileLogger.info('BARCODE_SCAN', `Backend response received`, {\n            barcode: confirmed,\n            requestTime,\n            alreadyInWatchlist: json.alreadyInWatchlist,\n            existingInDatabase: json.existingInDatabase,\n          });\n

new =           const requestTime = Date.now() - requestStart;\n          const scrapedItems = Array.isArray(json.scraped) ? (json.scraped as any[]) : [];\n          const scrapedSummary = scrapedItems.slice(0, 3).map(item => ({\n            name: item?.name || item?.product_name || '',\n            size: item?.contents_size_weight || item?.size || '',\n            hasSds: Boolean(item?.sdsUrl || item?.sds_url),\n            url: item?.url || '',\n          }));\n          const bestProduct = json.product ?? scrapedItems[0] ?? null;\n          mobileLogger.info('BARCODE_SCAN', `Backend response received`, {\n            barcode: confirmed,\n            requestTime,\n            alreadyInWatchlist: json.alreadyInWatchlist,\n            existingInDatabase: json.existingInDatabase,\n            scrapedCount: scrapedItems.length,\n            scrapedSample: scrapedSummary,\n            bestMatch: bestProduct\n              ? {\n                  name: bestProduct.name || bestProduct.product_name || '',\n                  size: bestProduct.contents_size_weight || bestProduct.size || '',\n                  hasSds: Boolean(bestProduct.sdsUrl || bestProduct.sds_url),\n                }\n              : undefined,\n          });\n

if old not in text:
 raise SystemExit('old block not found')

path.write_text(text.replace(old, new, 1))
