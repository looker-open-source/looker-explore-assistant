#!/bin/bash

# Script to discover your existing load balancer configuration
PROJECT_ID="combined-genai-bi"

echo "=== Discovering Load Balancer Configuration ==="
echo ""

echo "1. Listing all URL maps in project:"
gcloud compute url-maps list --project=${PROJECT_ID}

echo ""
echo "2. Listing all backend services:"
gcloud compute backend-services list --project=${PROJECT_ID}

echo ""
echo "3. Listing all target HTTP(S) proxies:"
gcloud compute target-https-proxies list --project=${PROJECT_ID}
gcloud compute target-http-proxies list --project=${PROJECT_ID}

echo ""
echo "4. Listing all global forwarding rules:"
gcloud compute forwarding-rules list --global --project=${PROJECT_ID}

echo ""
echo "5. Looking for IAP configuration:"
gcloud iap web get-iam-policy --project=${PROJECT_ID} 2>/dev/null || echo "No IAP policies found at project level"

echo ""
echo "=== Configuration Discovery Complete ==="
echo ""
echo "Please check the output above to identify:"
echo "- The correct URL map name (to update configure-existing-lb-cors.sh)"
echo "- The backend service name (should be: exploreassistantmcpbackendservice)"
echo "- The forwarding rule names and IPs"
