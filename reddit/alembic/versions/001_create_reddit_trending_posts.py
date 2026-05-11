"""create reddit_trending_posts

Revision ID: 001
Revises:
Create Date: 2026-05-12
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reddit_trending_posts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("post_id", sa.String(20), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("subreddit", sa.String(100), nullable=False),
        sa.Column("upvotes", sa.Integer(), nullable=False),
        sa.Column("num_comments", sa.Integer(), nullable=False),
        sa.Column("trend_score", sa.Float(), nullable=False),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("cache_key", sa.String(300), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reddit_trending_posts_cache_key", "reddit_trending_posts", ["cache_key"])
    op.create_index("ix_reddit_trending_posts_fetched_at", "reddit_trending_posts", ["fetched_at"])


def downgrade() -> None:
    op.drop_index("ix_reddit_trending_posts_fetched_at", table_name="reddit_trending_posts")
    op.drop_index("ix_reddit_trending_posts_cache_key", table_name="reddit_trending_posts")
    op.drop_table("reddit_trending_posts")
