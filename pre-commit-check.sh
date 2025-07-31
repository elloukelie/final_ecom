#!/bin/bash

echo "🔍 Pre-commit Security Check"
echo "============================"

# Check for sensitive files
echo "📁 Checking for sensitive files..."
if [[ -f ".env" ]]; then
    if git check-ignore .env > /dev/null; then
        echo "✅ .env file is properly ignored"
    else
        echo "❌ WARNING: .env file is not ignored!"
        exit 1
    fi
fi

# Check for hardcoded secrets in code
echo "🔐 Checking for hardcoded secrets..."
SECRET_PATTERNS=("sk-[a-zA-Z0-9]{48}" "mysql://.*:[^@]*@" "postgresql://.*:[^@]*@")
for pattern in "${SECRET_PATTERNS[@]}"; do
    if grep -r -E "$pattern" --exclude-dir=.git --exclude-dir=__pycache__ --exclude-dir=.venv --exclude="pre-commit-check.sh" . > /dev/null; then
        echo "❌ WARNING: Potential secret found matching pattern: $pattern"
        echo "   Files containing potential secrets:"
        grep -r -E "$pattern" --exclude-dir=.git --exclude-dir=__pycache__ --exclude-dir=.venv --exclude="pre-commit-check.sh" . | head -5
        exit 1
    fi
done
echo "✅ No hardcoded secrets found"

# Check Docker Compose syntax
echo "🐳 Validating Docker Compose..."
if command -v docker &> /dev/null; then
    if docker compose config > /dev/null 2>&1; then
        echo "✅ Docker Compose configuration is valid"
    else
        echo "❌ Docker Compose configuration has errors"
        exit 1
    fi
else
    echo "⚠️ Docker not found, skipping Docker Compose validation"
fi

# Check Python syntax
echo "🐍 Checking Python syntax..."
python_files=$(find . -name "*.py" -not -path "./.venv/*" -not -path "./__pycache__/*")
for file in $python_files; do
    if ! python3 -m py_compile "$file" 2>/dev/null; then
        echo "❌ Syntax error in: $file"
        exit 1
    fi
done
echo "✅ All Python files have valid syntax"

# Check for .env.example
echo "📋 Checking for .env.example..."
if [[ -f ".env.example" ]]; then
    echo "✅ .env.example exists"
else
    echo "❌ .env.example is missing"
    exit 1
fi

echo ""
echo "🎉 All checks passed! Repository is ready for commit."
echo ""
echo "💡 Quick start for users:"
echo "   1. cp .env.example .env"
echo "   2. Edit .env with your values"
echo "   3. docker compose up -d"
echo "   4. Open http://localhost:8501"
