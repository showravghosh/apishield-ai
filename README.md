# APIShield AI

APIShield AI is a smart security tool that protects APIs from attacks in real time.
It sits in front of an API. Every request goes through APIShield first. It uses
Artificial Intelligence to check each request and blocks attacks before they reach
the real server. Unlike normal firewalls that only follow fixed rules, APIShield
learns what normal traffic looks like, so it can catch both known and new attacks.

It detects 7 attack types: SQL Injection, Brute Force Login, BOLA, API Flooding,
Credential Stuffing, Parameter Tampering, and Token Replay.


## 1. Requirements (install these first)

You need a Linux machine (we use Kali Linux). Install these tools:

    sudo apt update
    sudo apt install -y python3 python3-venv git docker.io docker-compose sqlmap
    sudo systemctl enable --now docker
    sudo usermod -aG docker $USER

Log out and log back in once (so Docker works without sudo).


## 2. Download the project

    git clone https://github.com/showravghosh/apishield-ai.git
    cd apishield-ai


## 3. Install (one time)

This creates the Python environments and installs all libraries:

    ./setup.sh

Wait until it prints "Setup complete".


## 4. Start the tool (one command)

    ./run.sh

This starts four things automatically:
  - the database (PostgreSQL, in Docker)
  - the backend API (port 8000)
  - the AI security gateway (port 9000)
  - the dashboard (port 8080)


## 5. Open the dashboard

In your browser, open:

    http://localhost:8080

You will see live stats: total requests, allowed, blocked, threat level,
attack types, and a table of recent decisions.


## 6. Use it / see attacks being blocked

Clear the dashboard to zero (good before a demo):

    ./reset.sh

Then send live normal + attack traffic:

    ./demo.sh      (press Ctrl+C to stop it)

Or run real attacks yourself and watch them get blocked. See DEMO_GUIDE.md for
the exact commands for all 7 attacks (including sqlmap).


## 7. Stop everything

    ./stop.sh


## How it works

    User request  ->  APIShield Gateway  ->  AI checks it  ->  decision
                                                              |
                                  Safe   -> sent to the real API (allowed)
                                  Attack -> BLOCKED (403), shown on the dashboard


## The AI inside (layered defense)

No single model is best at everything, so APIShield uses four together:
  - Random Forest and CatBoost : fast detection of known attacks
  - Isolation Forest           : catches new / zero-day attacks it never saw
  - LSTM (deep learning)        : understands the pattern of a whole session
  - GNN (graph neural network)  : catches BOLA (who accesses whose data)

It also explains its decisions with SHAP (why a request was blocked), and it
adds only about 9 milliseconds per request, so it works in real time.


## Project structure

    test-api/           the target REST API (login, products, cart, users, orders)
    traffic-generator/  scripts that create normal + attack traffic (the dataset)
    ml-pipeline/        data preprocessing, model training, results and charts
    gateway/            the AI security gateway (the main tool)
    dashboard/          the live security dashboard
    setup.sh run.sh stop.sh reset.sh demo.sh   helper scripts


## Results (on our own dataset)

  - About 97% accuracy (5-fold cross-validation, stable results)
  - Detection is realistic (not a fake 100%), with explainable mistakes
  - Anomaly detector catches attacks it was never trained on
  - Gateway adds only ~9 ms per request


## Troubleshooting

  - Dashboard does not open: run  pgrep -f uvicorn  (you should see 3 numbers).
    If not, check logs: cat /tmp/apishield_gateway.log
  - "docker: permission denied": log out and back in, or run with sudo.
  - Port already in use: run ./stop.sh first, then ./run.sh again.


## Note

This is a research project. All attacks are run only on our own test system,
in a controlled environment. Never attack a system you do not own.
