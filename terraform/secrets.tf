# --- Secrets Manager: Application SECRET_KEY ---

resource "aws_secretsmanager_secret" "app_secret_key" {
  name        = "${var.app_name}/secret-key"
  description = "SECRET_KEY for JWT signing in the Task API"

  tags = {
    Name = "${var.app_name}-secret-key"
  }
}

resource "aws_secretsmanager_secret_version" "app_secret_key" {
  secret_id     = aws_secretsmanager_secret.app_secret_key.id
  secret_string = "CHANGE_ME_AFTER_TERRAFORM_APPLY"

  lifecycle {
    ignore_changes = [secret_string]
  }
}
