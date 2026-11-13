# Bedrock Knowledge Base for PDF content

# OpenSearch Serverless Collection
resource "aws_opensearchserverless_collection" "kb_collection" {
  name = "gcse-kb-${var.environment}"
  type = "VECTORSEARCH"
}

# Encryption policy
resource "aws_opensearchserverless_security_policy" "kb_encryption" {
  name = "gcse-kb-enc-${var.environment}"
  type = "encryption"
  
  policy = jsonencode({
    Rules = [{
      ResourceType = "collection"
      Resource = ["collection/gcse-kb-${var.environment}"]
    }]
    AWSOwnedKey = true
  })
}

# Network policy
resource "aws_opensearchserverless_security_policy" "kb_network" {
  name = "gcse-kb-net-${var.environment}"
  type = "network"
  
  policy = jsonencode([{
    Rules = [{
      ResourceType = "collection"
      Resource = ["collection/gcse-kb-${var.environment}"]
    }]
    AllowFromPublic = true
  }])
}

# IAM role for Bedrock KB
resource "aws_iam_role" "bedrock_kb_role" {
  name = "bedrock-kb-role-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "bedrock.amazonaws.com"
      }
    }]
  })
}

# S3 access for KB
resource "aws_iam_role_policy" "kb_s3_policy" {
  name = "kb-s3-policy"
  role = aws_iam_role.bedrock_kb_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:GetObject", "s3:ListBucket"]
      Resource = [
        "arn:aws:s3:::${var.specifications_bucket_name}",
        "arn:aws:s3:::${var.specifications_bucket_name}/*"
      ]
    }]
  })
}

# Bedrock Knowledge Base
resource "aws_bedrockagent_knowledge_base" "gcse_kb" {
  name     = "gcse-kb-${var.environment}"
  role_arn = aws_iam_role.bedrock_kb_role.arn
  
  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:${var.region}::foundation-model/amazon.titan-embed-text-v1"
    }
  }
  
  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.kb_collection.arn
      vector_index_name = "gcse-index"
      field_mapping {
        vector_field   = "embedding"
        text_field     = "text"
        metadata_field = "metadata"
      }
    }
  }
}

# Data source
resource "aws_bedrockagent_data_source" "s3_source" {
  knowledge_base_id = aws_bedrockagent_knowledge_base.gcse_kb.id
  name              = "s3-pdfs"
  
  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = "arn:aws:s3:::${var.specifications_bucket_name}"
    }
  }
  
  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "FIXED_SIZE"
      fixed_size_chunking_configuration {
        max_tokens         = 300
        overlap_percentage = 20
      }
    }
  }
}

output "knowledge_base_id" {
  value = aws_bedrockagent_knowledge_base.gcse_kb.id
}
