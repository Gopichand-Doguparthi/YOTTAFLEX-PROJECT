"""Add review_cases table for human disparity review workflow

Revision ID: 002_add_review_cases
Revises: 001_initial_schema
Create Date: 2026-11-12 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '002_add_review_cases'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table('review_cases'):
        op.create_table(
            'review_cases',
            sa.Column('case_id', sa.String(length=64), nullable=False),
            sa.Column('employee_id', sa.String(length=32), nullable=False),
            sa.Column('status', sa.String(length=24), nullable=False, server_default='OPEN'),
            sa.Column('assigned_to', sa.String(length=128), nullable=True),
            sa.Column('comments', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.ForeignKeyConstraint(['employee_id'], ['employees.employee_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('case_id'),
            sa.UniqueConstraint('employee_id', name='uq_review_cases_employee_id'),
        )
        op.create_index('idx_case_status', 'review_cases', ['status'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table('review_cases'):
        existing_indexes = {idx['name'] for idx in inspector.get_indexes('review_cases')}
        if 'idx_case_status' in existing_indexes:
            op.drop_index('idx_case_status', table_name='review_cases')
        op.drop_table('review_cases')
