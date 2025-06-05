from logic.logic import create_order
import asyncio

async def main():
    success, result = await create_order("buy", "Orbit", 10.23, 50, "test: address")
    type = result.get("type", {})
    order_id = type["buy_token"]["order_id"]
    print(result)
    success, result = await create_order("buy", "Orbit", 10.23, 50, "test: address", order_id=order_id, status="filled")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
