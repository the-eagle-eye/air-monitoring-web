"""create ops-service tables

Revision ID: ops_001
Revises:
Create Date: 2026-03-15

"""
from alembic import op
import sqlalchemy as sa

revision = "ops_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Tablas independientes ---

    op.create_table(
        "proveedores_calibracion",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("estado", sa.String(), nullable=False, server_default="activo"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "repuestos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("categoria", sa.String(), nullable=False),
        sa.Column("estado", sa.String(), nullable=False, server_default="activo"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("apellido", sa.String(), nullable=False),
        sa.Column("rol", sa.String(), nullable=False),
        sa.Column("estado", sa.String(), nullable=False, server_default="activo"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "dataloggers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("codigo_interno", sa.String(), nullable=False),
        sa.Column("numero_serie", sa.String(), nullable=True),
        sa.Column("ubicacion", sa.String(), nullable=True),
        sa.Column("estado", sa.String(), nullable=False, server_default="activo"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo_interno"),
    )

    # --- Tablas con dependencias ---

    op.create_table(
        "incidencias",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.String(), nullable=False),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(), nullable=False, server_default="pendiente"),
        sa.Column("prioridad", sa.String(), nullable=False, server_default="media"),
        sa.Column("responsable_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["responsable_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incidencias_device_id", "incidencias", ["device_id"])

    op.create_table(
        "mantenimientos_correctivos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("incidencia_id", sa.Integer(), nullable=False),
        sa.Column("diagnostico", sa.Text(), nullable=True),
        sa.Column("acciones_realizadas", sa.Text(), nullable=True),
        sa.Column("conclusion", sa.Text(), nullable=True),
        sa.Column("fecha_ejecucion", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["incidencia_id"], ["incidencias.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("incidencia_id"),
    )

    op.create_table(
        "mantenimiento_repuestos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("mantenimiento_id", sa.Integer(), nullable=False),
        sa.Column("repuesto_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["mantenimiento_id"], ["mantenimientos_correctivos.id"]
        ),
        sa.ForeignKeyConstraint(["repuesto_id"], ["repuestos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "calibraciones",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("incidencia_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(), nullable=False),
        sa.Column("fecha_calibracion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("certificado_url", sa.String(), nullable=True),
        sa.Column("proveedor_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["incidencia_id"], ["incidencias.id"]),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedores_calibracion.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("incidencia_id"),
    )
    op.create_index("ix_calibraciones_device_id", "calibraciones", ["device_id"])

    op.create_table(
        "archivos_adjuntos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entidad_tipo", sa.String(), nullable=False),
        sa.Column("entidad_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("file_url", sa.String(), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_archivos_entidad", "archivos_adjuntos", ["entidad_tipo", "entidad_id"]
    )

    # --- Seed data ---
    _seed_proveedores()
    _seed_usuarios()
    _seed_dataloggers()
    _seed_repuestos()


def _seed_proveedores():
    op.execute(
        """
        INSERT INTO proveedores_calibracion (nombre) VALUES
            ('Green Group Peru'),
            ('SGS Peru'),
            ('AGQ Labs Peru'),
            ('METRINDUST'),
            ('ALAB Peru'),
            ('Paz Laboratorios'),
            ('PESATEC Peru'),
            ('Air Products Cryogas Peru'),
            ('IMARK Peru'),
            ('SAT Peru')
        """
    )


def _seed_usuarios():
    op.execute(
        """
        INSERT INTO usuarios (email, nombre, apellido, rol) VALUES
            ('admin@oefa.gob.pe', 'Carlos', 'Mendoza', 'administrador'),
            ('tecnico1@oefa.gob.pe', 'Jorge', 'Quispe', 'tecnico'),
            ('coordinador1@oefa.gob.pe', 'Maria', 'Huaman', 'coordinador')
        """
    )


def _seed_dataloggers():
    op.execute(
        """
        INSERT INTO dataloggers (nombre, codigo_interno, numero_serie, ubicacion)
        VALUES
            ('CR310 Logger Norte', 'DL9A3K7P2X', 'SN-DL001', 'Estacion Norte'),
            ('CR310 Logger Sur', 'DL4F8T2M1Q', 'SN-DL002', 'Estacion Sur'),
            ('CR310 Logger Centro', 'DL7L2Z5N9A', 'SN-DL003', 'Estacion Centro'),
            ('CR310 Logger Oeste', 'DL1Q6R8X3M', 'SN-DL004', 'Estacion Oeste'),
            ('CR310 Logger Este', 'DL5B9C2V7T', 'SN-DL005', 'Estacion Este')
        """
    )


def _seed_repuestos():
    # Sensores y Detectores
    op.execute(
        """
        INSERT INTO repuestos (nombre, categoria) VALUES
            ('Sensor de SO2', 'Sensores y Detectores'),
            ('Sensor de NO', 'Sensores y Detectores'),
            ('Sensor de NO2', 'Sensores y Detectores'),
            ('Sensor de NOx', 'Sensores y Detectores'),
            ('Sensor de CO', 'Sensores y Detectores'),
            ('Sensor de CO2', 'Sensores y Detectores'),
            ('Sensor de O3', 'Sensores y Detectores'),
            ('Sensor de H2S', 'Sensores y Detectores'),
            ('Sensor de NH3', 'Sensores y Detectores'),
            ('Sensor de CH4', 'Sensores y Detectores'),
            ('Sensor de hidrocarburos (VOC)', 'Sensores y Detectores'),
            ('Sensor PM1', 'Sensores y Detectores'),
            ('Sensor PM2.5', 'Sensores y Detectores'),
            ('Sensor PM10', 'Sensores y Detectores'),
            ('Sensor de temperatura ambiente', 'Sensores y Detectores'),
            ('Sensor de presion barometrica', 'Sensores y Detectores'),
            ('Sensor de humedad relativa', 'Sensores y Detectores'),
            ('Sensor de flujo de muestra', 'Sensores y Detectores'),
            ('Sensor electroquimico multigas', 'Sensores y Detectores'),
            ('Detector FID (Flame Ionization Detector)', 'Sensores y Detectores')
        """
    )

    # Bombas y Sistemas de Muestreo
    op.execute(
        """
        INSERT INTO repuestos (nombre, categoria) VALUES
            ('Bomba de muestreo de aire', 'Bombas y Sistemas de Muestreo'),
            ('Bomba de vacio', 'Bombas y Sistemas de Muestreo'),
            ('Bomba de diafragma', 'Bombas y Sistemas de Muestreo'),
            ('Motor de bomba de muestreo', 'Bombas y Sistemas de Muestreo'),
            ('Kit de mantenimiento de bomba', 'Bombas y Sistemas de Muestreo'),
            ('Cabezal de bomba', 'Bombas y Sistemas de Muestreo'),
            ('Valvula de control de flujo', 'Bombas y Sistemas de Muestreo'),
            ('Regulador de flujo', 'Bombas y Sistemas de Muestreo'),
            ('Medidor de flujo', 'Bombas y Sistemas de Muestreo'),
            ('Controlador de flujo masico', 'Bombas y Sistemas de Muestreo'),
            ('Restrictor de flujo', 'Bombas y Sistemas de Muestreo'),
            ('Valvula solenoide de muestreo', 'Bombas y Sistemas de Muestreo'),
            ('Valvula check', 'Bombas y Sistemas de Muestreo'),
            ('Valvula bypass', 'Bombas y Sistemas de Muestreo'),
            ('Conector de linea de muestreo', 'Bombas y Sistemas de Muestreo')
        """
    )

    # Filtros y Consumibles
    op.execute(
        """
        INSERT INTO repuestos (nombre, categoria) VALUES
            ('Filtro de particulas PTFE', 'Filtros y Consumibles'),
            ('Filtro de fibra de vidrio', 'Filtros y Consumibles'),
            ('Filtro PM2.5', 'Filtros y Consumibles'),
            ('Filtro PM10', 'Filtros y Consumibles'),
            ('Cartucho filtro de aire', 'Filtros y Consumibles'),
            ('Filtro de linea de muestra', 'Filtros y Consumibles'),
            ('Filtro de bomba', 'Filtros y Consumibles'),
            ('Porta filtro EPA', 'Filtros y Consumibles'),
            ('Impactador PM2.5', 'Filtros y Consumibles'),
            ('Impactador PM10', 'Filtros y Consumibles'),
            ('Cabezal de muestreo PM10', 'Filtros y Consumibles'),
            ('Cabezal de muestreo PM2.5', 'Filtros y Consumibles'),
            ('Filtro HEPA para muestreo', 'Filtros y Consumibles'),
            ('Desecante de silica gel', 'Filtros y Consumibles'),
            ('Cartucho de carbon activado', 'Filtros y Consumibles')
        """
    )

    # Componentes Opticos y Analiticos
    op.execute(
        """
        INSERT INTO repuestos (nombre, categoria) VALUES
            ('Lampara UV para analizador de O3', 'Componentes Opticos y Analiticos'),
            ('Lampara UV para SO2', 'Componentes Opticos y Analiticos'),
            ('Fuente de luz IR', 'Componentes Opticos y Analiticos'),
            ('Detector fotometrico', 'Componentes Opticos y Analiticos'),
            ('Celda de reaccion', 'Componentes Opticos y Analiticos'),
            ('Camara de reaccion', 'Componentes Opticos y Analiticos'),
            ('Fotodiodo detector', 'Componentes Opticos y Analiticos'),
            ('Tubo de absorcion optica', 'Componentes Opticos y Analiticos'),
            ('Reflector optico', 'Componentes Opticos y Analiticos'),
            ('Filtro optico', 'Componentes Opticos y Analiticos')
        """
    )

    # Electronica y Control
    op.execute(
        """
        INSERT INTO repuestos (nombre, categoria) VALUES
            ('Placa electronica principal (PCB)', 'Electronica y Control'),
            ('Modulo de adquisicion de datos', 'Electronica y Control'),
            ('Fuente de poder', 'Electronica y Control'),
            ('Convertidor DC-DC', 'Electronica y Control'),
            ('Modulo Ethernet', 'Electronica y Control'),
            ('Modulo WiFi', 'Electronica y Control'),
            ('Modulo RS232', 'Electronica y Control'),
            ('Modulo RS485', 'Electronica y Control'),
            ('Pantalla LCD', 'Electronica y Control'),
            ('Panel de control', 'Electronica y Control'),
            ('Tarjeta de memoria', 'Electronica y Control'),
            ('CPU del analizador', 'Electronica y Control'),
            ('Controlador de temperatura', 'Electronica y Control'),
            ('Sensor interno de diagnostico', 'Electronica y Control')
        """
    )

    # Sistema Neumatico
    op.execute(
        """
        INSERT INTO repuestos (nombre, categoria) VALUES
            ('Linea de muestreo de teflon', 'Sistema Neumatico'),
            ('Tubo de acero inoxidable', 'Sistema Neumatico'),
            ('Conectores neumaticos', 'Sistema Neumatico'),
            ('Racores de compresion', 'Sistema Neumatico'),
            ('Valvula de calibracion', 'Sistema Neumatico'),
            ('Regulador de presion de gas', 'Sistema Neumatico'),
            ('Manifold de distribucion de gases', 'Sistema Neumatico'),
            ('Trampa de humedad', 'Sistema Neumatico'),
            ('Secador de aire', 'Sistema Neumatico'),
            ('Generador de aire cero', 'Sistema Neumatico')
        """
    )

    # Sistema de Calibracion
    op.execute(
        """
        INSERT INTO repuestos (nombre, categoria) VALUES
            ('Cilindro de gas patron', 'Sistema de Calibracion'),
            ('Regulador de cilindro de gas', 'Sistema de Calibracion'),
            ('Diluidor dinamico de gases', 'Sistema de Calibracion'),
            ('Generador de ozono para calibracion', 'Sistema de Calibracion'),
            ('Calibrador multigas', 'Sistema de Calibracion'),
            ('Valvula automatica de calibracion', 'Sistema de Calibracion')
        """
    )

    # Otros Repuestos
    op.execute(
        """
        INSERT INTO repuestos (nombre, categoria) VALUES
            ('Ventilador de enfriamiento', 'Otros Repuestos'),
            ('Termostato interno', 'Otros Repuestos'),
            ('Cable de alimentacion', 'Otros Repuestos'),
            ('Fusible electrico', 'Otros Repuestos'),
            ('UPS para estacion AQMS', 'Otros Repuestos'),
            ('Rack de montaje del analizador', 'Otros Repuestos'),
            ('Data logger ambiental', 'Otros Repuestos'),
            ('Antena de comunicacion', 'Otros Repuestos'),
            ('Sistema de calefaccion de linea de muestra', 'Otros Repuestos'),
            ('Kit de mantenimiento general', 'Otros Repuestos')
        """
    )


def downgrade() -> None:
    op.drop_table("archivos_adjuntos")
    op.drop_table("calibraciones")
    op.drop_table("mantenimiento_repuestos")
    op.drop_table("mantenimientos_correctivos")
    op.drop_table("incidencias")
    op.drop_table("dataloggers")
    op.drop_table("usuarios")
    op.drop_table("repuestos")
    op.drop_table("proveedores_calibracion")
