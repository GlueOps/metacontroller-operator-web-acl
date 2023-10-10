
import {
  to = aws_wafv2_web_acl.primary
  id = "7c04bc92-be1f-405a-9da8-bfdfe401d03e/primary/CLOUDFRONT" #Update ID
}

import {
  to = aws_wafv2_web_acl.block-bad-networks
  id = "ab716bd7-7574-41ce-81aa-5c1714afd75a/block-bad-networks/CLOUDFRONT" #Update ID
}

import {
  to = aws_wafv2_web_acl.rate-limit-only
  id = "ca9c9a96-1836-44da-903b-61961c724ad4/rate-limit-only/CLOUDFRONT" #Update ID
}

import {
  to = aws_wafv2_web_acl.block-bad-networks-and-rate-limit
  id = "b08c6112-fbc0-4437-8a11-d201c4a20382/block-bad-networks-and-rate-limit/CLOUDFRONT" #Update ID
}

resource "aws_wafv2_web_acl" "primary" {
  description   = "Provided by GlueOps"
  name          = "primary"
  scope         = "CLOUDFRONT"
  token_domains = []

  custom_response_body {
    content      = <<-EOT
                {
                error: "HTTP 429 Too Many Requests."
                }
            EOT
    content_type = "APPLICATION_JSON"
    key          = "http_429_response"
  }

  default_action {
    allow {
    }
  }

  rule {
    name     = "too-many-requests-per-source-ip"
    priority = 3

    action {
      block {
        custom_response {
          custom_response_body_key = "http_429_response"
          response_code            = 429
        }
      }
    }

    statement {
      rate_based_statement {
        aggregate_key_type = "IP"
        limit              = 100
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "too-many-requests-per-source-ip"
      sampled_requests_enabled   = true
    }
  }
  rule {
    name     = "AWS-AWSManagedRulesAmazonIpReputationList"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAmazonIpReputationList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesAmazonIpReputationList"
      sampled_requests_enabled   = true
    }
  }
  rule {
    name     = "AWS-AWSManagedRulesAnonymousIpList"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAnonymousIpList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesAnonymousIpList"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWS-AWSManagedRulesWordPressRuleSet"
    priority = 4

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesWordPressRuleSet"
        vendor_name = "AWS"
        version     = "Version_1.1"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesWordPressRuleSet"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "primary"
    sampled_requests_enabled   = true
  }
}





resource "aws_wafv2_web_acl" "block-bad-networks" {
  description   = "Provided by GlueOps"
  name          = "block-bad-networks"
  scope         = "CLOUDFRONT"
  token_domains = []

  custom_response_body {
    content      = <<-EOT
                {
                error: "HTTP 429 Too Many Requests."
                }
            EOT
    content_type = "APPLICATION_JSON"
    key          = "http_429_response"
  }

  default_action {
    allow {
    }
  }

  rule {
    name     = "AWS-AWSManagedRulesAmazonIpReputationList"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAmazonIpReputationList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesAmazonIpReputationList"
      sampled_requests_enabled   = true
    }
  }
  rule {
    name     = "AWS-AWSManagedRulesAnonymousIpList"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAnonymousIpList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesAnonymousIpList"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "primary"
    sampled_requests_enabled   = true
  }
}


resource "aws_wafv2_web_acl" "rate-limit-only" {
  description   = "Provided by GlueOps"
  name          = "rate-limit-only"
  scope         = "CLOUDFRONT"
  token_domains = []

  custom_response_body {
    content      = <<-EOT
                {
                error: "HTTP 429 Too Many Requests."
                }
            EOT
    content_type = "APPLICATION_JSON"
    key          = "http_429_response"
  }

  default_action {
    allow {
    }
  }

  rule {
    name     = "too-many-requests-per-source-ip"
    priority = 3

    action {
      block {
        custom_response {
          custom_response_body_key = "http_429_response"
          response_code            = 429
        }
      }
    }

    statement {
      rate_based_statement {
        aggregate_key_type = "IP"
        limit              = 100
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "too-many-requests-per-source-ip"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "primary"
    sampled_requests_enabled   = true
  }
}


resource "aws_wafv2_web_acl" "block-bad-networks-and-rate-limit" {
  description   = "Provided by GlueOps"
  name          = "block-bad-networks-and-rate-limit"
  scope         = "CLOUDFRONT"
  token_domains = []

  custom_response_body {
    content      = <<-EOT
                {
                error: "HTTP 429 Too Many Requests."
                }
            EOT
    content_type = "APPLICATION_JSON"
    key          = "http_429_response"
  }

  default_action {
    allow {
    }
  }

  rule {
    name     = "too-many-requests-per-source-ip"
    priority = 3

    action {
      block {
        custom_response {
          custom_response_body_key = "http_429_response"
          response_code            = 429
        }
      }
    }

    statement {
      rate_based_statement {
        aggregate_key_type = "IP"
        limit              = 100
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "too-many-requests-per-source-ip"
      sampled_requests_enabled   = true
    }
  }
  rule {
    name     = "AWS-AWSManagedRulesAmazonIpReputationList"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAmazonIpReputationList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesAmazonIpReputationList"
      sampled_requests_enabled   = true
    }
  }
  rule {
    name     = "AWS-AWSManagedRulesAnonymousIpList"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAnonymousIpList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesAnonymousIpList"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "primary"
    sampled_requests_enabled   = true
  }
}
