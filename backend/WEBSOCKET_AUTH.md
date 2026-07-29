# WebSocket Job Status Authentication

## Overview

The WebSocket endpoint for real-time job status updates requires authentication to prevent unauthorized access to private job information.

## Security Features

### 1. Token-Based Authentication

- Session token required via query parameter: `?token=SESSION_TOKEN`
- Token is validated against the session database
- Invalid or expired tokens are rejected with code 4001 (Unauthorized)

### 2. Job Ownership Verification

- User must own the job to receive status updates
- Unauthorized access attempts are logged
- Non-owners are rejected with code 4003 (Forbidden)

### 3. Connection Logging

- All connections are logged with user email and job ID
- Failed authentication attempts are logged as warnings
- Connection lifecycle is tracked (connect, disconnect)

## API Endpoint

### Connect to Job Status Stream

```
WebSocket wss://kalaos.app/api/jobs/ws/{job_id}?token=SESSION_TOKEN
```

**Parameters:**
- `job_id` (path): The job ID to monitor
- `token` (query): Valid session token

**Response Codes:**
- `1000`: Normal closure (job completed)
- `1001`: Going away
- `4001`: Unauthorized (invalid token)
- `4003`: Forbidden (user doesn't own job)
- `4004`: Not found (job doesn't exist)
- `1011`: Server error

## Message Format

### Status Updates

Messages are sent as JSON objects:

```json
{
  "job_id": "job123",
  "status": "processing",
  "progress": 45,
  "message": "Processing step 3/7",
  "created_at": "2026-07-29T12:00:00Z"
}
```

### Client Requests

Clients can request status refreshes:

```json
{
  "action": "refresh"
}
```

## Implementation Details

### Authentication Flow

```
1. Client initiates WebSocket connection with token
   GET /ws/job123?token=SESSION_TOKEN

2. Server validates token
   ✓ Token valid → proceed to step 3
   ✗ Token invalid → close(4001, "Unauthorized")

3. Server verifies job exists
   ✓ Job found → proceed to step 4
   ✗ Job not found → close(4004, "Not found")

4. Server checks job ownership
   ✓ User owns job → accept connection
   ✗ User doesn't own job → close(4003, "Forbidden")

5. Send initial status and stream updates
```

### Status Update Strategy

The implementation uses two mechanisms for status updates:

1. **Client-Initiated Refresh**: Client sends `{"action": "refresh"}` message
2. **Server-Side Polling**: Server checks job status every 30 seconds

This hybrid approach works with the current job system and can be upgraded to push-based updates using:
- Message queues (Redis Pub/Sub, RabbitMQ)
- Server-Sent Events (SSE) as fallback
- Webhook callbacks from job processor

## Usage Examples

### JavaScript Client

```javascript
class JobStatusMonitor {
  constructor(jobId, token) {
    this.jobId = jobId;
    this.token = token;
    this.ws = null;
  }

  connect() {
    return new Promise((resolve, reject) => {
      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
      const url = `${protocol}//${location.host}/api/jobs/ws/${this.jobId}?token=${this.token}`;

      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        console.log('Connected to job status stream');
        resolve();
      };

      this.ws.onmessage = (event) => {
        const update = JSON.parse(event.data);
        this.onUpdate(update);
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };

      this.ws.onclose = (event) => {
        if (event.code !== 1000) {
          console.warn(`Connection closed: ${event.code} - ${event.reason}`);
        }
        this.onClose();
      };
    });
  }

  refresh() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: 'refresh' }));
    }
  }

  onUpdate(update) {
    console.log(`Job ${update.job_id} status: ${update.status}`);
    if (update.progress !== undefined) {
      console.log(`Progress: ${update.progress}%`);
    }
  }

  onClose() {
    console.log('Disconnected from job status stream');
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Usage
const monitor = new JobStatusMonitor('job123', sessionToken);
await monitor.connect();

// Manually refresh status
monitor.refresh();

// Disconnect when done
monitor.disconnect();
```

### Python Client (asyncio)

```python
import asyncio
import json
import websockets

async def monitor_job(job_id: str, token: str):
    uri = f"wss://kalaos.app/api/jobs/ws/{job_id}?token={token}"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to job {job_id}")

            while True:
                message = await websocket.recv()
                update = json.loads(message)

                print(f"Status: {update['status']}")
                if 'progress' in update:
                    print(f"Progress: {update['progress']}%")

                if update['status'] in ['completed', 'failed']:
                    break

    except websockets.exceptions.WebSocketException as e:
        print(f"Connection error: {e}")

# Usage
asyncio.run(monitor_job('job123', session_token))
```

## Error Handling

### Common Errors

| Code | Reason | Action |
|------|--------|--------|
| 4001 | Invalid token | Re-authenticate and get new token |
| 4003 | Permission denied | Only job owner can monitor |
| 4004 | Job not found | Verify job ID is correct |
| 1011 | Server error | Retry after delay |

### Retry Strategy

```javascript
async function connectWithRetry(jobId, token, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const monitor = new JobStatusMonitor(jobId, token);
      await monitor.connect();
      return monitor;
    } catch (error) {
      if (i < maxRetries - 1) {
        await new Promise(resolve => 
          setTimeout(resolve, Math.pow(2, i) * 1000)
        );
      } else {
        throw error;
      }
    }
  }
}
```

## Security Considerations

### Authentication

- ✅ Session token required (not optional)
- ✅ Token validated against database
- ✅ Invalid tokens rejected immediately

### Authorization

- ✅ Job ownership verified
- ✅ Users can only access their own jobs
- ✅ Unauthorized access attempts logged

### Limitations

- ⚠️ Token passed in query parameter (visible in logs/history)
  - **Better approach**: Pass token in WebSocket handshake headers
  - **Migration path**: Upgrade to HTTP headers-based auth

### Future Enhancements

1. **Header-Based Authentication**
   ```javascript
   // Better than query parameter
   const ws = new WebSocket('wss://kalaos.app/api/jobs/ws/job123', [], {
     headers: { 'Authorization': `Bearer ${token}` }
   });
   ```

2. **Push-Based Updates**
   - Use Redis Pub/Sub for real-time updates
   - Job processor publishes status changes
   - WebSocket server subscribes and forwards

3. **Message Subscriptions**
   - Allow subscribing to multiple job updates
   - Filter by job status or result type
   - Bulk operations monitoring

4. **Rate Limiting**
   - Limit number of WebSocket connections per user
   - Limit message frequency
   - Prevent abuse of status endpoint

## Testing

### Test Unauthenticated Access

```bash
# Should fail with 4001 (Unauthorized)
websocat "ws://localhost:8000/api/jobs/ws/job123"
```

### Test Unauthorized Access

```bash
# Should fail with 4003 (Forbidden) if job is owned by another user
websocat "ws://localhost:8000/api/jobs/ws/other_user_job?token=$MY_TOKEN"
```

### Test Authorized Access

```bash
# Should succeed and stream updates
websocat "ws://localhost:8000/api/jobs/ws/my_job?token=$MY_TOKEN"
```

## References

- [OWASP WebSocket Security](https://owasp.org/www-community/attacks/WebSocket_protocol_vulnerabilities)
- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
- [RFC 6455 - WebSocket Protocol](https://tools.ietf.org/html/rfc6455)
