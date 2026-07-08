# Security groups: la EC2 es el único punto de entrada; RDS solo acepta desde la EC2.

resource "aws_security_group" "ec2" {
  name        = "airmon-ec2-sg"
  description = "Air Monitoring EC2 (web + ssh)"
  vpc_id      = aws_vpc.main.id

  # SSH solo desde tu IP
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["${var.my_ip}/32"]
  }

  # HTTP / HTTPS (Caddy o acceso directo)
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Frontend (demo sin dominio)
  ingress {
    description = "Frontend Next.js"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # API gateway (el navegador llama aquí; iot/ml/ops NO se exponen a Internet,
  # el gateway los proxya internamente).
  ingress {
    description = "API gateway"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "airmon-ec2-sg" }
}

resource "aws_security_group" "rds" {
  name        = "airmon-rds-sg"
  description = "Air Monitoring RDS (solo desde la EC2)"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL desde la EC2"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "airmon-rds-sg" }
}
