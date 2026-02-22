data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# --- Execution Role (pulling images, writing logs) ---

resource "aws_iam_role" "ecs_execution" {
  name               = "${var.app_name}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# --- Task Role (app permissions) ---

resource "aws_iam_role" "ecs_task" {
  name               = "${var.app_name}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

data "aws_iam_policy_document" "ecs_task" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.app.arn}:*"]
  }
}

resource "aws_iam_policy" "ecs_task" {
  name   = "${var.app_name}-ecs-task-policy"
  policy = data.aws_iam_policy_document.ecs_task.json
}

resource "aws_iam_role_policy_attachment" "ecs_task" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.ecs_task.arn
}
