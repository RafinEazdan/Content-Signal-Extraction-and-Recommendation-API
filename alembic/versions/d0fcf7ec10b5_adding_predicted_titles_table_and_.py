"""adding predicted_titles table and updating some constraints on channels table

Revision ID: d0fcf7ec10b5
Revises: 6e0fc348cc91
Create Date: 2026-03-20 05:49:10.726613

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0fcf7ec10b5'
down_revision: Union[str, Sequence[str], None] = '6e0fc348cc91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'predicted_titles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_db_id', sa.Integer(), nullable=False),
        sa.Column('predicted_title', sa.String(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_unique_constraint(
        "uq_channels_channel_handle",
        "channels",
        ["channel_handle"]
    )

    op.create_unique_constraint(
        "uq_channels_channel_id",
        "channels",
        ["channel_id"]
    )

    op.execute("""
        ALTER TABLE comments 
        ALTER COLUMN video_db_id 
        TYPE INTEGER 
        USING video_db_id::integer
    """)

def downgrade() -> None:
    op.execute("""
        ALTER TABLE comments 
        ALTER COLUMN video_db_id 
        TYPE VARCHAR
    """)

    op.drop_constraint("uq_channels_channel_handle", "channels", type_="unique")
    op.drop_constraint("uq_channels_channel_id", "channels", type_="unique")

    op.drop_table('predicted_titles')
