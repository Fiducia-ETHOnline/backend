#!/usr/bin/env python3
"""
Quick test script to verify OrderContract integration
Run this after setting up your .env file with actual contract addresses
"""

import asyncio
from blockchain.order_service import order_contract_service

async def test_integration():
    """Test the OrderContract integration"""
    print("🧪 Testing OrderContract Integration...")
    
    # Test 1: Check service info (should work without initialization)
    print("\n1. Checking service status...")
    service_info = order_contract_service.get_service_info()
    print(f"   Service initialized: {service_info.get('initialized', False)}")
    
    # Test 2: Try to initialize (will fail without proper env vars, but should not crash)
    print("\n2. Testing initialization (will fail without proper .env)...")
    try:
        success = await order_contract_service.initialize_service(
            order_contract_address="0x1234567890123456789012345678901234567890",  # Dummy address
            agent_controller_private_key=None
        )
        print(f"   Initialization success: {success}")
    except Exception as e:
        print(f"   Expected error (need real addresses): {type(e).__name__}")
    
    print("\n✅ Integration test complete!")
    print("\n📋 Next steps:")
    print("   1. Copy .env.example to .env")
    print("   2. Update .env with your contract addresses and keys")
    print("   3. Start your FastAPI server: python app.py")
    print("   4. Initialize service: POST /orders/initialize")
    print("   5. Test endpoints: GET /orders/health")

if __name__ == "__main__":
    asyncio.run(test_integration())