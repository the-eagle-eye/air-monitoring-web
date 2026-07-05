from unittest.mock import patch, MagicMock

from app.services import email_service


class TestEmailService:
    def test_smtp_not_configured_returns_false(self, db_session):
        """When SMTP_HOST is empty, send should return False."""
        with patch.object(email_service.settings, "SMTP_HOST", ""):
            result = email_service.send_calibracion_notification(
                db_session,
                {"device_id": "T101"},
                incidencia_id=1,
                motivo="anual",
            )
        assert result is False

    def test_get_coordinador_emails(self, db_session):
        """Should return emails of active coordinadores."""
        emails = email_service._get_coordinador_emails(db_session)
        assert "coord@test.com" in emails
        assert len(emails) == 1

    @patch("app.services.email_service.smtplib.SMTP")
    def test_send_email_success(self, mock_smtp_cls, db_session):
        """Should send email via SMTP when configured."""
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(email_service.settings, "SMTP_HOST", "smtp.test.com"),
            patch.object(email_service.settings, "SMTP_PORT", 587),
            patch.object(email_service.settings, "SMTP_USER", "user"),
            patch.object(email_service.settings, "SMTP_PASSWORD", "pass"),
            patch.object(email_service.settings, "SMTP_FROM", "test@test.com"),
            patch.object(email_service.settings, "FRONTEND_URL", "http://localhost:3000"),
        ):
            result = email_service.send_calibracion_notification(
                db_session,
                {
                    "device_id": "T101",
                    "nombre": "Analizador SO2",
                    "modelo": "T101",
                    "marca": "Teledyne",
                    "ubicacion": "Lab OEFA",
                    "parametro_medicion": "SO2",
                    "fecha_aniversario": "2026-03-20",
                },
                incidencia_id=42,
                motivo="anual",
            )

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pass")
        mock_server.sendmail.assert_called_once()
        call_args = mock_server.sendmail.call_args
        assert call_args[0][0] == "test@test.com"  # from
        assert "coord@test.com" in call_args[0][1]  # to

    @patch("app.services.email_service.smtplib.SMTP")
    def test_send_email_smtp_error_returns_false(self, mock_smtp_cls, db_session):
        """SMTP errors should not raise, just return False."""
        mock_smtp_cls.side_effect = Exception("SMTP connection failed")

        with (
            patch.object(email_service.settings, "SMTP_HOST", "smtp.test.com"),
            patch.object(email_service.settings, "SMTP_USER", "user"),
            patch.object(email_service.settings, "SMTP_PASSWORD", "pass"),
        ):
            result = email_service.send_calibracion_notification(
                db_session,
                {"device_id": "T101"},
                incidencia_id=1,
                motivo="post_correctiva",
            )

        assert result is False

    def test_alerta_correctiva_smtp_not_configured(self, db_session):
        """When SMTP_HOST is empty, alerta correctiva email should return False."""
        with patch.object(email_service.settings, "SMTP_HOST", ""):
            result = email_service.send_alerta_correctiva_notification(
                db_session,
                {"device_id": "T101"},
                incidencia_id=1,
            )
        assert result is False

    @patch("app.services.email_service.smtplib.SMTP")
    def test_alerta_correctiva_email_success(self, mock_smtp_cls, db_session):
        """Should send alerta correctiva email via SMTP when configured."""
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(email_service.settings, "SMTP_HOST", "smtp.test.com"),
            patch.object(email_service.settings, "SMTP_PORT", 587),
            patch.object(email_service.settings, "SMTP_USER", "user"),
            patch.object(email_service.settings, "SMTP_PASSWORD", "pass"),
            patch.object(email_service.settings, "SMTP_FROM", "test@test.com"),
            patch.object(email_service.settings, "FRONTEND_URL", "http://localhost:3000"),
        ):
            result = email_service.send_alerta_correctiva_notification(
                db_session,
                {
                    "device_id": "T104",
                    "nombre": "Equipo de Prueba",
                    "modelo": "CRA",
                    "marca": "HONDA",
                    "ubicacion": "LIMA",
                    "parametro_medicion": "10",
                },
                incidencia_id=99,
            )

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.sendmail.assert_called_once()
        call_args = mock_server.sendmail.call_args
        assert "coord@test.com" in call_args[0][1]
        msg_str = call_args[0][2]
        # El asunto viaja como cabecera (no codificado): confirma el subject nuevo
        # (post-retiro RF: "ALERTA: Incidencia correctiva creada - Equipo ...").
        assert "Incidencia correctiva creada" in msg_str
