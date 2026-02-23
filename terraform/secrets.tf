# --- Secrets Manager: Application SECRET_KEY ---

resource "aws_secretsmanager_secret" "app_secret_key" {
  name        = "${var.app_name}/secret-key"
  description = "SECRET_KEY for JWT signing in the Task API"

  tags = {
    Name = "${var.app_name}-secret-key"
  }
}

resource "random_password" "app_secret_key" {
  length  = 64
  special = true
}

resource "aws_secretsmanager_secret_version" "app_secret_key" {
  secret_id     = aws_secretsmanager_secret.app_secret_key.id
  secret_string = random_password.app_secret_key.result

  lifecycle {
    ignore_changes = [secret_string]
  }
}
