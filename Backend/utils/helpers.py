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
        firestore_client = get_firestore_client()
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: firestore_client.collection('analyses').document(analysis_id).update(update_data)
        )
    except Exception as e:
        print(f"Failed to update progress for {analysis_id}: {e}")


async def match_user_and_analysis_id(user_id: str, analysis_id: str, include_inactive: bool = False):
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
        results = query.stream()
        
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
