"""add_redirect_fields_to_lists

Revision ID: 5b59cc7e3b59
Revises: 151dc92c369f
Create Date: 2021-09-01 14:45:56.464706

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5b59cc7e3b59"
down_revision = "151dc92c369f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "lists",
        sa.Column("subscribe_redirect_url", sa.String, nullable=True),
    )
    op.add_column(
        "lists",
        sa.Column("confirm_redirect_url", sa.String, nullable=True),
    )
    op.add_column(
        "lists",
        sa.Column("unsubscribe_redirect_url", sa.String, nullable=True),
    )


def downgrade():
    op.drop_column("lists", "subscribe_redirect_url")
    op.drop_column("lists", "confirm_redirect_url")
    op.drop_column("lists", "unsubscribe_redirect_url")
