#!/bin/bash

echo "🚀 Deploying Multi-Topic Feature"
echo "=================================="

# Find the S3 bucket
BUCKET=$(aws s3 ls | grep gcse | grep frontend | awk '{print $3}' | head -1)

if [ -z "$BUCKET" ]; then
    echo "❌ Could not find frontend S3 bucket"
    echo "Please run: aws s3 ls | grep gcse"
    exit 1
fi

echo "✅ Found bucket: $BUCKET"

# Sync frontend build
echo ""
echo "📦 Syncing frontend build to S3..."
aws s3 sync frontend/build/ s3://$BUCKET/ --delete

if [ $? -eq 0 ]; then
    echo "✅ Frontend deployed successfully"
else
    echo "❌ Frontend deployment failed"
    exit 1
fi

# Find CloudFront distribution
DIST_ID=$(aws cloudfront list-distributions --query "DistributionList.Items[?contains(Origins.Items[0].DomainName, '$BUCKET')].Id" --output text)

if [ -n "$DIST_ID" ]; then
    echo ""
    echo "🔄 Invalidating CloudFront cache..."
    aws cloudfront create-invalidation --distribution-id $DIST_ID --paths "/*"
    echo "✅ Cache invalidation started"
else
    echo "⚠️  Could not find CloudFront distribution (cache not invalidated)"
fi

echo ""
echo "=================================="
echo "✅ Deployment Complete!"
echo ""
echo "🎉 Multi-Topic Feature is now live!"
echo ""
echo "Test it by:"
echo "1. Select question count (e.g., 10)"
echo "2. Select tier (Foundation/Higher)"
echo "3. Click multiple topic buttons"
echo "4. Watch the query build automatically"
echo "5. Generate questions for all topics at once"
echo ""