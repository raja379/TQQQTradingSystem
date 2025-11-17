# Trading System Infrastructure

This directory contains the AWS CDK infrastructure code for the trading system.

## Architecture

The infrastructure includes:

- **EventBridge**: Daily cron trigger at 12:30 PM PST
- **Lambda Functions**: Trading orchestration and connectors
- **DynamoDB**: Transaction storage with date/ticker partitioning
- **SQS DLQ**: Dead letter queue for failed events
- **SNS**: Notifications for alerts
- **CloudWatch**: Logging and monitoring
- **Secrets Manager**: Secure API key storage

## Prerequisites

- Node.js 18+
- AWS CLI configured
- AWS CDK CLI installed: `npm install -g aws-cdk`

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Bootstrap CDK (first time only):
   ```bash
   cdk bootstrap
   ```

3. Build the project:
   ```bash
   npm run build
   ```

## Deployment

1. Review changes:
   ```bash
   npm run diff
   ```

2. Deploy stack:
   ```bash
   npm run deploy
   ```

3. Destroy stack (when needed):
   ```bash
   npm run destroy
   ```

## Configuration

Environment variables and secrets:
- API keys stored in AWS Secrets Manager
- Lambda environment variables configured automatically
- DynamoDB table name: `trading-transactions`

## Monitoring

- CloudWatch alarms for DLQ messages and Lambda errors
- SNS notifications for alerts
- Log retention: 30 days