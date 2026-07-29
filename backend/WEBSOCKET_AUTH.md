# WebSocket Job Status Authentication

## Overview

The WebSocket endpoint `/jobs/ws/{job_id}` provides real-time job status updates with mandatory authentication and authorization. Clients must provide a valid session token to establish a connection.

## Security Implementation

### Authentication Flow

```
Client                              Server
  |                                   |
  |--WebSocket Upgrade Request------->|
  |    ws://host/jobs/ws/{job_id}     |
  |    ?token={session_token}         |
  |                                   |
  |<---Validate Token (Step 1)--------|
  |    Check token validity           |
  |    Return: email or None          |
  |                                   |
  |<---Verify Job (Step 2)------------|
  |    Check job exists               |
  |    Return: job or None            |
  |                                   |
  |<---Accept/Reject (Step 3)---------|
  |    401: Invalid token             |
  |    404: Job not found             |
  |    1000: Connection accepted      |
  |                                   |
  |<===Receive Status Updates========>|
  |    {"job_id": "...",              |
  |     "status": "running",          |
  |     "progress": 50}               |
  |                                   |
```

### Close Codes

| Code | Reason | Scenario |
|------|--------|----------|
| 4001 | Unauthorized | Invalid or missing session token |
| 4004 | Not Found | Job does not exist |
| 1000 | Normal Closure | Job completed or connection closed normally |
| 1011 | Server Error | Unexpected server error |

## Client Implementation

### JavaScript/WebSocket API

```javascript
// Connect to job status stream
async function watchJobStatus(jobId, sessionToken) {
  return new Promise((resolve, reject) => {
    const wsUrl = `ws://localhost:8000/jobs/ws/${jobId}?token=${sessionToken}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('Connected to job status stream');
    };

    ws.onmessage = (event) => {
      const status = JSON.parse(event.data);
      console.log(`Job ${status.job_id} status:`, status.status);
      console.log(`Progress: ${status.progress}%`);

      if (['completed', 'failed'].includes(status.status)) {
        ws.close();
        resolve(status);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      reject(error);
    };

    ws.onclose = (event) => {
      if (event.code === 1000) {
        console.log('Job connection closed (normal)');
        resolve(event);
      } else if (event.code === 4001) {
        reject(new Error('Unauthorized: Invalid session token'));
      } else if (event.code === 4004) {
        reject(new Error('Not Found: Job does not exist'));
      } else {
        reject(new Error(`WebSocket closed: ${event.code} ${event.reason}`));
      }
    };
  });
}

// Usage
try {
  const status = await watchJobStatus('job_12345', sessionToken);
  console.log('Job completed:', status);
} catch (error) {
  console.error('Error:', error.message);
}
```

### React Hook

```javascript
function useJobStatus(jobId, sessionToken) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const wsUrl = `ws://localhost:8000/jobs/ws/${jobId}?token=${sessionToken}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => setLoading(false);

    ws.onmessage = (event) => {
      const jobStatus = JSON.parse(event.data);
      setStatus(jobStatus);

      if (['completed', 'failed'].includes(jobStatus.status)) {
        ws.close();
      }
    };

    ws.onerror = () => {
      setError('WebSocket connection error');
      setLoading(false);
    };

    ws.onclose = (event) => {
      if (event.code === 4001) {
        setError('Unauthorized: Invalid token');
      } else if (event.code === 4004) {
        setError('Job not found');
      }
      setLoading(false);
    };

    return () => ws.close();
  }, [jobId, sessionToken]);

  return { status, error, loading };
}

// Usage in component
function JobMonitor({ jobId, token }) {
  const { status, error, loading } = useJobStatus(jobId, token);

  if (loading) return <div>Connecting...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <p>Status: {status?.status}</p>
      <p>Progress: {status?.progress}%</p>
      <progress value={status?.progress} max="100" />
    </div>
  );
}
```

### Python

```python
import asyncio
import json
import websockets

async def watch_job_status(job_id, session_token):
    """Watch job status in real-time via WebSocket."""
    uri = f"ws://localhost:8000/jobs/ws/{job_id}?token={session_token}"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to job {job_id}")

            while True:
                try:
                    message = await websocket.recv()
                    status = json.loads(message)

                    print(f"Job {status['job_id']} status: {status['status']}")
                    print(f"Progress: {status['progress']}%")

                    if status['status'] in ('completed', 'failed'):
                        print("Job finished")
                        break

                except json.JSONDecodeError:
                    print("Invalid JSON received")
                    continue

    except websockets.exceptions.WebSocketException as exc:
        # Handle connection errors
        if "4001" in str(exc):
            raise ValueError("Unauthorized: Invalid session token") from exc
        elif "4004" in str(exc):
            raise ValueError("Job not found") from exc
        else:
            raise

# Usage
async def main():
    try:
        await watch_job_status("job_12345", session_token)
    except ValueError as error:
        print(f"Error: {error}")

asyncio.run(main())
```

