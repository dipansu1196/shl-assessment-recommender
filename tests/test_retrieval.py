"""
Unit tests for retrieval module.

Tests use realistic queries from conversation traces and verify
that expected assessments appear in top-15 results.
"""

import pytest
from app.retrieval import search, get_by_name, get_metadata_count


class TestRetrieval:
    """Test suite for retrieval.search() function."""
    
    def test_rust_engineer_query(self):
        """
        Test query from C2: "senior Rust engineer high-performance networking"
        
        Expected items from C2 final shortlist:
        - Smart Interview Live Coding
        - Linux Programming (General)
        - Networking and Implementation (New)
        """
        query = "senior Rust engineer high-performance networking infrastructure"
        results = search(query, k=15)
        
        # Check we got 15 results
        assert len(results) == 15, "Should return exactly 15 results"
        
        # Check all results have required fields
        for result in results:
            assert 'name' in result
            assert 'score' in result
            assert 'test_type' in result
            assert 'url' in result
            assert isinstance(result['score'], float)
        
        # Extract names from top 15
        result_names = [r['name'] for r in results]
        
        # Expected items from C2 trace
        expected_items = [
            "Smart Interview Live Coding",
            "Linux Programming (General)", 
            "Networking and Implementation (New)"
        ]
        
        # Check at least 2 of 3 expected items appear in top-15
        found_count = sum(1 for item in expected_items if item in result_names)
        assert found_count >= 2, (
            f"Expected at least 2 of {expected_items} in top-15 results. "
            f"Found {found_count}. Results: {result_names[:5]}"
        )
        
        # Verify scores are in descending order
        scores = [r['score'] for r in results]
        assert scores == sorted(scores, reverse=True), "Results should be ordered by score descending"
    
    def test_graduate_financial_analyst_query(self):
        """
        Test query from C4: "graduate financial analysts numerical reasoning"
        
        Expected items from C4 final shortlist:
        - SHL Verify Interactive – Numerical Reasoning
        - Financial Accounting (New)
        - Basic Statistics (New)
        - Graduate Scenarios
        """
        query = "graduate financial analysts numerical reasoning finance knowledge"
        results = search(query, k=15)
        
        # Check we got 15 results
        assert len(results) == 15
        
        # Extract names from top 15
        result_names = [r['name'] for r in results]
        
        # Expected items from C4 trace
        expected_items = [
            "SHL Verify Interactive – Numerical Reasoning",
            "Financial Accounting (New)",
            "Basic Statistics (New)",
            "Graduate Scenarios"
        ]
        
        # Check at least 3 of 4 expected items appear in top-15
        found_count = sum(1 for item in expected_items if item in result_names)
        assert found_count >= 3, (
            f"Expected at least 3 of {expected_items} in top-15 results. "
            f"Found {found_count}. Results: {result_names[:5]}"
        )
        
        # Check that numerical reasoning appears in top results
        numerical_found = any('numerical' in name.lower() for name in result_names[:10])
        assert numerical_found, "Numerical reasoning test should appear in top 10"
    
    def test_senior_leadership_query(self):
        """
        Test query from C1: "senior leadership assessment CXO director"
        
        Expected items from C1 final shortlist:
        - Occupational Personality Questionnaire OPQ32r
        - OPQ Universal Competency Report 2.0
        - OPQ Leadership Report
        """
        query = "senior leadership assessment CXO director executive 15 years experience"
        results = search(query, k=15)
        
        # Check we got 15 results
        assert len(results) == 15
        
        # Extract names from top 15
        result_names = [r['name'] for r in results]
        
        # Expected items from C1 trace
        expected_items = [
            "Occupational Personality Questionnaire OPQ32r",
            "OPQ Universal Competency Report 2.0",
            "OPQ Leadership Report"
        ]
        
        # Check at least 2 of 3 expected items appear in top-15
        found_count = sum(1 for item in expected_items if item in result_names)
        assert found_count >= 2, (
            f"Expected at least 2 of {expected_items} in top-15 results. "
            f"Found {found_count}. Results: {result_names[:5]}"
        )
        
        # Check that OPQ appears prominently
        opq_in_top5 = any('opq' in name.lower() for name in result_names[:5])
        assert opq_in_top5, "OPQ assessment should appear in top 5 for leadership query"
    
    def test_search_returns_valid_metadata(self):
        """Test that all returned items have complete metadata."""
        query = "Python programming test"
        results = search(query, k=5)
        
        required_fields = [
            'entity_id', 'name', 'url', 'test_type', 
            'keys', 'description', 'duration', 'job_levels', 'languages', 'score'
        ]
        
        for result in results:
            for field in required_fields:
                assert field in result, f"Missing field: {field}"
            
            # Type checks
            assert isinstance(result['name'], str)
            assert isinstance(result['url'], str)
            assert result['url'].startswith('http'), "URL should be valid"
            assert isinstance(result['score'], float)
            assert 0 <= result['score'] <= 1, "Score should be normalized between 0 and 1"
    
    def test_get_by_name(self):
        """Test exact name lookup function."""
        # Test with known item from traces
        result = get_by_name("Occupational Personality Questionnaire OPQ32r")
        
        assert result is not None, "Should find OPQ32r"
        assert result['name'] == "Occupational Personality Questionnaire OPQ32r"
        assert 'url' in result
        assert 'test_type' in result
        
        # Test with non-existent item
        result = get_by_name("Non-Existent Assessment XYZ123")
        assert result is None, "Should return None for non-existent item"
    
    def test_metadata_count(self):
        """Test that catalog has reasonable number of items."""
        count = get_metadata_count()
        
        # Catalog should have hundreds of items based on spec
        assert count > 100, f"Catalog should have >100 items, got {count}"
        assert count < 5000, f"Catalog should have <5000 items, got {count}"


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])
