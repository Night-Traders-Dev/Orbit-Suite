from logic.logic import create_order
import asyncio

async def main():
    success, result = await create_order("buy", "Orbit", 10.23, 50, "test: address")
    print(success)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
