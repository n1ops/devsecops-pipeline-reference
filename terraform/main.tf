terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Backend config is partial — bucket and dynamodb_table are passed at init:
  #   terraform init -backend-config=backend.tfvars
  backend "s3" {
    key     = "prod/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}

resource "aws_dynamodb_table" "terraform_locks" {
  name         = "devsecops-pipeline-tfstate-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "devsecops-pipeline-reference"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
