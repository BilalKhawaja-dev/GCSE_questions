#!/usr/bin/env python3
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
        print(f"\n🧪 Running: {name}")
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
    
    print(f"\n📊 Validation Summary: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All validations passed!")
        return True
    else:
        print("⚠️ Some validations failed. Check individual results above.")
        return False

if __name__ == "__main__":
    success = run_validation_suite()
    sys.exit(0 if success else 1)
