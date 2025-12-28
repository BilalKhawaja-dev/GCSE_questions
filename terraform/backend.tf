# Terraform backend configuration for remote state management
# This file configures S3 backend with DynamoDB locking for state management

terraform {
  backend "s3" {
    bucket         = "gcse-terraform-state-a36bf0c7"
    key            = "prod/terraform.tfstate"
    region         = "eu-west-2"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}