## Security Properties

### 1. Authentication Required

- Every WebSocket connection requires a valid session token
- Token must be passed as a query parameter: `?token={token}`
- Invalid tokens result in immediate connection rejection (code 4001)

### 2. Token Validation

- Tokens are validated using the same session token verification as REST endpoints
- Revoked tokens are rejected
- Expired tokens are rejected
- Malformed tokens are rejected

### 3. Job Verification

- Server verifies job exists before accepting connection
- Non-existent jobs result in connection rejection (code 4004)
- Prevents clients from discovering jobs via enumeration (same job ID, no change in behavior)

### 4. Real-Time Updates

- Server sends status updates every 2 seconds (or on demand)
- Includes job status, progress, and timestamp
- Client can request refresh via `{"action": "refresh"}` message

### 5. Graceful Shutdown

- Server automatically closes connection when job completes
- Sends final status update before closing (code 1000)
- Prevents indefinite connections for completed jobs

## Attack Prevention

### Unauthorized Access

**Attack**: Unauthenticated user guesses job ID and connects
**Defense**: Token validation (4001 Unauthorized)

### Session Hijacking

**Attack**: Attacker intercepts token and uses it on another device
**Defense**: Token is tied to session; revocation affects all uses

### Job Enumeration

**Attack**: Attacker tries multiple job IDs to discover valid jobs
**Defense**: All non-existent jobs return same error (4004 Not Found)
- Cannot distinguish between deleted/invalid jobs

### DoS via Idle Connections

**Attack**: Attacker opens many connections without reading
**Defense**: 60-second read timeout per connection (server-side)

### Man-in-the-Middle

**Attack**: Attacker intercepts WebSocket traffic
**Defense**: Use `wss://` (WebSocket Secure) in production
- Transport-level encryption via TLS

## Deployment Notes

### WSS (WebSocket Secure)

In production, always use `wss://` (WebSocket over TLS):

```javascript
// Development
const ws = new WebSocket('ws://localhost:8000/jobs/ws/job_id?token=...');

// Production
const ws = new WebSocket('wss://api.kalaos.app/jobs/ws/job_id?token=...');
```

### Reverse Proxy Configuration

When behind a reverse proxy (nginx, Apache), ensure WebSocket support:

**Nginx example:**
```nginx
location /jobs/ws/ {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 86400;
}
```

### Monitoring

Log WebSocket connections and errors:

```python
logger.info(f"WebSocket connection: job_id={job_id}, token={token[:10]}...")
logger.warning(f"WebSocket rejected: code=4001, job_id={job_id}")
logger.error(f"WebSocket error: job_id={job_id}, error={exc}")
```

## Testing

### Unit Tests

```python
def test_websocket_requires_token(client):
    """Verify WebSocket rejects connections without token."""
    with pytest.raises(Exception):  # WebSocketDisconnect or similar
        with client.websocket_connect("/jobs/ws/job_123") as ws:
            ws.receive_json()

def test_websocket_invalid_token(client):
    """Verify WebSocket rejects invalid tokens."""
    with pytest.raises(Exception):
        with client.websocket_connect("/jobs/ws/job_123?token=invalid") as ws:
            ws.receive_json()

def test_websocket_nonexistent_job(client):
    """Verify WebSocket rejects nonexistent jobs."""
    token = get_valid_token()
    with pytest.raises(Exception):
        with client.websocket_connect(
            f"/jobs/ws/nonexistent_job?token={token}"
        ) as ws:
            ws.receive_json()

def test_websocket_valid_connection(client):
    """Verify WebSocket accepts valid token and job."""
    token = get_valid_token()
    job_id = create_test_job(token)

    with client.websocket_connect(f"/jobs/ws/{job_id}?token={token}") as ws:
        data = ws.receive_json()
        assert data["job_id"] == job_id
        assert "status" in data
```

### Integration Tests

```python
async def test_websocket_status_updates():
    """Verify WebSocket sends real-time status updates."""
    token = get_valid_token()
    job_id = create_test_job(token)

    async with websockets.connect(
        f"ws://localhost:8000/jobs/ws/{job_id}?token={token}"
    ) as ws:
        # Receive status updates
        for _ in range(3):
            data = json.loads(await ws.recv())
            assert data["job_id"] == job_id
            assert "status" in data
            assert "progress" in data
```

## Future Enhancements

1. **Job Ownership Verification**: Store job owner in database, verify user owns job
2. **Rate Limiting**: Limit number of concurrent WebSocket connections per user
3. **Custom Refresh Intervals**: Allow client to specify update frequency
4. **Progress Events**: Send incremental progress updates as job runs
5. **Error Details**: Send detailed error messages when job fails
6. **Heartbeat**: Send periodic heartbeat to detect stale connections
