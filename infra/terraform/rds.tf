# RDS PostgreSQL 15 — una sola base 'airmonitoring' (los 4 servicios comparten
# la BD con tablas de versión alembic distintas). Sin IP pública.

resource "aws_db_subnet_group" "main" {
  name       = "airmon-db-subnet"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  tags       = { Name = "airmon-db-subnet" }
}

resource "aws_db_instance" "main" {
  identifier             = "airmon-db"
  engine                 = "postgres"
  engine_version         = "15"
  instance_class         = var.db_instance_class
  allocated_storage      = 20
  storage_type           = "gp3"
  db_name                = "airmonitoring"
  username               = "airmon"
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  skip_final_snapshot    = true
  # Free-tier de AWS no permite retención > 0. Cambiar a 7 al salir de free-tier.
  backup_retention_period = 0
  tags = { Name = "airmon-db" }
}
