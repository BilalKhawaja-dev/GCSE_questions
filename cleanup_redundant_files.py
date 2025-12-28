#!/usr/bin/env python3
"""
Cleanup Redundant Files

This script identifies and removes redundant, temporary, and duplicate files
before pushing to CodePipeline for proper version control.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Set

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RedundantFilesCleaner:
    """Clean up redundant and temporary files"""
    
    def __init__(self):
        self.workspace_root = Path('.')
        self.files_to_remove = []
        self.files_to_keep = []
        self.analysis_results = {}
    
    def identify_redundant_files(self) -> Dict[str, List[str]]:
        """Identify redundant and temporary files"""
        
        redundant_categories = {
            'temporary_test_results': [],
            'duplicate_scripts': [],
            'old_debug_files': [],
            'cache_results': [],
            'redundant_html_tests': [],
            'duplicate_upload_scripts': [],
            'temporary_json_reports': []
        }
        
        # Find all files in workspace
        all_files = list(self.workspace_root.rglob('*'))
        all_files = [f for f in all_files if f.is_file()]
        
        for file_path in all_files:
            file_name = file_path.name
            file_str = str(file_path)
            
            # Temporary test result files
            if (file_name.endswith('.json') and 
                any(keyword in file_name for keyword in ['test_results', 'validation_', 'analysis_', 'report_'])):
                redundant_categories['temporary_test_results'].append(file_str)
            
            # Cache clearing results
            if 'cache' in file_name and file_name.endswith('.json'):
                redundant_categories['cache_results'].append(file_str)
            
            # Old debug files
            if any(keyword in file_name for keyword in ['debug_', 'test_lambda_', 'test_bedrock']):
                redundant_categories['old_debug_files'].append(file_str)
            
            # Redundant HTML test files
            if (file_name.endswith('.html') and 
                any(keyword in file_name for keyword in ['test_', 'latex_', 'frontend_'])):
                redundant_categories['redundant_html_tests'].append(file_str)
            
            # Check for duplicate upload scripts
            if 'upload' in file_name and file_name.endswith('.py'):
                if file_name in ['upload_gcse_examples.py', 'upload_sample_content.py']:
                    redundant_categories['duplicate_upload_scripts'].append(file_str)
            
            # Temporary JSON reports
            if (file_name.endswith('.json') and 
                any(keyword in file_name for keyword in ['_20251228_', 'timestamp', 'temp_'])):
                redundant_categories['temporary_json_reports'].append(file_str)
        
        return redundant_categories
    
    def identify_duplicate_functionality(self) -> Dict[str, List[str]]:
        """Identify scripts with duplicate functionality"""
        
        duplicates = {
            'cache_management': [],
            'content_upload': [],
            'testing_validation': [],
            'debug_scripts': []
        }
        
        # Cache management - keep the comprehensive one
        cache_files = [
            'fix_caching_issues.py',  # Keep - specific cache fixes
            'clear_all_caches.py',    # Keep - comprehensive cache clearing
            'test_cache_uniqueness.py'  # Remove - redundant with clear_all_caches.py
        ]
        
        # Content upload - consolidate
        upload_files = [
            'bulk_pdf_upload_system.py',      # Keep - main system
            'ai_knowledge_upload_system.py',  # Keep - AI instructions
            'upload_interface.py',            # Keep - user interface
            'upload_missing_examples.py',     # Keep - specific examples
            'upload_gcse_examples.py',        # Remove - redundant
            'upload_sample_content.py'        # Remove - redundant
        ]
        
        # Testing/validation - keep essential ones
        test_files = [
            'validate_ai_integration.py',     # Keep - essential validation
            'check_s3_content.py',           # Keep - essential checking
            'test_bulk_upload.py',           # Keep - specific test
            'test_cache_fix.py',             # Keep - specific test
            'test_user_workflow.py',         # Remove - redundant
            'test_frontend_e2e.py',          # Remove - redundant
            'test_e2e_api.py'                # Remove - redundant
        ]
        
        # Debug scripts - remove most
        debug_files = [
            'debug_connection.py',           # Remove - debug only
            'test_lambda_bedrock.py',        # Remove - debug only
            'test_bedrock.py',               # Remove - debug only
            'load_test.py'                   # Remove - debug only
        ]
        
        # Categorize for removal
        duplicates['content_upload'] = ['upload_gcse_examples.py', 'upload_sample_content.py']
        duplicates['testing_validation'] = ['test_user_workflow.py', 'test_frontend_e2e.py', 'test_e2e_api.py']
        duplicates['debug_scripts'] = ['debug_connection.py', 'test_lambda_bedrock.py', 'test_bedrock.py', 'load_test.py']
        duplicates['cache_management'] = ['test_cache_uniqueness.py']  # Keep others
        
        return duplicates
    
    def create_consolidated_scripts(self) -> Dict[str, str]:
        """Create consolidated versions of important scripts"""
        
        consolidated = {}
        
        # Create a consolidated validation script
        consolidated['validate_system.py'] = '''#!/usr/bin/env python3
"""
Consolidated System Validation

