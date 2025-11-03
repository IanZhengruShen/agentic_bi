"""create_visualization_tables

Revision ID: a1b2c3d4e5f6
Revises: dce4b39f5a36
Create Date: 2025-11-03 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'dce4b39f5a36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create custom_style_profiles table
    op.create_table(
        'custom_style_profiles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),

        # Profile metadata
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('is_default', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_public', sa.Boolean, nullable=False, server_default='false'),

        # Style configuration
        sa.Column('base_theme', sa.String(50), nullable=False, server_default="'plotly'"),

        # Color scheme
        sa.Column('color_palette', JSON),
        sa.Column('background_color', sa.String(20)),
        sa.Column('text_color', sa.String(20)),
        sa.Column('grid_color', sa.String(20)),

        # Typography
        sa.Column('font_family', sa.String(100)),
        sa.Column('font_size', sa.Integer),
        sa.Column('title_font_size', sa.Integer),

        # Layout
        sa.Column('margin_config', JSON),

        # Branding
        sa.Column('logo_url', sa.String(500)),
        sa.Column('logo_position', sa.String(20)),
        sa.Column('logo_size', JSON),
        sa.Column('watermark_text', sa.String(100)),

        # Advanced styling
        sa.Column('advanced_config', JSON),

        # Timestamps
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_custom_style_profiles_company', 'custom_style_profiles', ['company_id'])
    op.create_index('idx_custom_style_profiles_company_default', 'custom_style_profiles', ['company_id', 'is_default'])

    # Create visualizations table
    op.create_table(
        'visualizations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', UUID(as_uuid=True), nullable=False),

        # Plotly figure
        sa.Column('chart_type', sa.String(50), nullable=False),
        sa.Column('plotly_figure_json', JSON, nullable=False),

        # Styling
        sa.Column('plotly_theme', sa.String(50), server_default="'plotly'"),
        sa.Column('custom_style_profile_id', UUID(as_uuid=True)),
        sa.Column('theme_customizations', JSON),

        # Metadata
        sa.Column('title', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('insights', JSON),

        # Recommendation metadata
        sa.Column('recommendation_confidence', sa.Integer),
        sa.Column('alternative_chart_types', JSON),

        # Status
        sa.Column('status', sa.String(50), server_default="'pending'"),

        # Timestamps
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),

        # Foreign keys
        sa.ForeignKeyConstraint(['custom_style_profile_id'], ['custom_style_profiles.id'], ondelete='SET NULL'),
    )
    op.create_index('idx_visualizations_session', 'visualizations', ['session_id'])
    op.create_index('idx_visualizations_user', 'visualizations', ['user_id'])
    op.create_index('idx_visualizations_company', 'visualizations', ['company_id'])
    op.create_index('idx_visualizations_created', 'visualizations', ['created_at'])


def downgrade() -> None:
    op.drop_table('visualizations')
    op.drop_table('custom_style_profiles')
