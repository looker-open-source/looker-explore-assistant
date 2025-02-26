import pytest
import httpx
import asyncio

# List of mock data for testing
mock_data_list = [
    {
        "user_id": "56",
        "name": "ken",
        "email": "kiet.lt@joonsolutions.com"
    },
    {
        "user_id": "13",
        "name": "beck",
        "email": "bao.nq@joonsolutions.com"
    },
    {
        "user_id": "19",
        "name": "bach",
        "email": "nguyen.dnb@joonsolutions.com"
    }
]

@pytest.mark.asyncio
async def test_login():
    # Mock headers for the request, including a valid token
    headers = {
        "Authorization": "Bearer valid_token"
    }
    timeout = httpx.Timeout(None)

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Create a list of tasks for each request
        tasks = [
            send_request(client, mock_data, headers)
            for mock_data in mock_data_list
        ]
        # Run all tasks concurrently
        await asyncio.gather(*tasks)

async def send_request(client, mock_data, headers):
    # Log the current mock data being tested
    print(f"\nTesting with user_id: {mock_data['user_id']}")

    # Send a POST request to the /login endpoint
    response = await client.post("http://localhost:8000/login", json=mock_data, headers=headers)

    # Assert that the response status code is 200 (OK)
    assert response.status_code == 200

    # Assert that the response contains the expected data
    response_data = response.json()
    data = response_data["data"]
    message = response_data["message"]
    assert message in ("User created successfully", "User already exists")
    
    assert data["user_id"] == mock_data["user_id"]
    print(f"\nSuccessfully tested user_id: {mock_data['user_id']}")

# Run the test with pytest
if __name__ == "__main__":
    pytest.main()
