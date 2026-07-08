# Air Monitoring — infraestructura AWS (arquitectura EC2 única + RDS + S3).
# Ver docs/aws/spec-migracion-aws.md y docs/aws/guia-aws-paso-a-paso.md.
#
#   terraform init
#   terraform plan
#   terraform apply     # crea VPC + EC2 + RDS + S3 + SSM + IAM
#   terraform destroy   # elimina todo (costo ~0 entre demos)

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}
