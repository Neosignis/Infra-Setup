variable "name" { type = string }
variable "region" { type = string }
variable "callback_urls" { type = list(string) }
variable "logout_urls" { type = list(string) }

resource "aws_cognito_user_pool" "users" {
  name                     = var.name
  auto_verified_attributes = ["email"]
  username_attributes      = ["email"]
  admin_create_user_config {
    allow_admin_create_user_only = true
  }
  password_policy {
    minimum_length                   = 14
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 3
  }
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }
}
resource "aws_cognito_user_pool_client" "web" {
  name                                 = "workbench"
  user_pool_id                         = aws_cognito_user_pool.users.id
  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = var.callback_urls
  logout_urls                          = var.logout_urls
  prevent_user_existence_errors        = "ENABLED"
  enable_token_revocation              = true
  access_token_validity                = 5
  id_token_validity                    = 5
  refresh_token_validity               = 1
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
}
resource "aws_cognito_user_pool_domain" "web" {
  domain       = var.name
  user_pool_id = aws_cognito_user_pool.users.id
}
output "issuer" { value = "https://cognito-idp.${var.region}.amazonaws.com/${aws_cognito_user_pool.users.id}" }
output "client_id" { value = aws_cognito_user_pool_client.web.id }
output "domain" { value = "https://${aws_cognito_user_pool_domain.web.domain}.auth.${var.region}.amazoncognito.com" }
