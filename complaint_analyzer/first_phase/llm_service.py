import aiohttp
import asyncio
import logging

logger = logging.getLogger(__name__)

LLM_AUDIT_ENDPOINT = "http://localhost:8000/audit/transaction"
MAX_CONCURRENT_REQUESTS = 20

async def _audit_single(txn, session, semaphore):
    """
    Sends a single transaction to the LLM auditor asynchronously.
    """
    async with semaphore:
        try:
            async with session.post(
                LLM_AUDIT_ENDPOINT,
                json={"transaction": txn},
                timeout=aiohttp.ClientTimeout(total=2)
            ) as response:
                if response.status == 200:
                    corrected = await response.json()
                    return {"original": txn, "corrected": corrected, "status": "success"}
                else:
                    logger.warning(f"LLM Auditor returned status code {response.status}")
                    return {"original": txn, "corrected": None, "status": "failed"}
        except asyncio.TimeoutError:
            # logger.error("LLM Auditor request timed out.") # Silenced to prevent terminal spam
            return {"original": txn, "corrected": None, "status": "timeout"}
        except Exception as e:
            logger.error(f"LLM Auditor request failed: {e}")
            return {"original": txn, "corrected": None, "status": "error"}

async def audit_transactions_async(transactions):
    """
    Takes a list of low-quality transactions and processes them concurrently
    using the LLM microservice.
    """
    if not transactions:
        return []
        
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    # We use a single ClientSession for connection pooling and speed
    async with aiohttp.ClientSession() as session:
        tasks = [_audit_single(txn, session, semaphore) for txn in transactions]
        results = await asyncio.gather(*tasks)
        return results

async def post_async(url: str, payload: dict):
    """Generic async POST helper."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"POST {url} failed with status {response.status}")
                    return None
        except Exception as e:
            logger.error(f"POST {url} failed: {e}")
            return None

def run_llm_audit_batch(transactions):
    """
    Synchronous wrapper to run the async audit batch.
    """
    return asyncio.run(audit_transactions_async(transactions))
