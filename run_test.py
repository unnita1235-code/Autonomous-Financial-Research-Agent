import time
import requests
import json
import sys

print('Step 2: Sending POST request to start research...')
response = requests.post(
    'http://localhost:8000/research',
    json={'query': 'Analyze Apple Q3 2024 performance', 'ticker': 'AAPL'},
    headers={'Content-Type': 'application/json'}
)
data = response.json()
print(f'Response: {data}')
job_id = data['data']['job_id']

print('\nStep 3: Polling for status...')
while True:
    status_response = requests.get(f'http://localhost:8000/status/{job_id}').json()
    status = status_response['data']['status']
    print(f'Status: {status}')
    if status in ['complete', 'failed']:
        break
    time.sleep(15)

print('\nStep 4: Fetching final report...')
report_response = requests.get(f'http://localhost:8000/report/{job_id}').json()
print('\nFULL raw JSON report output:')
print(json.dumps(report_response, indent=2))
