output "ec2_public_ip" {
  description = "IP pública (elástica) de la EC2"
  value       = aws_eip.app.public_ip
}

output "rds_endpoint" {
  description = "Endpoint de RDS PostgreSQL"
  value       = aws_db_instance.main.address
}

output "s3_bucket" {
  description = "Bucket de artefactos del ensemble"
  value       = aws_s3_bucket.artifacts.bucket
}

output "app_url" {
  description = "URL del frontend"
  value       = "http://${aws_eip.app.public_ip}:3000"
}

output "api_url" {
  description = "URL del api-gateway"
  value       = "http://${aws_eip.app.public_ip}:8000"
}

output "ssh" {
  description = "Comando SSH a la EC2"
  value       = "ssh -i ~/.ssh/airmon_ec2 ec2-user@${aws_eip.app.public_ip}"
}
