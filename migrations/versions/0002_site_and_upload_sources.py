"""site per source, photo and saved-page sources

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-17 10:00:00
"""
from urllib.parse import urlsplit

from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

OLD = "source_type IN ('url', 'open_food_facts', 'synthetic_sample', 'manual')"
NEW = "source_type IN ('url', 'open_food_facts', 'synthetic_sample', 'manual', 'photo', 'saved_page')"


def upgrade() -> None:
    op.add_column('product_source', sa.Column('site', sa.String(length=100), nullable=True))
    op.create_index(op.f('ix_product_source_site'), 'product_source', ['site'], unique=False)
    op.drop_constraint('ck_source_type', 'product_source', type_='check')
    op.create_check_constraint('ck_source_type', 'product_source', NEW)
    # Backfill: pages analysed by URL get the host of that URL (www. removed).
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, source_url FROM product_source "
                                "WHERE source_type = 'url' AND source_url IS NOT NULL")).all()
    for id_, url in rows:
        host = (urlsplit(url).hostname or "").lower()
        if host:
            bind.execute(sa.text("UPDATE product_source SET site = :s WHERE id = :i"),
                         {"s": host[4:] if host.startswith("www.") else host, "i": id_})


def downgrade() -> None:
    op.execute("DELETE FROM product_source WHERE source_type IN ('photo', 'saved_page')")
    op.drop_constraint('ck_source_type', 'product_source', type_='check')
    op.create_check_constraint('ck_source_type', 'product_source', OLD)
    op.drop_index(op.f('ix_product_source_site'), table_name='product_source')
    op.drop_column('product_source', 'site')
