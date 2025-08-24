@echo off
echo 🔧 Initializing git repository...
git init

echo 📦 Removing old node_modules...
if exist node_modules rmdir /s /q node_modules
if exist package-lock.json del package-lock.json

echo 📦 Installing fresh dependencies...
npm install

echo 🔧 Setting up git hooks...
npm run prepare

echo ✅ Setup complete! You can now run:
echo   npm run check-all  - Check everything
echo   npm run fix-all    - Fix auto-fixable issues  
echo   npm run lint       - Run ESLint
echo   npm run format     - Run Prettier
