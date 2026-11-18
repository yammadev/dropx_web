"""firma de quien recibe guardada en la base de datos

Revision ID: c41f7a2d9b10
Revises: 9d15f59ec52b
Create Date: 2026-11-17 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = 'c41f7a2d9b10'
down_revision = '9d15f59ec52b'
branch_labels = None
depends_on = None


def upgrade():
    # Columna para la imagen PNG de la firma (en MySQL, MEDIUMBLOB: hasta 16 MB)
    with op.batch_alter_table('packages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('signature', sa.LargeBinary().with_variant(mysql.MEDIUMBLOB(), 'mysql'), nullable=True))


def downgrade():
    with op.batch_alter_table('packages', schema=None) as batch_op:
        batch_op.drop_column('signature')
