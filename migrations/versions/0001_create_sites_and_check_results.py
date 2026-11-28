"""Create sites and check_results without inserting any data."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("check_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("check_interval_seconds > 0", name="ck_sites_positive_interval"),
    )
    op.create_table(
        "check_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_up", sa.Boolean(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.CheckConstraint("response_ms >= 0", name="ck_check_results_nonnegative_response"),
        sa.CheckConstraint("status_code BETWEEN 100 AND 599", name="ck_check_results_http_status"),
    )
    op.create_index("ix_check_results_site_id_checked_at", "check_results", ["site_id", "checked_at"])


def downgrade() -> None:
    op.drop_index("ix_check_results_site_id_checked_at", table_name="check_results")
    op.drop_table("check_results")
    op.drop_table("sites")
