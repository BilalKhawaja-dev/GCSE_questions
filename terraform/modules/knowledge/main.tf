# Knowledge module - S3 buckets for specifications and examples

# Random suffix for bucket names to ensure uniqueness
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# S3 bucket for GCSE specifications
resource "aws_s3_bucket" "specifications" {
  bucket = "gcse-specifications-${var.environment}-${random_id.bucket_suffix.hex}"
  
  tags = {
    Name        = "GCSE Specifications"
    Environment = var.environment
    Purpose     = "Store Edexcel GCSE specification content"
  }
}

# S3 bucket for seed examples
resource "aws_s3_bucket" "examples" {
  bucket = "gcse-examples-${var.environment}-${random_id.bucket_suffix.hex}"
  
  tags = {
    Name        = "GCSE Examples"
    Environment = var.environment
    Purpose     = "Store verified question examples"
  }
}

# S3 bucket for Lambda deployment packages
resource "aws_s3_bucket" "lambda_packages" {
  bucket = "gcse-lambda-packages-${var.environment}-${random_id.bucket_suffix.hex}"
  
  tags = {
    Name        = "GCSE Lambda Packages"
    Environment = var.environment
    Purpose     = "Store Lambda deployment packages"
  }
}

# Enable versioning on specifications bucket
resource "aws_s3_bucket_versioning" "specifications_versioning" {
  bucket = aws_s3_bucket.specifications.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable versioning on examples bucket
resource "aws_s3_bucket_versioning" "examples_versioning" {
  bucket = aws_s3_bucket.examples.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable versioning on lambda packages bucket
resource "aws_s3_bucket_versioning" "lambda_packages_versioning" {
  bucket = aws_s3_bucket.lambda_packages.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption for specifications bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "specifications_encryption" {
  bucket = aws_s3_bucket.specifications.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Server-side encryption for examples bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "examples_encryption" {
  bucket = aws_s3_bucket.examples.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Server-side encryption for lambda packages bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "lambda_packages_encryption" {
  bucket = aws_s3_bucket.lambda_packages.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access to specifications bucket
resource "aws_s3_bucket_public_access_block" "specifications_pab" {
  bucket = aws_s3_bucket.specifications.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Block public access to examples bucket
resource "aws_s3_bucket_public_access_block" "examples_pab" {
  bucket = aws_s3_bucket.examples.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Block public access to lambda packages bucket
resource "aws_s3_bucket_public_access_block" "lambda_packages_pab" {
  bucket = aws_s3_bucket.lambda_packages.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle configuration for specifications bucket
resource "aws_s3_bucket_lifecycle_configuration" "specifications_lifecycle" {
  bucket = aws_s3_bucket.specifications.id

  rule {
    id     = "delete_old_versions"
    status = "Enabled"

    filter {
      prefix = ""
    }

    noncurrent_version_expiration {
      noncurrent_days = 90  # Keep previous versions for 90 days as per requirements
    }
  }

  rule {
    id     = "delete_incomplete_uploads"
    status = "Enabled"

    filter {
      prefix = ""
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Lifecycle configuration for examples bucket
resource "aws_s3_bucket_lifecycle_configuration" "examples_lifecycle" {
  bucket = aws_s3_bucket.examples.id

  rule {
    id     = "delete_old_versions"
    status = "Enabled"

    filter {
      prefix = ""
    }

    noncurrent_version_expiration {
      noncurrent_days = 30  # Keep deleted content for 30 days as per requirements
    }
  }

  rule {
    id     = "delete_incomplete_uploads"
    status = "Enabled"

    filter {
      prefix = ""
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Lifecycle configuration for lambda packages bucket
resource "aws_s3_bucket_lifecycle_configuration" "lambda_packages_lifecycle" {
  bucket = aws_s3_bucket.lambda_packages.id

  rule {
    id     = "delete_old_versions"
    status = "Enabled"

    filter {
      prefix = ""
    }

    noncurrent_version_expiration {
      noncurrent_days = 7  # Keep old deployment packages for 7 days
    }
  }

  rule {
    id     = "delete_incomplete_uploads"
    status = "Enabled"

    filter {
      prefix = ""
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}