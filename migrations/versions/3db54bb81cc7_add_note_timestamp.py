"""add note timestamp

Revision ID: 3db54bb81cc7
Revises: 
Create Date: 2021-04-07 11:12:33.850292

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3db54bb81cc7'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('note', sa.Column('timestamp', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('note', 'timestamp')
    # ### end Alembic commands ###
