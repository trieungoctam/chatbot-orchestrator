#!/usr/bin/env python3

import asyncio
import sys
sys.path.append('.')

from app.clients.platform_client import get_platform_client
from app.services.message_handler import ConfigurationService

async def test_platform_history():
    """Test the platform client get_conversation_history method with specific ID."""

    platform_client = get_platform_client()
    config_service = ConfigurationService()

    # Test conversation ID provided by user
    conversation_id = "613512425187747_9726023860843256"

    print(f"Testing Platform History Retrieval")
    print(f"="*50)
    print(f"Conversation ID: {conversation_id}")
    print()

    # Try to get the actual Pancake platform configuration
    try:
        print("1. Attempting to get Pancake platform config from database...")
        platform_config = await config_service.get_platform_config("6a84846a-559c-4ba9-9282-cb661806c082")
        print(f"✓ Found platform config: {platform_config['name']} at {platform_config['base_url']}")
    except Exception as e:
        print(f"✗ Failed to get Pancake platform config: {e}")
        print("Trying default platform config...")
        try:
            platform_config = await config_service.get_platform_config("default")
            print(f"✓ Found default platform config: {platform_config['name']} at {platform_config['base_url']}")
        except Exception as e2:
            print(f"✗ Failed to get default platform config: {e2}")
            print("Using fallback localhost configuration...")
            platform_config = {
                "id": "default",
                "name": "Test Platform",
                "base_url": "http://localhost:8000",
                "rate_limit_per_minute": 60,
                "auth_token": None,
                "meta_data": {}
            }

    print(f"Platform URL: {platform_config['base_url']}")
    print(f"Request URL: {platform_config['base_url']}/history-chat")
    print(f"Request Method: POST")
    print(f"Request Params: {{'conversation_id': '{conversation_id}'}}")
    print()

    try:
        print("2. Making request to platform...")
        result = await platform_client.get_conversation_history(
            conversation_id=conversation_id,
            platform_config=platform_config
        )

        print("\n" + "="*50)
        print("PLATFORM RESPONSE:")
        print("="*50)
        print(f"Success: {result.get('success', 'N/A')}")
        print(f"Conversation ID: {result.get('conversation_id', 'N/A')}")
        print(f"History Length: {len(result.get('history', ''))}")
        print(f"Has Resources: {bool(result.get('resources', {}))}")

        if result.get('success'):
            history = result.get('history', '')
            if history:
                print(f"History Preview: '{history[:200]}{'...' if len(history) > 200 else ''}'")
            else:
                print("History: (empty)")

            resources = result.get('resources', {})
            if resources:
                print(f"Resources: {resources}")
            else:
                print("Resources: (empty)")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")

        print("\n" + "="*50)
        print("RAW RESPONSE:")
        print("="*50)
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\nEXCEPTION OCCURRED:")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up the client session
        try:
            await platform_client.close()
        except:
            pass

async def list_available_platforms():
    """List available platform configurations."""
    platform_client = get_platform_client()

    print("\n" + "="*50)
    print("AVAILABLE PLATFORM CONFIGURATIONS:")
    print("="*50)

    try:
        platforms = await platform_client.list_available_platforms()
        if platforms:
            for i, platform in enumerate(platforms, 1):
                print(f"{i}. {platform['name']} (ID: {platform['id']})")
                print(f"   Base URL: {platform['base_url']}")
                print(f"   Rate Limit: {platform['rate_limit_per_minute']}/min")
                print()
        else:
            print("No active platform configurations found.")
    except Exception as e:
        print(f"Error listing platforms: {e}")

    try:
        await platform_client.close()
    except:
        pass

async def test_pancake_platform_directly():
    """Test Pancake platform directly with hardcoded config."""
    platform_client = get_platform_client()
    conversation_id = "613512425187747_9726023860843256"

    # Direct Pancake platform configuration
    pancake_config = {
        "id": "6a84846a-559c-4ba9-9282-cb661806c082",
        "name": "Pancake",
        "base_url": "http://103.141.140.71:13894/api/v1",
        "rate_limit_per_minute": 60,
        "auth_token": None,
        "meta_data": {}
    }

    print("\n" + "="*50)
    print("TESTING PANCAKE PLATFORM DIRECTLY:")
    print("="*50)
    print(f"Conversation ID: {conversation_id}")
    print(f"Platform URL: {pancake_config['base_url']}")
    print(f"Request URL: {pancake_config['base_url']}/history-chat")

    try:
        result = await platform_client.get_conversation_history(
            conversation_id=conversation_id,
            platform_config=pancake_config
        )

        print(f"\nSuccess: {result.get('success', 'N/A')}")
        print(f"Error: {result.get('error', 'None')}")
        print(f"History Length: {len(result.get('history', ''))}")

        if result.get('success') and result.get('history'):
            history = result.get('history', '')
            print(f"History Preview: '{history[:500]}{'...' if len(history) > 500 else ''}'")

        print("\nFull Response:")
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

    finally:
        try:
            await platform_client.close()
        except:
            pass

async def main():
    """Main test function."""
    await list_available_platforms()
    await test_platform_history()
    await test_pancake_platform_directly()

if __name__ == "__main__":
    asyncio.run(main())