import asyncio
from models.database import get_firestore_client
from datetime import datetime


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