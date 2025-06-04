#!/bin/bash

# Alembic Migration Management Script
# Usage: ./makemigrations.sh [command] [options]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ALEMBIC_CONFIG="alembic.ini"
MESSAGE=""
REVISION=""
TAG=""

# Help function
show_help() {
    echo -e "${BLUE}Alembic Migration Management Script${NC}"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo "  init                     Initialize Alembic in the project"
    echo "  create                   Create a new migration"
    echo "  upgrade                  Upgrade to latest migration"
    echo "  downgrade                Downgrade to previous migration"
    echo "  current                  Show current migration"
    echo "  history                  Show migration history"
    echo "  heads                    Show head revisions"
    echo "  branches                 Show branch points"
    echo "  check                    Check if database is up to date"
    echo "  stamp                    Mark a specific revision as current"
    echo "  show                     Show details of a specific revision"
    echo ""
    echo -e "${YELLOW}Options:${NC}"
    echo "  -m, --message MSG        Message for the migration"
    echo "  -r, --revision REV       Specific revision to target"
    echo "  -t, --tag TAG           Tag for the revision"
    echo "  -c, --config FILE       Alembic config file (default: alembic.ini)"
    echo "  -h, --help              Show this help message"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 create -m \"Add user table\""
    echo "  $0 upgrade"
    echo "  $0 downgrade -r base"
    echo "  $0 stamp -r head"
    echo "  $0 show -r current"
}

# Log functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if alembic is installed
check_alembic() {
    if ! command -v alembic &> /dev/null; then
        log_error "Alembic is not installed. Please install it with: pip install alembic"
        exit 1
    fi
}

# Check if alembic.ini exists
check_config() {
    if [[ ! -f "$ALEMBIC_CONFIG" ]]; then
        log_error "Alembic config file '$ALEMBIC_CONFIG' not found."
        log_info "Run '$0 init' to initialize Alembic or specify config with -c option."
        exit 1
    fi
}

# Initialize Alembic
init_alembic() {
    log_info "Initializing Alembic..."

    if [[ -f "alembic.ini" ]]; then
        log_warning "Alembic already initialized (alembic.ini exists)"
        read -p "Do you want to reinitialize? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Initialization cancelled."
            exit 0
        fi
    fi

    alembic init alembic
    log_success "Alembic initialized successfully!"
    log_info "Please configure your database URL in alembic.ini"
}

# Create new migration
create_migration() {
    check_config

    if [[ -z "$MESSAGE" ]]; then
        log_error "Migration message is required. Use -m option."
        exit 1
    fi

    log_info "Creating new migration: $MESSAGE"

    cmd="alembic -c $ALEMBIC_CONFIG revision --autogenerate -m \"$MESSAGE\""
    if [[ -n "$TAG" ]]; then
        cmd="$cmd --rev-id $TAG"
    fi

    eval $cmd
    log_success "Migration created successfully!"
}

# Upgrade database
upgrade_db() {
    check_config

    target=${REVISION:-"head"}
    log_info "Upgrading database to: $target"

    alembic -c "$ALEMBIC_CONFIG" upgrade "$target"
    log_success "Database upgraded successfully!"
}

# Downgrade database
downgrade_db() {
    check_config

    target=${REVISION:-"-1"}
    log_info "Downgrading database to: $target"

    # Confirm downgrade
    if [[ "$target" == "base" ]]; then
        log_warning "This will downgrade to base (remove all migrations)!"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Downgrade cancelled."
            exit 0
        fi
    fi

    alembic -c "$ALEMBIC_CONFIG" downgrade "$target"
    log_success "Database downgraded successfully!"
}

# Show current revision
show_current() {
    check_config

    log_info "Current database revision:"
    alembic -c "$ALEMBIC_CONFIG" current --verbose
}

# Show migration history
show_history() {
    check_config

    log_info "Migration history:"
    alembic -c "$ALEMBIC_CONFIG" history --verbose
}

# Show head revisions
show_heads() {
    check_config

    log_info "Head revisions:"
    alembic -c "$ALEMBIC_CONFIG" heads --verbose
}

# Show branch points
show_branches() {
    check_config

    log_info "Branch points:"
    alembic -c "$ALEMBIC_CONFIG" branches --verbose
}

# Check if database is up to date
check_db() {
    check_config

    log_info "Checking database status..."

    current=$(alembic -c "$ALEMBIC_CONFIG" current --verbose 2>/dev/null | head -n 1)
    head=$(alembic -c "$ALEMBIC_CONFIG" heads --verbose 2>/dev/null | head -n 1)

    if [[ "$current" == "$head" ]]; then
        log_success "Database is up to date!"
    else
        log_warning "Database is not up to date!"
        echo "Current: $current"
        echo "Head: $head"
        exit 1
    fi
}

# Stamp specific revision
stamp_revision() {
    check_config

    if [[ -z "$REVISION" ]]; then
        log_error "Revision is required for stamp command. Use -r option."
        exit 1
    fi

    log_info "Stamping database with revision: $REVISION"
    alembic -c "$ALEMBIC_CONFIG" stamp "$REVISION"
    log_success "Database stamped successfully!"
}

# Show revision details
show_revision() {
    check_config

    target=${REVISION:-"current"}
    log_info "Showing revision details: $target"
    alembic -c "$ALEMBIC_CONFIG" show "$target"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--message)
            MESSAGE="$2"
            shift 2
            ;;
        -r|--revision)
            REVISION="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -c|--config)
            ALEMBIC_CONFIG="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        init|create|upgrade|downgrade|current|history|heads|branches|check|stamp|show)
            COMMAND="$1"
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check if alembic is available
check_alembic

# Execute command
case "${COMMAND:-}" in
    init)
        init_alembic
        ;;
    create)
        create_migration
        ;;
    upgrade)
        upgrade_db
        ;;
    downgrade)
        downgrade_db
        ;;
    current)
        show_current
        ;;
    history)
        show_history
        ;;
    heads)
        show_heads
        ;;
    branches)
        show_branches
        ;;
    check)
        check_db
        ;;
    stamp)
        stamp_revision
        ;;
    show)
        show_revision
        ;;
    "")
        log_error "No command specified."
        show_help
        exit 1
        ;;
    *)
        log_error "Unknown command: $COMMAND"
        show_help
        exit 1
        ;;
esac
