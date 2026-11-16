# Candidate Sources

Datasets in this directory are isolated research inputs. They are not verified annotations, must not be treated as ground truth, and are excluded from grouped training/evaluation splits until separately reviewed and explicitly approved.

`complete_product_catalog/` is the read-only import release for `Complete_Product_Catalog_With_JSON_Photos.xlsx`. The importer creates a release only in a new or empty directory and refuses to overwrite nonempty output. It does not fetch images, request retailer URLs, or write to PostgreSQL.

The release includes a raw source-cell snapshot for provenance, candidate annotation and acquisition records, image references, quality reports, and an input hash manifest. Review the audit and field mapping in [`../../../reports/COMPLETE_PRODUCT_CATALOG_QUALITY_REPORT.md`](../../../reports/COMPLETE_PRODUCT_CATALOG_QUALITY_REPORT.md) and [`../../../reports/COMPLETE_PRODUCT_CATALOG_FIELD_MAPPING.md`](../../../reports/COMPLETE_PRODUCT_CATALOG_FIELD_MAPPING.md) before any future promotion or annotation work.
