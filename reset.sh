#!/bin/bash
cd "$(dirname "$0")"
> gateway/gateway_decisions.csv
echo "timestamp,ip,method,endpoint,predicted,risk,decision" > gateway/gateway_decisions.csv
echo "Dashboard stats reset to zero."
