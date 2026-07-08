# Bucket S3 para los artefactos del ensemble (.pkl gitignored, no viajan en el repo).
# Se suben con `aws s3 sync` y la EC2 los descarga al arrancar (user_data).

resource "aws_s3_bucket" "artifacts" {
  bucket        = "airmon-artifacts-${data.aws_caller_identity.current.account_id}"
  force_destroy = true # permite `terraform destroy` aunque tenga objetos (demo)
  tags          = { Name = "airmon-artifacts" }
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
