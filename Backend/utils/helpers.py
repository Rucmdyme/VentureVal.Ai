from fastapi import HTTPException
from typing import Dict
import asyncio
from models.database import get_firestore_client
from datetime import datetime
from constants import Collections
import logging
from firebase_admin import firestore
logger = logging.getLogger(__name__)


async def update_progress(analysis_id: str, progress: int = None, message: str = "", **kwargs: dict):
    """Update analysis progress"""
    try:
        update_data = {
            'updated_at': datetime.now()
        }
        if progress:
            update_data.update({'progress': progress})
        if message:
            update_data.update({'message': message})
        if kwargs:
            update_data.update({**kwargs})
        await db_update(analysis_id, Collections.ANALYSIS, update_data)
    except Exception as e:
        print(f"Failed to update progress for {analysis_id}: {e}")


async def match_user_and_analysis_id(user_id: str, analysis_id: str = None, include_inactive: bool = False):
    db=get_firestore_client()

    query = db.collection(Collections.USER_ANALYSIS_MAPPING).where(
            "user_id", "==", user_id
        )
    if analysis_id:
        query = query.where(
                "analysis_id", "==", analysis_id
            )
    if not include_inactive:
        query = query.where("is_active", "==", True)
    query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
    try:
        results = await asyncio.to_thread(lambda: list(query.stream()))
        
        # 5. Process and Return Data
        mappings = []
        for doc in results:
            data = doc.to_dict()
            data['id'] = doc.id # Include the document ID for reference
            mappings.append(data)
            
        logger.info(f"Retrieved {len(mappings)} mappings for user {user_id}.")
        return mappings
    except Exception as e:
        logger.error(f"Error querying analysis mappings for user {user_id}: {e}")
        return []


async def db_insert(unique_id: str, collection: str, data: dict):
    db=get_firestore_client()
    data = {**data, "created_at": datetime.now()}
    try:
        doc_ref = db.collection(collection).document(unique_id)
        await asyncio.to_thread(doc_ref.set, data)
    except Exception as db_error:
        logger.error(f"Failed to create analysis record: {db_error}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to initialize analysis"
        )
    
async def db_update(unique_id: str, collection: str, data: dict)-> dict:
    db=get_firestore_client()
    data = {**data, "updated_at": datetime.now()}
    try:
        await asyncio.to_thread(
            lambda: db.collection(collection).document(unique_id).update(data)
        )
    except Exception as db_error:
        logger.error(f"Failed to update analysis record: {db_error}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to update analysis"
        )

async def db_get(collection: str, unique_id: str)-> dict:
    db=get_firestore_client()
    try:
        doc = await asyncio.to_thread(
            lambda: db.collection(collection).document(unique_id).get()
        )
        return doc.to_dict()
    except Exception as db_error:
        logger.error(f"Failed to fetch analysis record: {db_error}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to fetch analysis"
        )


async def asyncio_gather_dict(tasks: Dict):
    """
    Gather a dictionary of Asyncio Task instances while preserving keys
    """

    async def mark(key, coroutine):
        return key, await coroutine

    return {
        key: result for key, result in await asyncio.gather(*(mark(key, coroutine) for key, coroutine in tasks.items()))
    }