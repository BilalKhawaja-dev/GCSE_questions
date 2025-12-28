# AI module outputs

output "bedrock_models" {
  description = "Available Bedrock models"
  value = {
    haiku_model_id  = data.aws_bedrock_foundation_model.haiku.model_id
    sonnet_model_id = data.aws_bedrock_foundation_model.sonnet.model_id
  }
}