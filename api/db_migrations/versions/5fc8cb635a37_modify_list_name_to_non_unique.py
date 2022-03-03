"""modify List name to non-unique

Revision ID: 5fc8cb635a37
Revises: 5b59cc7e3b59
Create Date: 2022-03-03 15:23:24.583903

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "5fc8cb635a37"
down_revision = "5b59cc7e3b59"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("lists_name_key", "lists")


def downgrade():
    op.create_unique_constraint("lists_name_key", "lists", ["name"])
