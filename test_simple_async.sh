#!/bin/bash

# Test async generation with curl

API_URL="https://3b41y4ox0l.execute-api.eu-west-2.amazonaws.com/prod"

echo "=== Testing Async Generation ==="
echo ""

# Step 1: Register/Login
echo "Step 1: Authenticating..."
AUTH_RESPONSE=$(curl -s -X POST "$API_URL/auth" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "register",
    "username": "async_test_'$(date +%s)'",
    "password": "TestPassword123!",
    "email": "async_test_'$(date +%s)'@example.com"
  }')

echo "Auth response: $AUTH_RESPONSE"
echo ""

SESSION_TOKEN=$(echo $AUTH_RESPONSE | jq -r '.session_token')
USER_ID=$(echo $AUTH_RESPONSE | jq -r '.user_id')

echo "User ID: $USER_ID"
echo "Session Token: ${SESSION_TOKEN:0:20}..."
echo ""

# Step 2: Interpret query
echo "Step 2: Interpreting query..."
INTERPRET_RESPONSE=$(curl -s -X POST "$API_URL/interpret" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -d '{
    "query": "15 Higher Algebra questions"
  }')

echo "Interpret response: $INTERPRET_RESPONSE"
echo ""

TOPIC=$(echo $INTERPRET_RESPONSE | jq -r '.intent.topic')
TIER=$(echo $INTERPRET_RESPONSE | jq -r '.intent.tier')
COUNT=$(echo $INTERPRET_RESPONSE | jq -r '.intent.count')
ENRICHED=$(echo $INTERPRET_RESPONSE | jq -r '.enriched_prompt')

echo "Topic: $TOPIC, Tier: $TIER, Count: $COUNT"
echo ""

# Step 3: Generate questions
echo "Step 3: Generating questions..."

# Create JSON payload properly
PAYLOAD=$(jq -n \
  --arg topic "$TOPIC" \
  --arg tier "$TIER" \
  --argjson count "$COUNT" \
  --arg enriched "$ENRICHED" \
  '{topic: $topic, tier: $tier, count: $count, enriched_prompt: $enriched}')

GENERATE_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$API_URL/generate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -d "$PAYLOAD")

HTTP_STATUS=$(echo "$GENERATE_RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
RESPONSE_BODY=$(echo "$GENERATE_RESPONSE" | sed '/HTTP_STATUS/d')

echo "HTTP Status: $HTTP_STATUS"
echo "Response: $RESPONSE_BODY"
echo ""

if [ "$HTTP_STATUS" = "202" ]; then
  echo "✅ Async job created!"
  
  JOB_ID=$(echo $RESPONSE_BODY | jq -r '.job_id')
  SESSION_ID=$(echo $RESPONSE_BODY | jq -r '.session_id')
  
  echo "Job ID: $JOB_ID"
  echo "Session ID: $SESSION_ID"
  echo ""
  
  # Step 4: Poll for completion
  echo "Step 4: Polling for completion..."
  
  for i in {1..20}; do
    sleep 5
    
    POLL_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X GET "$API_URL/user/sessions/$SESSION_ID" \
      -H "Authorization: Bearer $SESSION_TOKEN")
    
    POLL_STATUS=$(echo "$POLL_RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
    POLL_BODY=$(echo "$POLL_RESPONSE" | sed '/HTTP_STATUS/d')
    
    if [ "$POLL_STATUS" = "200" ]; then
      JOB_STATUS=$(echo $POLL_BODY | jq -r '.metadata.status')
      PROGRESS=$(echo $POLL_BODY | jq -r '.metadata.progress')
      
      echo "Poll $i: Status=$JOB_STATUS, Progress=$PROGRESS%"
      
      if [ "$JOB_STATUS" = "completed" ]; then
        QUESTION_COUNT=$(echo $POLL_BODY | jq -r '.generated_questions | length')
        GEN_TIME=$(echo $POLL_BODY | jq -r '.metadata.generation_time')
        
        echo ""
        echo "✅ Generation completed!"
        echo "Questions: $QUESTION_COUNT"
        echo "Generation time: ${GEN_TIME}s"
        exit 0
      elif [ "$JOB_STATUS" = "failed" ]; then
        ERROR=$(echo $POLL_BODY | jq -r '.metadata.error')
        echo ""
        echo "❌ Generation failed: $ERROR"
        exit 1
      fi
    else
      echo "Poll $i: HTTP $POLL_STATUS (session not found yet)"
    fi
  done
  
  echo ""
  echo "❌ Timeout waiting for completion"
  exit 1
else
  echo "❌ Expected 202 Accepted, got $HTTP_STATUS"
  exit 1
fi
