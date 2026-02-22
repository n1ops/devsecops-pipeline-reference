output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.app.dns_name
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.app.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.app.name
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "github_actions_role_arn" {
  description = "IAM role ARN for GitHub Actions OIDC deploy job"
  value       = aws_iam_role.github_actions.arn
}

output "secret_key_arn" {
  description = "Secrets Manager ARN for the application SECRET_KEY"
  value       = aws_secretsmanager_secret.app_secret_key.arn
}
