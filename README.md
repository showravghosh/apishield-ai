# APIShield AI

APIShield AI is a smart security tool that protects APIs from attacks in real time.
It sits in front of your API. Every request passes through APIShield first.
It uses Artificial Intelligence to check each request, and it blocks attacks
before they reach your real server.

Unlike normal firewalls that only follow fixed rules, APIShield learns what
normal traffic looks like. So it can catch both known attacks and new ones.

## What it detects

1. SQL Injection
2. Brute Force Login
3. BOLA (Broken Object Level Authorization)
4. API Flooding
5. Credential Stuffing
6. Parameter Tampering
7. Token Replay

## How it works

Every request goes to the APIShield Gateway first. AI models check it.
If it is safe, it is sent to the real API. If it is an attack, it is blocked
with a 403 error, and the live dashboard shows it.

## The AI inside

APIShield uses four kinds of AI together (a layered defense):

- Tree models (Random Forest, CatBoost): fast detection of known attacks
- Isolation Forest: catches new, unknown attacks it never saw
- LSTM: understands the pattern across a whole session
- GNN: catches BOLA by looking at who accesses whose data

It also explains decisions with SHAP, and adds only about 9 ms per request.

## How to run

Install once:  ./setup.sh
Start the tool: ./run.sh
Open the dashboard: http://localhost:8080

Other commands:
  ./reset.sh   clear the dashboard to zero (before a demo)
  ./demo.sh    send live normal + attack traffic
  ./stop.sh    stop everything

To see real attacks being blocked, read DEMO_GUIDE.md

## Project structure

  test-api/           the target REST API
  traffic-generator/  scripts that create normal + attack traffic
  ml-pipeline/        preprocessing, model training, results
  gateway/            the AI security gateway (main tool)
  dashboard/          the live security dashboard

## Results

- About 97% accuracy (5-fold cross-validation, stable)
- Detection is realistic, not perfect, with explainable mistakes
- Gateway adds only ~9 ms per request

## Note

This is a research project. All attacks are run only on our own test system.
Never attack a system you do not own.
