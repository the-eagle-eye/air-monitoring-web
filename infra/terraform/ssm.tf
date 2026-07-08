# Secretos cifrados en SSM Parameter Store (SecureString, gratis).
# La EC2 los lee vía su rol IAM; nunca viajan en el repo ni en la imagen.

resource "aws_ssm_parameter" "db_password" {
  name  = "/airmon/db_password"
  type  = "SecureString"
  value = var.db_password
}

resource "aws_ssm_parameter" "secret_key" {
  name  = "/airmon/secret_key"
  type  = "SecureString"
  value = var.secret_key
}

resource "aws_ssm_parameter" "smtp_user" {
  name  = "/airmon/smtp_user"
  type  = "SecureString"
  value = var.smtp_user
}

resource "aws_ssm_parameter" "smtp_password" {
  name  = "/airmon/smtp_password"
  type  = "SecureString"
  value = var.smtp_password
}
