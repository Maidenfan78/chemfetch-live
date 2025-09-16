import { fetchBingLinks } from ../server/utils/scraper.js;

async function main() {
 for (const query of [Item 93549004, 93549004 barcode, 93549004 product, 93549004]) {
 const links = await fetchBingLinks(query, 10);
 console.log(query, links);
 }
}

main().catch(err => {
 console.error(err);
 process.exit(1);
});
