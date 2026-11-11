"""Initial relational schema migration

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-11 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # locations
    op.create_table(
        'locations',
        sa.Column('location_id', sa.String(length=16), nullable=False),
        sa.Column('location_name', sa.String(length=128), nullable=False),
        sa.Column('country', sa.String(length=3), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('geo_tier', sa.String(length=16), nullable=False),
        sa.Column('cost_of_living_index', sa.Float(), nullable=False),
        sa.CheckConstraint('cost_of_living_index > 0', name='chk_col_index_pos'),
        sa.PrimaryKeyConstraint('location_id'),
        sa.UniqueConstraint('location_name')
    )

    # roles
    op.create_table(
        'roles',
        sa.Column('role_id', sa.String(length=32), nullable=False),
        sa.Column('role_title', sa.String(length=128), nullable=False),
        sa.Column('job_family', sa.String(length=64), nullable=False),
        sa.Column('job_function', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.PrimaryKeyConstraint('role_id'),
        sa.UniqueConstraint('role_title')
    )

    # levels
    op.create_table(
        'levels',
        sa.Column('level_id', sa.String(length=16), nullable=False),
        sa.Column('level_code', sa.String(length=16), nullable=False),
        sa.Column('level_name', sa.String(length=64), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.CheckConstraint('rank >= 1', name='chk_level_rank_pos'),
        sa.PrimaryKeyConstraint('level_id'),
        sa.UniqueConstraint('level_code'),
        sa.UniqueConstraint('rank')
    )

    # compensation_bands
    op.create_table(
        'compensation_bands',
        sa.Column('band_id', sa.String(length=128), nullable=False),
        sa.Column('role_id', sa.String(length=32), nullable=False),
        sa.Column('level_id', sa.String(length=16), nullable=False),
        sa.Column('location_id', sa.String(length=16), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('min_salary', sa.Float(), nullable=False),
        sa.Column('mid_salary', sa.Float(), nullable=False),
        sa.Column('max_salary', sa.Float(), nullable=False),
        sa.Column('effective_start_date', sa.Date(), nullable=False),
        sa.Column('effective_end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='ACTIVE'),
        sa.CheckConstraint('min_salary > 0 AND min_salary < mid_salary AND mid_salary < max_salary', name='chk_band_spread'),
        sa.ForeignKeyConstraint(['level_id'], ['levels.level_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['location_id'], ['locations.location_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.role_id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('band_id')
    )
    op.create_index('idx_band_lookup', 'compensation_bands', ['role_id', 'level_id', 'location_id', 'effective_start_date', 'effective_end_date'])

    # employees
    op.create_table(
        'employees',
        sa.Column('employee_id', sa.String(length=32), nullable=False),
        sa.Column('first_name', sa.String(length=64), nullable=False),
        sa.Column('last_name', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=128), nullable=False),
        sa.Column('department', sa.String(length=64), nullable=False),
        sa.Column('current_role_id', sa.String(length=32), nullable=False),
        sa.Column('current_level_id', sa.String(length=16), nullable=False),
        sa.Column('current_location_id', sa.String(length=16), nullable=False),
        sa.Column('hire_date', sa.Date(), nullable=False),
        sa.Column('employment_type', sa.String(length=20), nullable=False, server_default='FULL_TIME'),
        sa.Column('fte', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('fte > 0 AND fte <= 1.0', name='chk_employee_fte_valid'),
        sa.ForeignKeyConstraint(['current_level_id'], ['levels.level_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['current_location_id'], ['locations.location_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['current_role_id'], ['roles.role_id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('employee_id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_emp_role_lvl_loc', 'employees', ['current_role_id', 'current_level_id', 'current_location_id'])

    # salary_records
    op.create_table(
        'salary_records',
        sa.Column('salary_id', sa.String(length=64), nullable=False),
        sa.Column('employee_id', sa.String(length=32), nullable=False),
        sa.Column('base_salary', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('fte', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('pay_frequency', sa.String(length=16), nullable=False, server_default='ANNUAL'),
        sa.Column('normalized_salary', sa.Float(), nullable=False),
        sa.Column('normalized_currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('change_reason', sa.String(length=32), nullable=False),
        sa.Column('benchmark_band_id', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('base_salary > 0 AND fte > 0 AND fte <= 1.0 AND normalized_salary > 0', name='chk_sal_positive'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.employee_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['benchmark_band_id'], ['compensation_bands.band_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('salary_id')
    )
    op.create_index('idx_sal_emp_eff', 'salary_records', ['employee_id', 'effective_date'])

    # performance_evidence
    op.create_table(
        'performance_evidence',
        sa.Column('evidence_id', sa.String(length=64), nullable=False),
        sa.Column('employee_id', sa.String(length=32), nullable=False),
        sa.Column('review_cycle', sa.String(length=16), nullable=False),
        sa.Column('rating_score', sa.Float(), nullable=False),
        sa.Column('rating_label', sa.String(length=32), nullable=False),
        sa.Column('reviewer_id', sa.String(length=32), nullable=True),
        sa.Column('documented_skills_score', sa.Float(), nullable=False, server_default='70.0'),
        sa.Column('critical_initiative_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.CheckConstraint('rating_score >= 1.0 AND rating_score <= 5.0', name='chk_rating_range'),
        sa.CheckConstraint('documented_skills_score >= 0.0 AND documented_skills_score <= 100.0', name='chk_skill_score_range'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.employee_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['employees.employee_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('evidence_id')
    )
    op.create_index('idx_perf_emp_cycle', 'performance_evidence', ['employee_id', 'review_cycle'])

    # tenure_records
    op.create_table(
        'tenure_records',
        sa.Column('tenure_id', sa.String(length=64), nullable=False),
        sa.Column('employee_id', sa.String(length=32), nullable=False),
        sa.Column('company_start_date', sa.Date(), nullable=False),
        sa.Column('role_start_date', sa.Date(), nullable=False),
        sa.Column('years_of_experience_total', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('tenure_in_company_years', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('tenure_in_role_years', sa.Float(), nullable=False, server_default='0.0'),
        sa.CheckConstraint('years_of_experience_total >= 0.0', name='chk_exp_pos'),
        sa.CheckConstraint('tenure_in_company_years >= 0.0', name='chk_comp_tenure_pos'),
        sa.CheckConstraint('tenure_in_role_years >= 0.0', name='chk_role_tenure_pos'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.employee_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('tenure_id'),
        sa.UniqueConstraint('employee_id')
    )

    # promotions
    op.create_table(
        'promotions',
        sa.Column('promotion_id', sa.String(length=64), nullable=False),
        sa.Column('employee_id', sa.String(length=32), nullable=False),
        sa.Column('from_level_id', sa.String(length=16), nullable=False),
        sa.Column('to_level_id', sa.String(length=16), nullable=False),
        sa.Column('from_role_id', sa.String(length=32), nullable=False),
        sa.Column('to_role_id', sa.String(length=32), nullable=False),
        sa.Column('promotion_date', sa.Date(), nullable=False),
        sa.Column('previous_salary', sa.Float(), nullable=False),
        sa.Column('new_salary', sa.Float(), nullable=False),
        sa.Column('increase_percentage', sa.Float(), nullable=False),
        sa.Column('approved_by', sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.employee_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_level_id'], ['levels.level_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['from_role_id'], ['roles.role_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['to_level_id'], ['levels.level_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['to_role_id'], ['roles.role_id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('promotion_id')
    )

    # adjustment_proposals
    op.create_table(
        'adjustment_proposals',
        sa.Column('proposal_id', sa.String(length=32), nullable=False),
        sa.Column('employee_id', sa.String(length=32), nullable=False),
        sa.Column('current_salary', sa.Float(), nullable=False),
        sa.Column('proposed_salary', sa.Float(), nullable=False),
        sa.Column('adjustment_amount', sa.Float(), nullable=False),
        sa.Column('adjustment_percentage', sa.Float(), nullable=False),
        sa.Column('reason_code', sa.String(length=32), nullable=False),
        sa.Column('justification_notes', sa.Text(), nullable=False),
        sa.Column('evidence_summary', sa.Text(), nullable=False),
        sa.Column('related_disparity_findings', sa.Text(), nullable=False),
        sa.Column('proposed_effective_date', sa.Date(), nullable=False),
        sa.Column('approval_status', sa.String(length=20), nullable=False, server_default='DRAFT'),
        sa.Column('created_by', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('reviewed_by', sa.String(length=64), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.CheckConstraint('current_salary > 0 AND proposed_salary > 0', name='chk_prop_salary_pos'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.employee_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('proposal_id')
    )
    op.create_index('idx_adj_status', 'adjustment_proposals', ['approval_status'])

    # approval_events
    op.create_table(
        'approval_events',
        sa.Column('event_id', sa.String(length=64), nullable=False),
        sa.Column('entity_name', sa.String(length=32), nullable=False),
        sa.Column('entity_id', sa.String(length=128), nullable=False),
        sa.Column('event_type', sa.String(length=32), nullable=False),
        sa.Column('actor_id', sa.String(length=64), nullable=False),
        sa.Column('actor_role', sa.String(length=32), nullable=False),
        sa.Column('old_state', sa.Text(), nullable=True),
        sa.Column('new_state', sa.Text(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('event_id')
    )
    op.create_index('idx_audit_entity', 'approval_events', ['entity_name', 'entity_id'])
    op.create_index('idx_audit_time', 'approval_events', ['timestamp'])

    # exchange_rates
    op.create_table(
        'exchange_rates',
        sa.Column('exchange_rate_id', sa.String(length=32), nullable=False),
        sa.Column('from_currency', sa.String(length=3), nullable=False),
        sa.Column('to_currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('rate', sa.Float(), nullable=False),
        sa.Column('effective_start_date', sa.Date(), nullable=False),
        sa.Column('effective_end_date', sa.Date(), nullable=False),
        sa.CheckConstraint('rate > 0', name='chk_rate_pos'),
        sa.PrimaryKeyConstraint('exchange_rate_id')
    )
    op.create_index('idx_fx_lookup', 'exchange_rates', ['from_currency', 'to_currency', 'effective_start_date', 'effective_end_date'])

    # role_comparability_rationales
    op.create_table(
        'role_comparability_rationales',
        sa.Column('mapping_id', sa.String(length=64), nullable=False),
        sa.Column('role_id_a', sa.String(length=32), nullable=False),
        sa.Column('role_id_b', sa.String(length=32), nullable=False),
        sa.Column('is_comparable', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('documented_rationale', sa.Text(), nullable=False),
        sa.Column('approved_by', sa.String(length=64), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(['role_id_a'], ['roles.role_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id_b'], ['roles.role_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('mapping_id')
    )

    # ground_truth_records
    op.create_table(
        'ground_truth_records',
        sa.Column('ground_truth_id', sa.String(length=64), nullable=False),
        sa.Column('record_type', sa.String(length=32), nullable=False),
        sa.Column('record_id', sa.String(length=128), nullable=False),
        sa.Column('issue_type', sa.String(length=64), nullable=False),
        sa.Column('is_anomaly', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('expected_detection', sa.String(length=64), nullable=False),
        sa.Column('root_cause_explanation', sa.Text(), nullable=False),
        sa.Column('injected_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('ground_truth_id')
    )
    op.create_index('idx_gt_issue', 'ground_truth_records', ['issue_type'])
    op.create_index('idx_gt_record', 'ground_truth_records', ['record_type', 'record_id'])


def downgrade() -> None:
    op.drop_table('ground_truth_records')
    op.drop_table('role_comparability_rationales')
    op.drop_table('exchange_rates')
    op.drop_table('approval_events')
    op.drop_table('adjustment_proposals')
    op.drop_table('promotions')
    op.drop_table('tenure_records')
    op.drop_table('performance_evidence')
    op.drop_table('salary_records')
    op.drop_table('employees')
    op.drop_table('compensation_bands')
    op.drop_table('levels')
    op.drop_table('roles')
    op.drop_table('locations')
