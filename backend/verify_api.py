import requests
import json
import os
import uuid

BASE_URL = "http://localhost:5000"
TEST_EMAIL = f"test_{uuid.uuid4().hex[:8]}@example.com"
TEST_PASSWORD = "password123"
TEST_USERNAME = f"user_{uuid.uuid4().hex[:8]}"

def print_result(name, success, message=""):
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status} {name}: {message}")

def verify_api():
    print(f"Starting API Verification on {BASE_URL}...")
    
    session = requests.Session()
    token = None
    user_id = None
    
    # 1. Register
    try:
        payload = {
            "username": TEST_USERNAME,
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        response = session.post(f"{BASE_URL}/auth/register", json=payload)
        if response.status_code == 200:
            data = response.json()
            token = data.get('token')
            user_id = data.get('user', {}).get('id')
            print_result("Register", True, f"User: {TEST_USERNAME}")
        else:
            print_result("Register", False, f"Status: {response.status_code}, Body: {response.text}")
            return
    except Exception as e:
        print_result("Register", False, str(e))
        return

    # Set Auth Header
    headers = {'Authorization': f'Bearer {token}'}
    session.headers.update(headers)

    # 2. Login (Verify login works, though we have token from register)
    try:
        payload = {
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD
        }
        response = session.post(f"{BASE_URL}/auth/login", json=payload)
        if response.status_code == 200:
            print_result("Login", True)
        else:
            print_result("Login", False, f"Status: {response.status_code}")
    except Exception as e:
        print_result("Login", False, str(e))

    # 3. Upload File (Data Route - Frontend uses this)
    # We need a sample CSV. I'll use the one in app/sample_csv/deliveries.csv
    csv_path = "app/sample_csv/deliveries.csv"
    if not os.path.exists(csv_path):
        print_result("Upload File", False, f"Sample file not found at {csv_path}")
        return

    analysis_session_id = None
    try:
        files = {'file': open(csv_path, 'rb')}
        # Frontend uses /api/data/upload
        response = session.post(f"{BASE_URL}/api/data/upload", files=files)
        if response.status_code == 200:
            data = response.json()
            analysis_session_id = data.get('session', {}).get('session_id')
            print_result("Upload File (Data)", True, f"Session ID: {analysis_session_id}")
        else:
            print_result("Upload File (Data)", False, f"Status: {response.status_code}, Body: {response.text}")
            return
    except Exception as e:
        print_result("Upload File (Data)", False, str(e))
        return

    # 4. Create Notebook (Data Route - Frontend uses this)
    notebook_id = None
    try:
        payload = {
            "session_id": analysis_session_id,
            "analysis_type": "comprehensive_eda",
            "user_context": "Initial data load" # Frontend sends this
        }
        # Frontend uses /api/data/create (which is /api/data/create in flask)
        response = session.post(f"{BASE_URL}/api/data/create", json=payload)
        if response.status_code == 200:
            data = response.json()
            notebook_id = data.get('notebook', {}).get('notebook_id')
            print_result("Create Notebook (Data)", True, f"Notebook ID: {notebook_id}")
        else:
            print_result("Create Notebook (Data)", False, f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        print_result("Create Notebook (Data)", False, str(e))

    # 5. Add Cell
    cell_id = None
    try:
        payload = {
            "session_id": analysis_session_id,
            "type": "code",
            "source": "print('Hello World')",
            "index": 0
        }
        response = session.post(f"{BASE_URL}/api/notebook/{notebook_id}/add_cell", json=payload)
        if response.status_code == 200:
            data = response.json()
            cell_id = data.get('new_cell', {}).get('id')
            print_result("Add Cell", True, f"Cell ID: {cell_id}")
        else:
            print_result("Add Cell", False, f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        print_result("Add Cell", False, str(e))

    # 6. Update Cell
    try:
        if cell_id:
            payload = {
                "session_id": analysis_session_id,
                "cell_id": cell_id,
                "content": "print('Updated Hello World')"
            }
            response = session.post(f"{BASE_URL}/api/notebook/{notebook_id}/update", json=payload)
            if response.status_code == 200:
                print_result("Update Cell", True)
            else:
                print_result("Update Cell", False, f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        print_result("Update Cell", False, str(e))

    # 7. Execute Cell
    try:
        if cell_id:
            payload = {
                "session_id": analysis_session_id,
                "cell_id": cell_id
            }
            response = session.post(f"{BASE_URL}/api/notebook/{notebook_id}/execute", json=payload)
            if response.status_code == 200:
                print_result("Execute Cell", True)
            else:
                print_result("Execute Cell", False, f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        print_result("Execute Cell", False, str(e))

    # 8. Process Instruction (Ghost Cell)
    try:
        payload = {
            "session_id": analysis_session_id,
            "instruction": "Show me the head of the dataframe"
        }
        response = session.post(f"{BASE_URL}/api/notebook/{notebook_id}/process_instruction", json=payload)
        if response.status_code == 200:
            print_result("Process Instruction", True)
        else:
            print_result("Process Instruction", False, f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        print_result("Process Instruction", False, str(e))

    # 9. Get Session Variables
    try:
        response = session.get(f"{BASE_URL}/api/notebook/session/{analysis_session_id}/variables")
        if response.status_code == 200:
            print_result("Get Session Variables", True)
        else:
            print_result("Get Session Variables", False, f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        print_result("Get Session Variables", False, str(e))

    # 10. Delete Cell
    try:
        if cell_id:
            payload = {
                "session_id": analysis_session_id,
                "cell_id": cell_id
            }
            response = session.post(f"{BASE_URL}/api/notebook/{notebook_id}/delete_cell", json=payload)
            if response.status_code == 200:
                print_result("Delete Cell", True)
            else:
                print_result("Delete Cell", False, f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        print_result("Delete Cell", False, str(e))

    # 11. Quick Analysis
    try:
        payload = {
            "session_id": analysis_session_id
        }
        response = session.post(f"{BASE_URL}/api/analysis/quick", json=payload)
        if response.status_code == 200:
            print_result("Quick Analysis", True)
        else:
            print_result("Quick Analysis", False, f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        print_result("Quick Analysis", False, str(e))

    # 12. Comprehensive Analysis
    try:
        payload = {
            "session_id": analysis_session_id,
            "analysis_type": "comprehensive",
            "focus_areas": ["trends"]
        }
        response = session.post(f"{BASE_URL}/api/analysis/comprehensive", json=payload)
        if response.status_code == 200:
            print_result("Comprehensive Analysis", True)
        else:
            print_result("Comprehensive Analysis", False, f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        print_result("Comprehensive Analysis", False, str(e))

    # 13. Session Routes (Create/Get)
    # Note: /api/session/create seems to be a separate session management from notebook upload
    # Let's test it independently
    session_id_2 = None
    try:
        payload = {
            "dataset_info": {"name": "test"}
        }
        response = session.post(f"{BASE_URL}/api/session/create", json=payload)
        if response.status_code == 200:
            data = response.json()
            session_id_2 = data.get('session', {}).get('session_id')
            print_result("Create Session (Session API)", True, f"Session ID: {session_id_2}")
        else:
            print_result("Create Session (Session API)", False, f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        print_result("Create Session (Session API)", False, str(e))

    # 14. Get Session
    try:
        if session_id_2:
            response = session.get(f"{BASE_URL}/api/session/{session_id_2}")
            if response.status_code == 200:
                print_result("Get Session", True)
            else:
                print_result("Get Session", False, f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        print_result("Get Session", False, str(e))

    # 15. Get Session Notebooks
    try:
        if session_id_2:
            response = session.get(f"{BASE_URL}/api/session/{session_id_2}/notebooks")
            if response.status_code == 200:
                print_result("Get Session Notebooks", True)
            else:
                print_result("Get Session Notebooks", False, f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        print_result("Get Session Notebooks", False, str(e))

if __name__ == "__main__":
    verify_api()
