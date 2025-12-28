#!/bin/bash
"""
Commit Recent Changes to Version Control

This script helps commit all the recent improvements to your repository.
"""

echo "🔄 COMMITTING RECENT CHANGES TO VERSION CONTROL"
echo "=" * 60

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "❌ No git repository found. Initialize with:"
    echo "   git init"
    echo "   git remote add origin <your-repo-url>"
    exit 1
fi

echo "📊 Checking current status..."
git status

echo -e "\n📝 Adding new files..."

# Add all new scripts and tools
git add clear_all_caches.py
git add test_cache_fix.py
git add upload_missing_examples.py
git add ai_knowledge_upload_system.py
git add enhanced_ai_integration.py
git add upload_interface.py
git add question_bank_processor.py
git add ai_context_manager.py
git add lambda_instruction_integration.py
git add pdf_collection_guide.md
git add AI_KNOWLEDGE_BASE_SETUP_COMPLETE.md

# Add instruction files
git add ai_instructions/

# Add modified core files
git add src/utils/cache.py
git add src/services/bedrock_service.py
git add frontend/src/utils/mathJax.ts
git add frontend/src/components/QuestionDisplay.tsx

# Add updated task tracking
git add .kiro/specs/gcse-question-generator/tasks.md

# Add any test results and reports (optional)
git add *.json 2>/dev/null || true

echo -e "\n💾 Committing changes..."
git commit -m "feat: Enhanced AI knowledge base and caching fixes

- Added comprehensive AI instruction repository system
- Created bulk PDF upload and processing tools
- Fixed persistent caching issues with cache clearing system
- Enhanced mathematical notation rendering (human-readable format)
- Added question bank enhancement and categorization tools
- Created upload interface and content management system
- Updated Lambda functions with enhanced AI instructions
- Added comprehensive documentation and guides

Key improvements:
- Resolved same-question caching problem
- Clear upload destinations for PDF content
- AI agents now have detailed instruction access
- Enhanced question generation capabilities
- Better content organization and processing"

echo -e "\n🚀 Pushing to remote repository..."
git push origin main

echo -e "\n✅ Changes committed and pushed successfully!"
echo -e "\n📋 Summary of changes:"
echo "   • AI knowledge base system"
echo "   • Cache clearing and fixing tools"
echo "   • PDF upload and processing system"
echo "   • Enhanced AI instructions"
echo "   • Mathematical notation improvements"
echo "   • Comprehensive documentation"