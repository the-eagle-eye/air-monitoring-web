# EC2 única que corre todo el stack vía docker-compose.prod.yml.
# El rol IAM le da acceso de solo-lectura a S3 (artefactos) y SSM (secretos)
# sin claves hardcodeadas.

# --- Rol IAM: la EC2 lee S3 + SSM ---
resource "aws_iam_role" "ec2" {
  name = "airmon-ec2-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "ec2" {
  name = "airmon-ec2-s3-ssm"
  role = aws_iam_role.ec2.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Read: descarga inicial de artefactos en el user_data (los .pkl + theta_*.json
        # seed) desde S3 al arrancar la EC2.
        # Write: write-through de C11 (docs/spec-auto-training-onboarding.md §7) —
        # `training_service._write_artifacts_atomic` sube el bundle a S3 tras
        # completar el entrenamiento local, para que estaciones warm-uped en
        # producción sobrevivan un replace de la EC2.
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:ListBucket", "s3:PutObject"]
        Resource = [aws_s3_bucket.artifacts.arn, "${aws_s3_bucket.artifacts.arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"]
        Resource = "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/airmon/*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "ec2" {
  name = "airmon-ec2-profile"
  role = aws_iam_role.ec2.name
}

resource "aws_key_pair" "main" {
  key_name   = "airmon-key"
  public_key = var.ssh_public_key
}

data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2.name
  key_name               = aws_key_pair.main.key_name

  root_block_device {
    volume_size = 30 # gp3; espacio para imágenes ML + artefactos
    volume_type = "gp3"
  }

  # Deploy automático: instala Docker, clona el repo, baja artefactos de S3,
  # lee secretos de SSM y levanta el stack. Ver user_data.sh.tftpl.
  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    region          = var.region
    code_bundle_key = var.code_bundle_key
    rds_host        = aws_db_instance.main.address
    s3_bucket       = aws_s3_bucket.artifacts.bucket
    public_host     = var.public_host
  })

  # Recrea la instancia si cambia el user_data (re-deploy).
  user_data_replace_on_change = true

  tags = { Name = "airmon-app" }

  # La BD debe existir antes de que la EC2 corra las migraciones al arrancar.
  depends_on = [aws_db_instance.main]
}

resource "aws_eip" "app" {
  instance = aws_instance.app.id
  tags     = { Name = "airmon-eip" }
}
