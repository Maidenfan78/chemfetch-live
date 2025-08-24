#!/bin/bash

# ChemFetch Supabase Development Helper Script

set -e

echo "🧪 ChemFetch Supabase Development Helper"
echo "======================================="

# Function to show help
show_help() {
    echo "Usage: ./dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  setup      - Initial project setup"
    echo "  check      - Run all quality checks"
    echo "  fix        - Fix all auto-fixable issues"
    echo "  types      - Generate database types"
    echo "  migrate    - Apply migrations"
    echo "  reset      - Reset local database"
    echo "  help       - Show this help message"
    echo ""
}

# Function to setup the project
setup_project() {
    echo "📦 Installing dependencies..."
    npm install
    
    echo "🔧 Setting up git hooks..."
    npm run prepare
    
    echo "✅ Project setup complete!"
    echo "Next steps:"
    echo "1. Link to your Supabase project: supabase link --project-ref your-ref"
    echo "2. Apply migrations: ./dev.sh migrate"
    echo "3. Generate types: ./dev.sh types"
}

# Function to run quality checks
run_checks() {
    echo "🔍 Running quality checks..."
    npm run check-all
    echo "✅ All checks passed!"
}

# Function to fix issues
fix_issues() {
    echo "🔧 Fixing auto-fixable issues..."
    npm run fix-all
    echo "✅ All fixes applied!"
}

# Function to generate types
generate_types() {
    echo "📝 Generating database types..."
    if command -v supabase &> /dev/null; then
        supabase gen types typescript --local > supabase/database.types.ts 2>/dev/null || \
        supabase gen types typescript > supabase/database.types.ts
        echo "✅ Types generated!"
    else
        echo "❌ Supabase CLI not found. Please install it first:"
        echo "npm install -g supabase"
    fi
}

# Function to apply migrations
apply_migrations() {
    echo "🗄️ Applying migrations..."
    if command -v supabase &> /dev/null; then
        supabase db push
        echo "✅ Migrations applied!"
    else
        echo "❌ Supabase CLI not found. Please install it first:"
        echo "npm install -g supabase"
    fi
}

# Function to reset database
reset_database() {
    echo "🔄 Resetting local database..."
    if command -v supabase &> /dev/null; then
        supabase db reset
        echo "✅ Database reset!"
    else
        echo "❌ Supabase CLI not found. Please install it first:"
        echo "npm install -g supabase"
    fi
}

# Main script logic
case "${1:-help}" in
    setup)
        setup_project
        ;;
    check)
        run_checks
        ;;
    fix)
        fix_issues
        ;;
    types)
        generate_types
        ;;
    migrate)
        apply_migrations
        ;;
    reset)
        reset_database
        ;;
    help|*)
        show_help
        ;;
esac
