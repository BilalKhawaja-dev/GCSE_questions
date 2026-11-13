# AI module - Bedrock model configurations and policies

# Data source to check Bedrock model availability
data "aws_bedrock_foundation_model" "haiku" {
  model_id = var.bedrock_model_haiku
}

data "aws_bedrock_foundation_model" "sonnet" {
  model_id = var.bedrock_model_sonnet
}

# Output model information for verification
output "bedrock_models_available" {
  description = "Available Bedrock models"
  value = {
    haiku = {
      model_id   = data.aws_bedrock_foundation_model.haiku.model_id
      model_name = data.aws_bedrock_foundation_model.haiku.model_name
    }
    sonnet = {
      model_id   = data.aws_bedrock_foundation_model.sonnet.model_id
      model_name = data.aws_bedrock_foundation_model.sonnet.model_name
    }
  }
}