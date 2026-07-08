variable "region" {
  description = "Región AWS"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "Tipo de instancia EC2. t3.small (2GB) recomendado; t3.micro entra en free-tier pero justo de RAM con 2 imágenes ML."
  type        = string
  default     = "t3.small"
}

variable "db_instance_class" {
  description = "Clase de instancia RDS. db.t3.micro entra en free-tier."
  type        = string
  default     = "db.t3.micro"
}

variable "db_password" {
  description = "Password del usuario master de RDS (rotar; nunca commitear)"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "Secreto de firma JWT (HS256) del api-gateway"
  type        = string
  sensitive   = true
}

variable "smtp_user" {
  description = "Usuario SMTP (Mailtrap)"
  type        = string
  sensitive   = true
}

variable "smtp_password" {
  description = "Password SMTP (Mailtrap)"
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "Contenido de la llave pública SSH (~/.ssh/airmon_ec2.pub) para acceder a la EC2"
  type        = string
}

variable "my_ip" {
  description = "Tu IP pública (sin /32) para restringir el acceso SSH"
  type        = string
}

# El repo es PRIVADO → no se clona en la EC2. En su lugar se sube un bundle del
# código a S3 (git archive) y la EC2 lo baja con su rol IAM (sin credenciales git).
variable "code_bundle_key" {
  description = "Key del bundle de código en el bucket S3 (tar.gz subido con git archive)"
  type        = string
  default     = "app/airmon-app-bundle.tar.gz"
}

variable "public_host" {
  description = "Host/IP público que el navegador usará para llamar al gateway. Vacío = usar la IP elástica de la EC2 (se resuelve en user_data)."
  type        = string
  default     = ""
}
