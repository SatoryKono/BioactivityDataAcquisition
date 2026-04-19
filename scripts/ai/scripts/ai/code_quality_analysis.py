#!/usr/bin/env python3
"""Analyze code quality to determine relevance of Sonar remediation issues."""

import os
from pathlib import Path
from collections import defaultdict

print("🔍 Comprehensive Code Quality Analysis")
print("=" * 50)

# Analyze Python files for common quality issues
def analyze_python_code():
    python_files = list(Path("./src").rglob("*.py"))
    
    issues_found = {
        'complex_functions': 0,
        'long_functions': 0,
        'unused_imports': 0,
        'missing_docstrings': 0,
        'total_files': len(python_files),
        'total_lines': 0
    }
    
    if not python_files:
        print("❌ No Python files found in ./src")
        return issues_found
    
    print(f"📊 Analyzing {len(python_files)} Python files...")
    
    for i, file_path in enumerate(python_files[:50], 1):  # Limit to first 50 files
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except UnicodeDecodeError:
            print(f"⚠️  Skipping {file_path} due to encoding issues")
            continue
        except PermissionError:
            print(f"⚠️  Skipping {file_path} due to permission issues")
            continue
        except OSError as e:
            print(f"⚠️  Skipping {file_path} due to file access error: {e}")
            continue
        
        issues_found['total_lines'] += len(lines)

        # Check for complex functions (high cyclomatic complexity indicator)
        if 'def ' in content and ('if ' in content or 'for ' in content or 'while ' in content):
            # Simple heuristic for complexity
            complexity_indicators = content.count('if') + content.count('for') + content.count('while')
            if complexity_indicators > 5:
                issues_found['complex_functions'] += 1

        # Check for long functions
        if 'def ' in content:
            func_lines = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
            if func_lines > 50:
                issues_found['long_functions'] += 1

        # Check for missing docstrings (simple check)
        if 'def ' in content and '"""' not in content and "'''" not in content:
            issues_found['missing_docstrings'] += 1
                    
        except (IOError, UnicodeDecodeError, json.JSONDecodeError) as e:
            print(f"⚠️  Error analyzing {file_path}: {e}")
        except Exception as e:
            print(f"⚠️  Unexpected error analyzing {file_path}: {e}")
            raise
    
    return issues_found

# Analyze code structure
def analyze_code_structure():
    structure = {
        'packages': set(),
        'modules': set(),
        'test_files': set()
    }
    
    # Find all Python packages and modules
    for root, dirs, files in os.walk("./src"):
        for dir_name in dirs:
            if not dir_name.startswith('_'):
                structure['packages'].add(dir_name)
        
        for file_name in files:
            if file_name.endswith('.py'):
                if file_name.startswith('test_') or file_name.endswith('_test.py'):
                    structure['test_files'].add(file_name)
                else:
                    module_name = file_name.replace('.py', '')
                    if not module_name.startswith('_'):
                        structure['modules'].add(module_name)
    
    return structure

# Main analysis
if __name__ == "__main__":
    # Code structure analysis
    print("\n🏗️  Code Structure Analysis:")
    structure = analyze_code_structure()
    print(f"   Packages: {len(structure['packages'])}")
    print(f"   Modules: {len(structure['modules'])}")
    print(f"   Test files: {len(structure['test_files'])}")
    
    # Code quality analysis
    print("\n🔬 Code Quality Analysis:")
    quality_issues = analyze_python_code()
    
    print(f"   Files analyzed: {quality_issues['total_files']}")
    print(f"   Total lines: {quality_issues['total_lines']}")
    print(f"   Complex functions: {quality_issues['complex_functions']}")
    print(f"   Long functions: {quality_issues['long_functions']}")
    print(f"   Missing docstrings: {quality_issues['missing_docstrings']}")
    
    # Calculate quality score
    total_issues = (quality_issues['complex_functions'] + 
                   quality_issues['long_functions'] + 
                   quality_issues['missing_docstrings'])
    
    if quality_issues['total_files'] > 0:
        issues_per_file = total_issues / quality_issues['total_files']
        quality_score = max(0, 100 - (issues_per_file * 10))
    else:
        quality_score = 100
    
    print(f"\n📊 Quality Score: {quality_score:.1f}/100")
    
    # Relevance assessment for Sonar issues
    print("\n🎯 Sonar Remediation Issues Relevance:")
    
    if quality_score >= 90:
        print("   ✅ EXCELLENT - Code quality is very high")
        print("   📋 Sonar issues may be proactive/preventive")
        print("   🔮 Focus on maintaining quality rather than fixing issues")
    elif quality_score >= 75:
        print("   ✅ GOOD - Code quality is solid")
        print("   📋 Sonar issues are likely relevant for continuous improvement")
        print("   🔮 Wave-based approach makes sense for systematic improvement")
    elif quality_score >= 50:
        print("   ⚠️  FAIR - Code quality needs attention")
        print("   📋 Sonar issues are highly relevant and necessary")
        print("   🔮 Remediation waves should be prioritized")
    else:
        print("   ❌ POOR - Code quality needs significant improvement")
        print("   📋 Sonar issues are critical and urgent")
        print("   🔮 Immediate action required on remediation")
    
    # Specific recommendations
    print("\n💡 Specific Recommendations:")
    if quality_issues['complex_functions'] > 5:
        print("   • Refactor complex functions (Wave 3: complexity refactors)")
    if quality_issues['long_functions'] > 3:
        print("   • Split long functions into smaller, focused methods")
    if quality_issues['missing_docstrings'] > 10:
        print("   • Add docstrings for better documentation (Wave 4: hygiene)")
    
    print("\n✅ Analysis complete!")