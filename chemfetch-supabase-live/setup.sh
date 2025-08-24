# Initialize git and install packages

echo "🔧 Initializing git repository..."
git init

echo "📦 Removing old node_modules..."
rm -rf node_modules package-lock.json

echo "📦 Installing fresh dependencies..."
npm install

echo "🔧 Setting up git hooks..."
npm run prepare

echo "✅ Setup complete! You can now run:"
echo "  npm run check-all  - Check everything"
echo "  npm run fix-all    - Fix auto-fixable issues"
echo "  npm run lint       - Run ESLint"
echo "  npm run format     - Run Prettier"
