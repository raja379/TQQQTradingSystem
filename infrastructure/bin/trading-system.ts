#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { TradingSystemStack } from '../lib/trading-system-stack';

const app = new cdk.App();

new TradingSystemStack(app, 'TradingSystemStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});