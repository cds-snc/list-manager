"""create subscriptions table

Revision ID: 151dc92c369f
Revises: 7dd0e55cf646
Create Date: 2021-08-26 23:35:20.570405

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "151dc92c369f"
down_revision = "7dd0e55cf646"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("list_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.Unicode(255)),
        sa.Column("phone", sa.Unicode(255)),
        sa.Column("confirmed", sa.Boolean, unique=False, default=False),
        sa.Column("created_at", sa.DateTime, default=sa.func.utc_timestamp()),
        sa.Column("updated_at", sa.DateTime, onupdate=sa.func.utc_timestamp()),
        sa.ForeignKeyConstraint(
            ["list_id"],
            ["lists.id"],
        ),
    )


def downgrade():
    op.drop_table("subscriptions")
