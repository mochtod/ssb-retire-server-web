import requests
import os

AAP_URL = os.environ.get('AAP_URL', 'https://ansibleaap.chrobinson.com')
TOKEN = os.environ.get('AAP_TOKEN', '22tTr8IldpcV9A5w6mAgUxwkZLjHk7')  # Fallback for development
TEMPLATE_ID = int(os.environ.get('AAP_TEMPLATE_ID', '66'))

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

payload = {
    "extra_vars": {
        "record_names": [
            "fq2pi2web3",
            "fq2pi2web4",
            "fqkctestrate01",
            "chr2in2ap209"
        ],
        "schedule_shutdown_date": "2025/04/04",
        "schedule_retire_date": "2025/04/11",
        "schedule_shutdown_time": "12:00:00",
        "schedule_retire_time": "12:30:00",
        "dns_server": ["10.68.64.100", "10.68.64.101"],
        "dns_zone": "freightquote.com"
    }
}

response = requests.post(
    f"{AAP_URL}/api/v2/job_templates/{TEMPLATE_ID}/launch/",
    headers=headers,
    json=payload
)

if response.status_code == 201:
    job_id = response.json().get("id")
    print(f"Job launched successfully! Job ID: {job_id}")
else:
    print("Job launch failed!", response.status_code, response.text)
