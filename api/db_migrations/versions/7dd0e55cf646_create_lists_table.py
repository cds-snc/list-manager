"""create lists table

Revision ID: 7dd0e55cf646
Revises:
Create Date: 2021-08-26 23:07:17.310594

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "7dd0e55cf646"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "lists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Unicode(255), nullable=False, unique=True),
        sa.Column("language", sa.Unicode(255), nullable=False),
        sa.Column("active", sa.Boolean, unique=False, default=True),
        sa.Column("subscribe_email_template_id", sa.Unicode(255)),
        sa.Column("unsubscribe_email_template_id", sa.Unicode(255)),
        sa.Column("subscribe_phone_template_id", sa.Unicode(255)),
        sa.Column("unsubscribe_phone_template_id", sa.Unicode(255)),
        sa.Column("service_id", sa.Unicode(255), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime, default=sa.func.utc_timestamp()),
        sa.Column("updated_at", sa.DateTime, onupdate=sa.func.utc_timestamp()),
    )


def downgrade():
    op.drop_table("lists")