This script combines multiple validation checks into one comprehensive tool.
"""

import subprocess
import sys
from pathlib import Path

def run_validation_suite():
    """Run comprehensive system validation"""
    
    print("🔍 COMPREHENSIVE SYSTEM VALIDATION")
    print("=" * 60)
    
    validations = [
        ("S3 Content Check", "python check_s3_content.py"),
        ("AI Integration Validation", "python validate_ai_integration.py"),
        ("Cache System Test", "python test_cache_fix.py")
    ]
    
    results = {}
    
    for name, command in validations:
        print(f"\\n🧪 Running: {name}")
        try:
            result = subprocess.run(command.split(), capture_output=True, text=True, timeout=300)
            results[name] = {
                'success': result.returncode == 0,
                'output': result.stdout[-500:] if result.stdout else '',  # Last 500 chars
                'error': result.stderr[-500:] if result.stderr else ''
            }
            
            if result.returncode == 0:
                print(f"   ✅ {name}: PASSED")
            else:
                print(f"   ❌ {name}: FAILED")
                
        except Exception as e:
            print(f"   💥 {name}: ERROR - {str(e)}")
            results[name] = {'success': False, 'error': str(e)}
    
    # Summary
    passed = sum(1 for r in results.values() if r.get('success', False))
    total = len(results)
    
    print(f"\\n📊 Validation Summary: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All validations passed!")
        return True
    else:
        print("⚠️ Some validations failed. Check individual results above.")
        return False

if __name__ == "__main__":
    success = run_validation_suite()
    sys.exit(0 if success else 1)
'''
        
        return consolidated
    
    def remove_redundant_files(self, redundant_files: Dict[str, List[str]], duplicates: Dict[str, List[str]]) -> Dict[str, int]:
        """Remove identified redundant files"""
        
        removal_stats = {
            'removed': 0,
            'failed': 0,
            'categories': {}
        }
        
        # Combine all files to remove
        all_files_to_remove = []
        
        for category, files in redundant_files.items():
            all_files_to_remove.extend(files)
            removal_stats['categories'][category] = len(files)
        
        for category, files in duplicates.items():
            all_files_to_remove.extend(files)
            if category not in removal_stats['categories']:
                removal_stats['categories'][category] = 0
            removal_stats['categories'][category] += len(files)
        
        # Remove duplicates from list
        all_files_to_remove = list(set(all_files_to_remove))
        
        logger.info(f"Removing {len(all_files_to_remove)} redundant files")
        
        for file_path in all_files_to_remove:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"✅ Removed: {file_path}")
                    removal_stats['removed'] += 1
                else:
                    logger.warning(f"⚠️ File not found: {file_path}")
            except Exception as e:
                logger.error(f"❌ Failed to remove {file_path}: {str(e)}")
                removal_stats['failed'] += 1
        
        return removal_stats
    
    def update_gitignore(self):
        """Update .gitignore to prevent future redundant files"""
        
        gitignore_additions = [
            "# Temporary test results",
            "*_test_results_*.json",
            "*_validation_*.json",
            "*_analysis_*.json",
            "cache_clear_results.json",
            "",
            "# Debug and temporary files",
            "debug_*.py",
            "temp_*.py",
            "*_temp.json",
            "",
            "# HTML test files",
            "test_*.html",
            "",
            "# Temporary reports",
            "*_20*_*.json",
            "upload_report.json",
            "bulk_upload_test_report.json"
        ]
        
        gitignore_path = Path('.gitignore')
        
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                current_content = f.read()
        else:
            current_content = ""
        
        # Add new entries if not already present
        new_entries = []
        for entry in gitignore_additions:
            if entry not in current_content:
                new_entries.append(entry)
        
        if new_entries:
            with open(gitignore_path, 'a') as f:
                f.write("\n# Added by cleanup script\n")
                f.write("\n".join(new_entries))
                f.write("\n")
            
            logger.info(f"✅ Updated .gitignore with {len(new_entries)} new entries")
        else:
            logger.info("✅ .gitignore already up to date")
    
    def run_cleanup(self) -> Dict[str, any]:
        """Run complete cleanup process"""
        
        logger.info("🧹 Starting redundant files cleanup")
        
        results = {
            'redundant_files': {},
            'duplicate_functionality': {},
            'consolidated_scripts': {},
            'removal_stats': {},
            'cleanup_successful': False
        }
        
        try:
            # Step 1: Identify redundant files
            logger.info("Step 1: Identifying redundant files")
            results['redundant_files'] = self.identify_redundant_files()
            
            # Step 2: Identify duplicate functionality
            logger.info("Step 2: Identifying duplicate functionality")
            results['duplicate_functionality'] = self.identify_duplicate_functionality()
            
            # Step 3: Create consolidated scripts
            logger.info("Step 3: Creating consolidated scripts")
            consolidated = self.create_consolidated_scripts()
            results['consolidated_scripts'] = list(consolidated.keys())
            
            for filename, content in consolidated.items():
                with open(filename, 'w') as f:
                    f.write(content)
                os.chmod(filename, 0o755)
                logger.info(f"✅ Created consolidated script: {filename}")
            
            # Step 4: Remove redundant files
            logger.info("Step 4: Removing redundant files")
            results['removal_stats'] = self.remove_redundant_files(
                results['redundant_files'], 
                results['duplicate_functionality']
            )
            
            # Step 5: Update .gitignore
            logger.info("Step 5: Updating .gitignore")
            self.update_gitignore()
            
            results['cleanup_successful'] = True
            logger.info("🎉 Cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"💥 Cleanup failed: {str(e)}")
            results['error'] = str(e)
        
        return results

def main():
    """Main cleanup function"""
    
    print("🧹 REDUNDANT FILES CLEANUP")
    print("=" * 60)
    print("Cleaning up redundant and temporary files before CodePipeline push")
    
    try:
        cleaner = RedundantFilesCleaner()
        results = cleaner.run_cleanup()
        
        print(f"\\n📊 Cleanup Results:")
        print(f"   Files removed: {results['removal_stats'].get('removed', 0)}")
        print(f"   Removal failures: {results['removal_stats'].get('failed', 0)}")
        print(f"   Consolidated scripts created: {len(results['consolidated_scripts'])}")
        print(f"   Cleanup successful: {results['cleanup_successful']}")
        
        if results['cleanup_successful']:
            print(f"\\n🎉 Cleanup successful!")
            print(f"\\n📁 Remaining essential files:")
            
            essential_files = [
                'bulk_pdf_upload_system.py',
                'ai_knowledge_upload_system.py', 
                'enhanced_ai_integration.py',
                'upload_interface.py',
                'clear_all_caches.py',
                'validate_ai_integration.py',
                'check_s3_content.py',
                'validate_system.py'  # New consolidated script
            ]
            
            for file in essential_files:
                if os.path.exists(file):
                    print(f"   ✅ {file}")
                else:
                    print(f"   ❌ {file} (missing)")
            
            print(f"\\n🚀 Ready for CodePipeline push!")
            return True
        else:
            print(f"\\n⚠️ Cleanup had issues. Check logs above.")
            return False
            
    except Exception as e:
        print(f"\\n💥 Cleanup failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)