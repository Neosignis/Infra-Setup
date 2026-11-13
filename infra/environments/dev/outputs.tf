output "ecr_urls" {
  value = module.registry.urls
}
output "bucket_names" {
  value = module.storage.bucket_names
}
output "cognito_issuer" {
  value = module.identity.issuer
}
output "cognito_client_id" {
  value = module.identity.client_id
}
output "cognito_domain" {
  value = module.identity.domain
}
output "api_alb_dns" {
  value = try(module.api[0].alb_dns, null)
}
output "database_endpoint" {
  value = try(module.database[0].endpoint, null)
}
output "database_master_secret_arn" {
  value     = try(module.database[0].master_secret_arn, null)
  sensitive = true
}
output "gpu_service_name" {
  value = try(module.gpu[0].service_name, null)
}
