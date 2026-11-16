# Retailer extraction assessment

The current URL workflow uses the shared robots-aware, SSRF-safe page fetcher,
then JSON-LD/microdata and static HTML extraction. The results below distinguish
live checks in `reports/retailer_audit.json` from retailers with no recorded live
check. No retailer-specific adapter or private API is used.

| Retailer | Evidence | Fields found | Missing / limitation | Page behavior | Status |
|---|---|---|---|---|---|
| Blinkit | Live permitted fetch, recorded in `retailer_audit.json` | Product name and brand in JSON-LD; `75 g` in HTML | Selling price, MRP, availability, variant, ingredients, nutrition, image | Response was fetchable; metadata is partial | Partial live extraction |
| Zepto | Live permitted fetch, recorded in `retailer_audit.json` | None | Identity, price, quantity, image, ingredients, nutrition | Empty response in the audited environment; likely location/dynamic/edge dependent | Unsupported in this environment |
| Swiggy Instamart | Live permitted fetch, recorded in `retailer_audit.json` | None | Identity, price, quantity, image, ingredients, nutrition | Empty response in the audited environment; likely location/dynamic/edge dependent | Unsupported in this environment |
| Amazon India | Live permitted fetch, recorded in `retailer_audit.json` | A weak ingredient text fragment only; dynamic heading rejected as identity | Confirmed identity, price, MRP, quantity, variant, availability, nutrition, image | Dynamic/anti-bot response observed; no control was bypassed | Unsupported for reliable product extraction |
| BigBasket | No live response or retailer fixture recorded | None verified | All fields unverified | Dynamic behavior not tested in this task | Not assessed; do not claim support |
| JioMart | No live response or retailer fixture recorded | None verified | All fields unverified | Dynamic behavior not tested in this task | Not assessed; do not claim support |

All recorded retailer checks use real fetched pages; the repository also has
synthetic/static fixtures for extractor regression tests, but fixtures are not
retailer compatibility evidence. Product price, availability, variant, and image
must be treated as unavailable unless extraction evidence exists on the current
listing. If a retailer returns an empty, blocked, or ambiguous page, use manual
entry or label-image upload; do not try to evade the site's controls.
