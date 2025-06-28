import asyncio
from fastapi import BackgroundTasks
from .deps import is_milestone, get_chain, get_active_nodes
from .config import settings
from .services import distribute_fees

async def maybe_distribute_fees(background_tasks: BackgroundTasks):
    chain = get_chain()
    if is_milestone(len(chain)):
        # schedule non‐blocking distribution
        background_tasks.add_task(
            distribute_fees,
            get_active_nodes(),
            settings.fee_collector
        )