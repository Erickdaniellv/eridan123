"""Descripción de los cambios

Revision ID: 7b7909067c4b
Revises: 
Create Date: 2024-12-14 11:51:14.136660

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7b7909067c4b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('pedidos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('productos_str', sa.Text(), nullable=True),
    sa.Column('total', sa.Float(), nullable=True),
    sa.Column('estado', sa.String(length=20), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('productos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=50), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=True),
    sa.Column('precio_base', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('saldos_cartera',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('empresa', sa.Integer(), nullable=False),
    sa.Column('llave_sucursal_doc', sa.String(length=20), nullable=False),
    sa.Column('sucursal', sa.Integer(), nullable=False),
    sa.Column('cartera', sa.Integer(), nullable=False),
    sa.Column('tipo_movimiento', sa.String(length=10), nullable=False),
    sa.Column('cod_cliente', sa.String(length=10), nullable=False),
    sa.Column('nombre_cliente', sa.String(length=255), nullable=False),
    sa.Column('limite_credito', sa.Numeric(), nullable=True),
    sa.Column('documento', sa.String(length=20), nullable=False),
    sa.Column('fecha_documento', sa.Date(), nullable=False),
    sa.Column('fecha_movimiento', sa.Date(), nullable=False),
    sa.Column('dias_transcurridos', sa.Integer(), nullable=False),
    sa.Column('importe_original', sa.Numeric(), nullable=False),
    sa.Column('importe_iva', sa.Numeric(), nullable=False),
    sa.Column('tasa_iva', sa.Numeric(), nullable=False),
    sa.Column('saldo_actual', sa.Numeric(), nullable=False),
    sa.Column('tipo_moneda', sa.Enum('PESOS', 'DOLARES', name='tipo_moneda_enum'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('sucursal',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('nombre')
    )
    op.create_table('tamanos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=20), nullable=False),
    sa.Column('precio_extra', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('nombre')
    )
    op.create_table('usuarios',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=100), nullable=False),
    sa.Column('nombre_usuario', sa.String(length=1000), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=True),
    sa.Column('es_administrador', sa.Boolean(), nullable=True),
    sa.Column('es_vendedor', sa.Boolean(), nullable=True),
    sa.Column('margen_personalizado', sa.Float(), nullable=True),
    sa.Column('rfc', sa.String(length=100), nullable=True),
    sa.Column('telefono', sa.String(length=20), nullable=True),
    sa.Column('direccion', sa.String(length=200), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('rfc')
    )
    op.create_table('opciones',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('producto_id', sa.Integer(), nullable=True),
    sa.Column('nombre', sa.String(length=50), nullable=False),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.Column('precio_extra', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('posicion',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('sucursal_id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=100), nullable=False),
    sa.Column('titulo', sa.String(length=100), nullable=False),
    sa.Column('departamento', sa.String(length=100), nullable=False),
    sa.Column('encargado', sa.String(length=100), nullable=True),
    sa.Column('disponible', sa.Boolean(), nullable=True),
    sa.Column('superior_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['sucursal_id'], ['sucursal.id'], ),
    sa.ForeignKeyConstraint(['superior_id'], ['posicion.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('posicion')
    op.drop_table('opciones')
    op.drop_table('usuarios')
    op.drop_table('tamanos')
    op.drop_table('sucursal')
    op.drop_table('saldos_cartera')
    op.drop_table('productos')
    op.drop_table('pedidos')
    # ### end Alembic commands ###
