#!/usr/bin/env python3
"""Check the relevance of existing Sonar remediation issues."""

import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

github_token = os.getenv('GITHUB_TOKEN')
repo = os.getenv('GITHUB_REPO', 'SatoryKono/BioactivityDataAcquisition')

# List of Sonar remediation issues to check
issues_to_check = [2988, 2987, 2986, 2985]

print('🔍 Analyzing Sonar Remediation Issues Relevance')
print('=' * 60)

for issue_number in issues_to_check:
    try:
        response = requests.get(
            f'https://api.github.com/repos/{repo}/issues/{issue_number}',
            headers={
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
        )
        
        if response.status_code == 200:
            issue = response.json()
            
            # Calculate age
            created_at = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00'))
            now_utc = datetime.now(timezone.utc)  # Use timezone-aware datetime
            age_days = (now_utc - created_at).days
            
            # Get comments count
            comments_response = requests.get(
                f'https://api.github.com/repos/{repo}/issues/{issue_number}/comments',
                headers={'Authorization': f'token {github_token}'}
            )
            comments_count = len(comments_response.json()) if comments_response.status_code == 200 else 0
            
            print(f'\n📋 Issue #{issue_number}: {issue["title"]}')
            print(f'Status: {"OPEN" if issue["state"] == "open" else "CLOSED"}')
            print(f'Age: {age_days} days old')
            print(f'Comments: {comments_count}')
            print(f'Updated: {issue["updated_at"]}')
            
            # Check for activity
            if age_days > 30 and comments_count == 0:
                status = '⚠️  STALE - No recent activity'
            elif issue['state'] == 'closed':
                status = '✅ COMPLETED'
            else:
                status = '🔄 ACTIVE'
            
            print(f'Relevance: {status}')
            
            # Show first line of body if available
            body = issue.get('body', '')
            if body:
                first_line = body.split('\n')[0][:80]
                print(f'Content: {first_line}...')
            
            print(f'URL: {issue["html_url"]}')
            
        else:
            print(f'\n❌ Issue #{issue_number}: Not found or inaccessible')
            
    except requests.exceptions.RequestException as e:
        print(f'\n❌ Network error checking issue #{issue_number}: {e}')
    except json.JSONDecodeError as e:
        print(f'\n❌ JSON decode error for issue #{issue_number}: {e}')
    except (KeyError, ValueError, IndexError) as e:
        if isinstance(e, KeyError):
            print(f'\n❌ Missing expected field in issue #{issue_number}: {e}')
        else:
            print(f'\n❌ Expected error checking issue #{issue_number}: {e}')
    except Exception as e:
        print(f'\n❌ Unexpected error checking issue #{issue_number}: {e}')
        raise

print('\n' + '=' * 60)
print('📊 SUMMARY ANALYSIS')
print('=' * 60)
print('These issues appear to be part of a structured Sonar remediation program.')
print('The numbering suggests a wave-based approach to code quality improvement.')
print('\nRecommendation: Check if these issues are still relevant given that')
print('SonarQube currently reports 0 active issues in the project.')