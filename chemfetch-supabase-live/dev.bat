@echo off
setlocal enabledelayedexpansion

echo 🧪 ChemFetch Supabase Development Helper
echo =======================================

if "%1"=="" goto :help
if "%1"=="help" goto :help
if "%1"=="setup" goto :setup
if "%1"=="check" goto :check
if "%1"=="fix" goto :fix
if "%1"=="types" goto :types
if "%1"=="migrate" goto :migrate
if "%1"=="reset" goto :reset
goto :help

:help
echo Usage: dev.bat [command]
echo.
echo Commands:
echo   setup      - Initial project setup
echo   check      - Run all quality checks
echo   fix        - Fix all auto-fixable issues
echo   types      - Generate database types
echo   migrate    - Apply migrations
echo   reset      - Reset local database
echo   help       - Show this help message
echo.
goto :end

:setup
echo 📦 Installing dependencies...
call npm install
if errorlevel 1 goto :error

echo 🔧 Setting up git hooks...
call npm run prepare
if errorlevel 1 goto :error

echo ✅ Project setup complete!
echo Next steps:
echo 1. Link to your Supabase project: supabase link --project-ref your-ref
echo 2. Apply migrations: dev.bat migrate
echo 3. Generate types: dev.bat types
goto :end

:check
echo 🔍 Running quality checks...
call npm run check-all
if errorlevel 1 goto :error
echo ✅ All checks passed!
goto :end

:fix
echo 🔧 Fixing auto-fixable issues...
call npm run fix-all
if errorlevel 1 goto :error
echo ✅ All fixes applied!
goto :end

:types
echo 📝 Generating database types...
where supabase >nul 2>nul
if errorlevel 1 (
    echo ❌ Supabase CLI not found. Please install it first:
    echo npm install -g supabase
    goto :end
)
supabase gen types typescript --local > supabase\database.types.ts 2>nul || supabase gen types typescript > supabase\database.types.ts
if errorlevel 1 goto :error
echo ✅ Types generated!
goto :end

:migrate
echo 🗄️ Applying migrations...
where supabase >nul 2>nul
if errorlevel 1 (
    echo ❌ Supabase CLI not found. Please install it first:
    echo npm install -g supabase
    goto :end
)
call supabase db push
if errorlevel 1 goto :error
echo ✅ Migrations applied!
goto :end

:reset
echo 🔄 Resetting local database...
where supabase >nul 2>nul
if errorlevel 1 (
    echo ❌ Supabase CLI not found. Please install it first:
    echo npm install -g supabase
    goto :end
)
call supabase db reset
if errorlevel 1 goto :error
echo ✅ Database reset!
goto :end

:error
echo ❌ Command failed with error code %errorlevel%
exit /b %errorlevel%

:end
