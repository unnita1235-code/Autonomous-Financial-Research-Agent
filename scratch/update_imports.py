import os
import re

replacements = {
    r'\bcircuitbreaker\b': 'circuit_breaker',
    r'\berrorhandler\b': 'error_handler',
    r'\bfallbackchains\b': 'fallback_chains',
    r'\bqueryanalyzer\b': 'query_analyzer',
    r'\bcalculationengine\b': 'calculation_engine',
    r'\bcompanyprofile\b': 'company_profile',
    r'\bfactchecker\b': 'fact_checker',
    r'\bfinancialdataapi\b': 'financial_data_api',
    r'\bnewssentiment\b': 'news_sentiment',
    r'\bpeercomparison\b': 'peer_comparison',
    r'\breportgenerator\b': 'report_generator',
    r'\bvectordbsearch\b': 'vector_db_search',
    r'\bwebsearch\b': 'web_search',
    r'\bconflictresolver\b': 'conflict_resolver'
}

def update_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    for old, new in replacements.items():
        new_content = re.sub(old, new, new_content)
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated: {file_path}")

def main():
    root_dir = r'd:\Autonomous Financial Research Agent'
    for root, dirs, files in os.walk(root_dir):
        # Skip .git, .venv, node_modules, etc.
        for skip in ['.git', '.venv', 'node_modules', '.next']:
            if skip in dirs:
                dirs.remove(skip)
        
        for file in files:
            if file.endswith('.py') or file.endswith('.md') or file.endswith('.json') or file.endswith('.yaml') or file.endswith('.yml'):
                try:
                    update_file(os.path.join(root, file))
                except Exception as e:
                    print(f"Error processing {file}: {e}")

if __name__ == "__main__":
    main()
