"""
Configuration CLI Tool
Command-line interface for configuration management
"""
import os
import sys
import argparse
from typing import Dict, Any
import structlog

from .settings import get_settings, Environment
from .env_template import EnvironmentTemplate, generate_all_templates
from .factory import get_configuration_factory, ConfigurationError

logger = structlog.get_logger(__name__)


def validate_configuration():
    """Validate current configuration"""
    try:
        factory = get_configuration_factory()
        validation_results = factory.validate_configuration()

        print("🔍 Configuration Validation Results:")
        print("=" * 50)

        for component, is_valid in validation_results.items():
            status = "✅ VALID" if is_valid else "❌ INVALID"
            print(f"{component.upper():<20} {status}")

        all_valid = all(validation_results.values())

        if all_valid:
            print("\n🎉 All configuration components are valid!")
            return True
        else:
            print("\n⚠️  Some configuration components are invalid.")
            print("Please check your environment variables and configuration files.")
            return False

    except Exception as e:
        print(f"❌ Configuration validation failed: {str(e)}")
        return False


def show_configuration():
    """Display current configuration"""
    try:
        settings = get_settings()

        print("📋 Current Configuration:")
        print("=" * 50)

        # Application settings
        print("\n🖥️  Application:")
        print(f"  Name: {settings.app_name}")
        print(f"  Version: {settings.app_version}")
        print(f"  Environment: {settings.environment}")
        print(f"  Debug: {settings.debug}")
        print(f"  Host: {settings.host}:{settings.port}")

        # Database settings
        print("\n🗄️  Database:")
        print(f"  Host: {settings.database.host}:{settings.database.port}")
        print(f"  Database: {settings.database.name}")
        print(f"  User: {settings.database.user}")
        print(f"  Pool Size: {settings.database.pool_size}")
        print(f"  Echo: {settings.database.echo}")

        # AI Service settings
        print("\n🤖 AI Service:")
        print(f"  Base URL: {settings.ai_service.openai_base_url}")
        print(f"  API Key: {'***' + settings.ai_service.openai_api_key[-4:] if settings.ai_service.openai_api_key else 'Not set'}")
        print(f"  Default Model: {settings.ai_service.default_model}")
        print(f"  Timeout: {settings.ai_service.timeout_seconds}s")
        print(f"  Content Filtering: {settings.ai_service.enable_content_filtering}")

        # Cache settings
        print("\n🔴 Cache:")
        print(f"  Host: {settings.cache.redis_host}:{settings.cache.redis_port}")
        print(f"  Database: {settings.cache.redis_db}")
        print(f"  Enabled: {settings.cache.enable_cache}")
        print(f"  Default TTL: {settings.cache.default_ttl}s")

        # Security settings
        print("\n🔐 Security:")
        print(f"  CORS Origins: {settings.security.cors_origins}")
        print(f"  Rate Limiting: {settings.security.enable_rate_limiting}")
        print(f"  Trusted Hosts: {settings.security.trusted_hosts}")

        # Logging settings
        print("\n📊 Logging:")
        print(f"  Level: {settings.logging.level}")
        print(f"  JSON Format: {settings.logging.format_json}")
        print(f"  Console: {settings.logging.enable_console}")
        print(f"  File: {settings.logging.enable_file}")

        return True

    except Exception as e:
        print(f"❌ Failed to display configuration: {str(e)}")
        return False


def generate_env_template(environment: str, output_file: str = None):
    """Generate environment template"""
    try:
        env = Environment(environment.lower())

        if output_file:
            filename = EnvironmentTemplate.save_template(env, output_file)
            print(f"✅ Environment template saved to: {filename}")
        else:
            template = EnvironmentTemplate.generate_template(env)
            print(f"📝 Environment template for {environment}:")
            print("=" * 50)
            print(template)

        return True

    except ValueError as e:
        print(f"❌ Invalid environment: {environment}")
        print("Valid environments: development, testing, staging, production")
        return False
    except Exception as e:
        print(f"❌ Failed to generate template: {str(e)}")
        return False


def test_services():
    """Test external service connections"""
    try:
        print("🧪 Testing Service Connections:")
        print("=" * 50)

        factory = get_configuration_factory()

        # Test AI service
        print("\n🤖 Testing AI Service...")
        try:
            ai_service = factory.create_ai_service()
            is_healthy = await ai_service.health_check()
            print(f"   AI Service: {'✅ HEALTHY' if is_healthy else '❌ UNHEALTHY'}")
        except Exception as e:
            print(f"   AI Service: ❌ ERROR - {str(e)}")

        # Test platform service
        print("\n🌐 Testing Platform Service...")
        try:
            platform_service = factory.create_platform_service()
            if platform_service:
                is_healthy = await platform_service.health_check()
                print(f"   Platform Service: {'✅ HEALTHY' if is_healthy else '❌ UNHEALTHY'}")
            else:
                print("   Platform Service: ⚠️  NOT CONFIGURED")
        except Exception as e:
            print(f"   Platform Service: ❌ ERROR - {str(e)}")

        # Test notification service
        print("\n📧 Testing Notification Service...")
        try:
            notification_service = factory.create_notification_service()
            if notification_service:
                print("   Notification Service: ✅ CONFIGURED")
            else:
                print("   Notification Service: ⚠️  NOT CONFIGURED")
        except Exception as e:
            print(f"   Notification Service: ❌ ERROR - {str(e)}")

        return True

    except Exception as e:
        print(f"❌ Service testing failed: {str(e)}")
        return False


def generate_all_env_templates():
    """Generate all environment templates"""
    try:
        print("📝 Generating all environment templates...")

        templates = generate_all_templates()

        for env_name, template in templates.items():
            filename = f".env.{env_name}"
            with open(filename, 'w') as f:
                f.write(template)
            print(f"✅ Generated: {filename}")

        print(f"\n🎉 Generated {len(templates)} environment templates!")
        return True

    except Exception as e:
        print(f"❌ Failed to generate templates: {str(e)}")
        return False


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Chat Orchestrator Configuration CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m app.infrastructure.config.cli validate
  python -m app.infrastructure.config.cli show
  python -m app.infrastructure.config.cli generate development
  python -m app.infrastructure.config.cli generate production --output .env.prod
  python -m app.infrastructure.config.cli test-services
  python -m app.infrastructure.config.cli generate-all
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate configuration')

    # Show command
    show_parser = subparsers.add_parser('show', help='Show current configuration')

    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate environment template')
    generate_parser.add_argument('environment',
                               choices=['development', 'testing', 'staging', 'production'],
                               help='Environment type')
    generate_parser.add_argument('--output', '-o',
                               help='Output file (prints to stdout if not specified)')

    # Test services command
    test_parser = subparsers.add_parser('test-services', help='Test external service connections')

    # Generate all command
    generate_all_parser = subparsers.add_parser('generate-all', help='Generate all environment templates')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == 'validate':
            success = validate_configuration()
        elif args.command == 'show':
            success = show_configuration()
        elif args.command == 'generate':
            success = generate_env_template(args.environment, args.output)
        elif args.command == 'test-services':
            success = test_services()
        elif args.command == 'generate-all':
            success = generate_all_env_templates()
        else:
            parser.print_help()
            return 1

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())