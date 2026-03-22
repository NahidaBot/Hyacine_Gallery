"""add authors table and artworks.author_ref_id

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-03-23 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a1'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'authors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('platform_uid', sa.String(length=255), nullable=False),
        sa.Column('canonical_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['canonical_id'], ['authors.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('platform', 'platform_uid', name='uq_authors_platform_uid'),
    )
    with op.batch_alter_table('authors', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_authors_name'), ['name'], unique=False)
        batch_op.create_index(batch_op.f('ix_authors_platform'), ['platform'], unique=False)

    with op.batch_alter_table('artworks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('author_ref_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_artworks_author_ref_id'), ['author_ref_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_artworks_author_ref_id',
            'authors',
            ['author_ref_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    with op.batch_alter_table('artworks', schema=None) as batch_op:
        batch_op.drop_constraint('fk_artworks_author_ref_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_artworks_author_ref_id'))
        batch_op.drop_column('author_ref_id')

    with op.batch_alter_table('authors', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_authors_platform'))
        batch_op.drop_index(batch_op.f('ix_authors_name'))

    op.drop_table('authors')
