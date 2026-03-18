import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from sqlalchemy.orm import Session

from app.config import settings
from app.models.usuario import Usuario

logger = logging.getLogger(__name__)


def _get_coordinador_emails(db: Session) -> list[str]:
    """Obtener emails de coordinadores activos."""
    usuarios = (
        db.query(Usuario)
        .filter(Usuario.rol == "coordinador", Usuario.estado == "activo")
        .all()
    )
    return [u.email for u in usuarios]


def send_calibracion_notification(
    db: Session,
    equipo_data: dict,
    incidencia_id: int,
    motivo: str = "anual",
) -> bool:
    """Enviar notificacion de calibracion a coordinadores.

    Args:
        db: Session de base de datos
        equipo_data: dict con datos del equipo (device_id, nombre, modelo, etc.)
        incidencia_id: ID de la incidencia creada
        motivo: "anual" o "post_correctiva"
    """
    if not settings.SMTP_HOST:
        logger.warning("SMTP no configurado, omitiendo envio de email")
        return False

    destinatarios = _get_coordinador_emails(db)
    if not destinatarios:
        logger.warning("No hay coordinadores activos para notificar")
        return False

    device_id = equipo_data.get("device_id", "N/A")
    nombre = equipo_data.get("nombre", "N/A")
    modelo = equipo_data.get("modelo", "N/A")
    marca = equipo_data.get("marca", "N/A")
    ubicacion = equipo_data.get("ubicacion", "N/A")
    parametro = equipo_data.get("parametro_medicion", "N/A")

    if motivo == "anual":
        asunto = f"Calibracion anual proxima - Equipo {device_id}"
        fecha_aniversario = equipo_data.get("fecha_aniversario", "N/A")
        motivo_texto = (
            f"Se ha detectado que el equipo {device_id} se aproxima a su "
            f"fecha de calibracion anual (aniversario: {fecha_aniversario})."
        )
    else:
        asunto = f"Calibracion post-correctiva requerida - Equipo {device_id}"
        motivo_texto = (
            f"Se ha finalizado un mantenimiento correctivo del equipo "
            f"{device_id} y se requiere una calibracion posterior."
        )

    link = f"{settings.FRONTEND_URL}/incidencias/{incidencia_id}"

    cuerpo = (
        f"{motivo_texto}\n\n"
        f"--- Datos del equipo ---\n"
        f"Device ID: {device_id}\n"
        f"Nombre: {nombre}\n"
        f"Modelo: {modelo}\n"
        f"Marca: {marca}\n"
        f"Ubicacion: {ubicacion}\n"
        f"Parametro de medicion: {parametro}\n\n"
        f"Se ha creado una incidencia de calibracion que requiere su "
        f"coordinacion.\n\n"
        f"Como coordinador, usted es responsable de:\n"
        f"  - Coordinar la calibracion con el proveedor especializado\n"
        f"  - Recibir y adjuntar el certificado de calibracion\n"
        f"  - Cerrar la incidencia una vez completada\n\n"
        f"Ver incidencia: {link}\n"
    )

    try:
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_FROM
        msg["To"] = ", ".join(destinatarios)
        msg["Subject"] = asunto
        msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, destinatarios, msg.as_string())

        logger.info(
            "Email de calibracion enviado a %d coordinador(es) para equipo %s",
            len(destinatarios),
            device_id,
        )
        return True
    except Exception:
        logger.exception("Error enviando email de calibracion para equipo %s", device_id)
        return False


def send_alerta_correctiva_notification(
    db: Session,
    equipo_data: dict,
    incidencia_id: int,
) -> bool:
    """Enviar notificacion a coordinadores cuando se crea incidencia correctiva por alerta alta.

    Args:
        db: Session de base de datos
        equipo_data: dict con datos del equipo (device_id, nombre, modelo, etc.)
        incidencia_id: ID de la incidencia creada
    """
    if not settings.SMTP_HOST:
        logger.warning("SMTP no configurado, omitiendo envio de email")
        return False

    destinatarios = _get_coordinador_emails(db)
    if not destinatarios:
        logger.warning("No hay coordinadores activos para notificar")
        return False

    device_id = equipo_data.get("device_id", "N/A")
    nombre = equipo_data.get("nombre", "N/A")
    modelo = equipo_data.get("modelo", "N/A")
    marca = equipo_data.get("marca", "N/A")
    ubicacion = equipo_data.get("ubicacion", "N/A")
    parametro = equipo_data.get("parametro_medicion", "N/A")

    asunto = f"ALERTA ALTA: Incidencia correctiva creada - Equipo {device_id}"
    motivo_texto = (
        f"Se ha detectado una prediccion de ALTO RIESGO (RUL <= 30 dias) "
        f"para el equipo {device_id}. Se ha creado automaticamente una "
        f"incidencia correctiva que requiere atencion inmediata."
    )

    link = f"{settings.FRONTEND_URL}/incidencias/{incidencia_id}"

    cuerpo = (
        f"{motivo_texto}\n\n"
        f"--- Datos del equipo ---\n"
        f"Device ID: {device_id}\n"
        f"Nombre: {nombre}\n"
        f"Modelo: {modelo}\n"
        f"Marca: {marca}\n"
        f"Ubicacion: {ubicacion}\n"
        f"Parametro de medicion: {parametro}\n\n"
        f"Acciones requeridas:\n"
        f"  - Revisar el estado del equipo inmediatamente\n"
        f"  - Coordinar mantenimiento correctivo\n"
        f"  - Actualizar el estado de la incidencia\n\n"
        f"Ver incidencia: {link}\n"
    )

    try:
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_FROM
        msg["To"] = ", ".join(destinatarios)
        msg["Subject"] = asunto
        msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, destinatarios, msg.as_string())

        logger.info(
            "Email de alerta correctiva enviado a %d coordinador(es) para equipo %s",
            len(destinatarios),
            device_id,
        )
        return True
    except Exception:
        logger.exception("Error enviando email de alerta correctiva para equipo %s", device_id)
        return False
