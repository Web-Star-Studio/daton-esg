#!/bin/sh
set -eu

if awslocal s3api head-bucket --bucket "$S3_BUCKET_NAME" >/dev/null 2>&1; then
  echo "Bucket $S3_BUCKET_NAME already exists"
else
  awslocal s3 mb "s3://$S3_BUCKET_NAME"
  echo "Created bucket $S3_BUCKET_NAME"
fi
