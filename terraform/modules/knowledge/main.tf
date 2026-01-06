# Knowledge module - S3 buckets for specifications and examples

# Random suffix for bucket names to ensure uniqueness
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# KMS key for S3 encryption
resource "aws_kms_key" "s3_key" {
  description             = "KMS key for S3 encryption - GCSE Generator V2"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = {
    Name        = "GCSE S3 Encryption Key"
    Environment = var.environment
    Purpose     = "S3 bucket encryption"
  }
}

resource "aws_kms_alias" "s3_key_alias" {
  name          = "alias/gcse-s3-${var.environment}"
  target_key_id = aws_kms_key.s3_key.key_id
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

# S3 bucket for question bank (AI learning dataset)
resource "aws_s3_bucket" "question_bank" {
  bucket = "gcse-question-bank-${var.environment}-${random_id.bucket_suffix.hex}"
  
  tags = {
    Name        = "GCSE Question Bank"
    Environment = var.environment
    Purpose     = "Store generated questions for AI learning"
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

# Enable versioning on question bank bucket
resource "aws_s3_bucket_versioning" "question_bank_versioning" {
  bucket = aws_s3_bucket.question_bank.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption for specifications bucket with KMS
resource "aws_s3_bucket_server_side_encryption_configuration" "specifications_encryption" {
  bucket = aws_s3_bucket.specifications.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3_key.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# Server-side encryption for examples bucket with KMS
resource "aws_s3_bucket_server_side_encryption_configuration" "examples_encryption" {
  bucket = aws_s3_bucket.examples.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3_key.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# Server-side encryption for lambda packages bucket with KMS
resource "aws_s3_bucket_server_side_encryption_configuration" "lambda_packages_encryption" {
  bucket = aws_s3_bucket.lambda_packages.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3_key.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# Server-side encryption for question bank bucket with KMS
resource "aws_s3_bucket_server_side_encryption_configuration" "question_bank_encryption" {
  bucket = aws_s3_bucket.question_bank.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3_key.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
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

# Block public access to question bank bucket
resource "aws_s3_bucket_public_access_block" "question_bank_pab" {
  bucket = aws_s3_bucket.question_bank.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Bucket policy to enforce HTTPS for specifications bucket
resource "aws_s3_bucket_policy" "specifications_https_policy" {
  bucket = aws_s3_bucket.specifications.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureConnections"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.specifications.arn,
          "${aws_s3_bucket.specifications.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# Bucket policy to enforce HTTPS for examples bucket
resource "aws_s3_bucket_policy" "examples_https_policy" {
  bucket = aws_s3_bucket.examples.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureConnections"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.examples.arn,
          "${aws_s3_bucket.examples.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# Bucket policy to enforce HTTPS for lambda packages bucket
resource "aws_s3_bucket_policy" "lambda_packages_https_policy" {
  bucket = aws_s3_bucket.lambda_packages.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureConnections"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.lambda_packages.arn,
          "${aws_s3_bucket.lambda_packages.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# Bucket policy to enforce HTTPS for question bank bucket
resource "aws_s3_bucket_policy" "question_bank_https_policy" {
  bucket = aws_s3_bucket.question_bank.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureConnections"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.question_bank.arn,
          "${aws_s3_bucket.question_bank.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
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

# Lifecycle configuration for question bank bucket
resource "aws_s3_bucket_lifecycle_configuration" "question_bank_lifecycle" {
  bucket = aws_s3_bucket.question_bank.id

  rule {
    id     = "transition_to_ia"
    status = "Enabled"

    filter {
      prefix = "generated/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }

  rule {
    id     = "delete_old_versions"
    status = "Enabled"

    filter {
      prefix = ""
    }

    noncurrent_version_expiration {
      noncurrent_days = 365  # Keep old versions for 1 year for AI learning
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