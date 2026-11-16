# Product URL Source Authorization and Limitations

## Enabled source scope

The URL extraction service uses the existing `open_food_facts` registration. Its domain allowlist is `world.openfoodfacts.org`; its local policy evidence points to the repository's runtime-only URL analysis documentation, existing Open Food Facts integration, robots handling, and ODbL attribution/share-alike requirements. The source is processed one user-submitted URL at a time. The candidate retains Open Food Facts attribution and ODbL source metadata.

This is a repository policy decision, not an independent legal opinion or a live verification of current terms. The service does not crawl lists, search pages, or use private endpoints. The repository's source notes should be rechecked by the project owner before changing the permitted fields, host allowlist, retention, or reuse of extracted content. Product image rights may differ from database/content terms; images are only referenced and never downloaded here.

## Blocked sources

- Retailer domains such as Blinkit, Zepto, Swiggy Instamart, Amazon India, BigBasket and JioMart are not registered as authorized product-page sources in this workflow and are blocked before DNS/network access.
- BigBasket's existing registration has unknown authorization and is disabled; the URL service will not access it.
- Unknown, undocumented, disabled, or denied source registrations fail closed.
- A redirect to a host outside the registered source domain set is blocked, even when the destination is publicly routable.

No CAPTCHA, login, access control, anti-bot mechanism or robots restriction is bypassed. `robots.txt` is checked by the shared fetcher. Consistent with that existing fetcher's behavior, an unreachable/missing robots file is treated as no stated restriction; a disallow rule blocks the page. The service makes no request to image URLs, including HEAD requests, so MIME type and image availability remain unverified.

## Technical limitations

- Safe destination validation uses DNS resolution before connection, but the shared fetcher's documented DNS-rebinding limitation remains; production should use an egress firewall.
- Dynamic or client-rendered pages may expose no usable HTML/JSON-LD. The service does not execute JavaScript or use retailer/private APIs.
- Schema.org and HTML values may be stale, incomplete, malformed or refer to a variant different from the page title. Conflicts are reported; source data is not authoritative ground truth.
- `build_product` uses the project's existing category taxonomy and ingredient dictionary. Category is interpreted, and ingredient normalization is a candidate transformation.
- Duplicate detection is limited to distinct Product entities present on the fetched page. Cross-page/database duplicate matching is intentionally not implemented.
- Page-level Open Graph images are not proven to depict the selected product. No image bytes or product identity are visually checked.
- A product URL on Open Food Facts is not a retailer listing, so retailer identity remains null unless a future explicitly authorized retailer-specific source is added.
