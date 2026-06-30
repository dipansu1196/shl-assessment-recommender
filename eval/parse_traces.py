"""
Parse conversation trace markdown files into structured test fixtures.

Each trace file (C1.md - C10.md) contains a multi-turn conversation with expected
recommendations at the end. This module parses them into structured fixtures for
the replay harness.
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Tuple


def parse_trace_file(filepath: Path) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Parse a single trace markdown file.
    
    Returns:
        (turns, expected_recommendations)
        where:
        - turns: list of {"role": "user"|"assistant", "content": "..."} dicts
        - expected_recommendations: list of {"name": str, "url": str, "test_type": str}
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    turns = []
    expected_recommendations = []
    
    # Split by "### Turn X" sections
    turn_sections = re.split(r'### Turn (\d+)\n', content)
    
    if len(turn_sections) < 2:
        # Fallback: try to parse without explicit turn markers
        return _parse_trace_fallback(content)
    
    # Process each turn (skip header at index 0)
    for i in range(1, len(turn_sections), 2):
        turn_num = turn_sections[i]
        turn_content = turn_sections[i+1] if i+1 < len(turn_sections) else ""
        
        # Parse user and assistant messages in this turn
        user_match = re.search(r'\*\*User\*\*\n\n> (.+?)(?=\n\n\*\*Agent\*\*|\n\n_|$)', turn_content, re.DOTALL)
        agent_match = re.search(r'\*\*Agent\*\*\n\n(.+?)(?=\n\n_|\Z)', turn_content, re.DOTALL)
        
        if user_match:
            user_text = user_match.group(1).strip()
            # Clean up markdown quotes
            user_text = re.sub(r'^> ', '', user_text, flags=re.MULTILINE)
            turns.append({
                "role": "user",
                "content": user_text
            })
        
        if agent_match:
            agent_text = agent_match.group(1).strip()
            
            # Check if this section contains a recommendations table
            # Tables have | separators
            if '|' in agent_text:
                # This turn has recommendations - parse the table
                # Also extract the text before the table
                table_match = re.search(r'(\|.*?\|.*?\|.*?\|)', agent_text, re.DOTALL)
                if table_match:
                    table_start = agent_text.find(table_match.group(0))
                    reply_text = agent_text[:table_start].strip()
                    
                    # Extract table rows
                    table_lines = [line.strip() for line in agent_text[table_start:].split('\n') if line.strip().startswith('|')]
                    recs = _parse_recommendations_table(table_lines)
                    
                    # Only keep the reply text, not the table
                    agent_text = reply_text
                    
                    # Store expected recommendations from the LAST turn with recommendations
                    if recs:
                        expected_recommendations = recs
            
            # Add agent message
            if agent_text:  # Only add if there's content besides the table
                # Remove footnote markers like "_`end_of_conversation`: **true**_"
                agent_text = re.sub(r'\n\n_.*', '', agent_text, flags=re.DOTALL)
                agent_text = agent_text.strip()
                
                if agent_text:
                    turns.append({
                        "role": "assistant",
                        "content": agent_text
                    })
    
    return turns, expected_recommendations


def _parse_trace_fallback(content: str) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Fallback parser for traces without explicit turn markers.
    Looks for **User** and **Agent** blocks.
    """
    turns = []
    expected_recommendations = []
    
    # Split by **User** markers
    user_blocks = re.split(r'\*\*User\*\*\n\n> ', content)
    
    for block in user_blocks[1:]:  # Skip header
        # Extract user message (everything until **Agent**)
        user_match = re.match(r'(.+?)(?=\n\n\*\*Agent\*\*|\Z)', block, re.DOTALL)
        if user_match:
            user_text = user_match.group(1).strip()
            turns.append({
                "role": "user",
                "content": user_text
            })
            
            # Extract agent response
            agent_match = re.search(r'\*\*Agent\*\*\n\n(.+?)(?=\n\n_|\Z)', block, re.DOTALL)
            if agent_match:
                agent_text = agent_match.group(1).strip()
                
                # Check for table with recommendations
                if '|' in agent_text:
                    # Parse table
                    table_lines = [line.strip() for line in agent_text.split('\n') if line.strip().startswith('|')]
                    recs = _parse_recommendations_table(table_lines)
                    if recs:
                        expected_recommendations = recs
                    
                    # Remove table from agent text
                    agent_text = re.sub(r'\|.*?\|.*?\n.*?\n(?:\|.*?\n)+', '', agent_text)
                
                # Clean up footnotes
                agent_text = re.sub(r'\n\n_.*', '', agent_text, flags=re.DOTALL).strip()
                
                if agent_text:
                    turns.append({
                        "role": "assistant",
                        "content": agent_text
                    })
    
    return turns, expected_recommendations


def _parse_recommendations_table(table_lines: List[str]) -> List[Dict[str, str]]:
    """
    Parse a markdown recommendations table into structured data.
    
    Table format:
    | # | Name | Test Type | Keys | Duration | Languages | URL |
    |---|------|-----------|------|----------|-----------|-----|
    | 1 | Assessment Name | K | ... | ... | ... | https://... |
    
    Returns list of {"name": str, "url": str, "test_type": str}
    """
    recommendations = []
    
    if len(table_lines) < 3:
        return recommendations
    
    # Skip header and separator rows
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.split('|')[1:-1]]  # Remove empty first/last
        
        if len(cells) >= 7:
            # Format: # | Name | Test Type | Keys | Duration | Languages | URL
            name = cells[1]
            test_type = cells[2]
            url = cells[6]
            
            # Clean up name (remove markdown links if present)
            name = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', name)
            
            # Clean up URL (extract from markdown link if needed)
            url_match = re.search(r'https?://[^\s)]+', url)
            if url_match:
                url = url_match.group(0)
            
            if name and url and test_type:
                recommendations.append({
                    "name": name,
                    "url": url,
                    "test_type": test_type
                })
    
    return recommendations


def load_all_traces(traces_dir: Path = None) -> Dict[str, Tuple[List[Dict[str, str]], List[Dict[str, str]]]]:
    """
    Load all trace files from the traces directory.
    
    Returns:
        Dict mapping trace_id (e.g. "C1") to (turns, expected_recommendations)
    """
    if traces_dir is None:
        traces_dir = Path(__file__).parent.parent / "GenAI_SampleConversations"
    
    traces = {}
    
    # Load C1.md through C10.md
    for i in range(1, 11):
        trace_file = traces_dir / f"C{i}.md"
        if trace_file.exists():
            try:
                turns, expected = parse_trace_file(trace_file)
                traces[f"C{i}"] = (turns, expected)
                print(f"✓ Loaded {trace_file.name}: {len(turns)} turns, {len(expected)} expected recommendations")
            except Exception as e:
                print(f"✗ Failed to load {trace_file.name}: {e}")
        else:
            print(f"✗ File not found: {trace_file}")
    
    return traces


if __name__ == "__main__":
    # Test the parser
    traces = load_all_traces()
    print(f"\nLoaded {len(traces)} traces")
    
    # Print first trace as example
    if traces:
        first_id = sorted(traces.keys())[0]
        turns, expected = traces[first_id]
        print(f"\n{first_id} example:")
        print(f"Turns: {len(turns)}")
        for i, turn in enumerate(turns):
            print(f"  Turn {i+1}: {turn['role']}: {turn['content'][:60]}...")
        print(f"Expected recommendations: {len(expected)}")
        for rec in expected:
            print(f"  - {rec['name']} ({rec['test_type']})")
