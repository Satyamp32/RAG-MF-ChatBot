"""
Tests for URL fetcher functionality.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from src.ingestion.fetcher import Fetcher, FetchResult, RobotsChecker
from src.utils.retry import NetworkError, RateLimitError, TemporaryError


class TestFetchResult:
    """Test cases for FetchResult class."""
    
    def test_fetch_result_creation(self):
        """Test FetchResult initialization."""
        result = FetchResult(
            url="https://example.com",
            content="<html>test</html>",
            status_code=200
        )
        
        assert result.url == "https://example.com"
        assert result.content == "<html>test</html>"
        assert result.status_code == 200
        assert result.is_success is True
        assert result.is_not_modified is False
        assert result.fetcher_kind == "httpx"
        assert result.content_hash is not None
    
    def test_fetch_result_not_modified(self):
        """Test FetchResult with 304 status."""
        result = FetchResult(
            url="https://example.com",
            content="",
            status_code=304,
            etag="test-etag"
        )
        
        assert result.is_success is True
        assert result.is_not_modified is True
        assert result.etag == "test-etag"
    
    def test_fetch_result_to_dict(self):
        """Test FetchResult serialization."""
        result = FetchResult(
            url="https://example.com",
            content="test",
            status_code=200,
            etag="test-etag"
        )
        
        data = result.to_dict()
        
        assert data["url"] == "https://example.com"
        assert data["status_code"] == 200
        assert data["etag"] == "test-etag"
        assert "fetched_at" in data
        assert "content_hash" in data


class TestRobotsChecker:
    """Test cases for RobotsChecker class."""
    
    @pytest.mark.asyncio
    async def test_robots_allowed(self):
        """Test robots.txt allowance."""
        checker = RobotsChecker()
        
        # Mock a successful robots.txt fetch
        with patch('httpx.Client.get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = "User-agent: *\nAllow: /"
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = checker.is_allowed("https://example.com/page")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_robots_disallowed(self):
        """Test robots.txt disallowance."""
        checker = RobotsChecker()
        
        # Mock a disallowing robots.txt
        with patch('httpx.Client.get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = "User-agent: *\nDisallow: /private/"
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = checker.is_allowed("https://example.com/private/page")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_robots_fallback_on_error(self):
        """Test robots.txt fallback on error."""
        checker = RobotsChecker()
        
        # Mock a failed robots.txt fetch
        with patch('httpx.Client.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            result = checker.is_allowed("https://example.com/page")
            assert result is True  # Should allow by default


class TestFetcher:
    """Test cases for Fetcher class."""
    
    @pytest.fixture
    def fetcher(self):
        """Create a Fetcher instance for testing."""
        return Fetcher(timeout=10, max_retries=2)
    
    @pytest.mark.asyncio
    async def test_fetch_url_success(self, fetcher):
        """Test successful URL fetch."""
        with patch.object(fetcher.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = "<html>test content</html>"
            mock_response.status_code = 200
            mock_response.headers = {"ETag": "test-etag"}
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await fetcher._fetch_with_httpx("https://example.com")
            
            assert result.url == "https://example.com"
            assert result.content == "<html>test content</html>"
            assert result.status_code == 200
            assert result.etag == "test-etag"
            assert result.is_success is True
    
    @pytest.mark.asyncio
    async def test_fetch_url_not_modified(self, fetcher):
        """Test 304 Not Modified response."""
        with patch.object(fetcher.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = ""
            mock_response.status_code = 304
            mock_response.headers = {}
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await fetcher._fetch_with_httpx(
                "https://example.com",
                etag="test-etag"
            )
            
            assert result.status_code == 304
            assert result.is_not_modified is True
    
    @pytest.mark.asyncio
    async def test_fetch_url_rate_limit(self, fetcher):
        """Test rate limiting response."""
        with patch.object(fetcher.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "60"}
            mock_get.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(RateLimitError):
                await fetcher._fetch_with_httpx("https://example.com")
    
    @pytest.mark.asyncio
    async def test_fetch_url_redirect_error(self, fetcher):
        """Test redirect response handling."""
        with patch.object(fetcher.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 301
            mock_response.headers = {"Location": "https://new-url.com"}
            mock_get.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(NetworkError, match="Redirect detected"):
                await fetcher._fetch_with_httpx("https://example.com")
    
    @pytest.mark.asyncio
    async def test_content_quality_validation(self, fetcher):
        """Test content quality validation."""
        # Test good content
        good_result = FetchResult(
            url="https://example.com",
            content="<html>This is about HDFC mutual fund with detailed information</html>",
            status_code=200
        )
        assert fetcher._validate_content_quality(good_result) is True
        
        # Test too short content
        short_result = FetchResult(
            url="https://example.com",
            content="Short",
            status_code=200
        )
        assert fetcher._validate_content_quality(short_result) is False
        
        # Test missing keywords
        bad_result = FetchResult(
            url="https://example.com",
            content="<html>This page has no relevant content</html>",
            status_code=200
        )
        assert fetcher._validate_content_quality(bad_result) is False
    
    @pytest.mark.asyncio
    async def test_fetch_all_concurrent(self, fetcher):
        """Test concurrent fetching of multiple URLs."""
        urls = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3"
        ]
        
        with patch.object(fetcher, 'fetch_url') as mock_fetch:
            # Mock successful fetches
            mock_fetch.return_value = FetchResult(
                url="test",
                content="test content",
                status_code=200
            )
            
            results = await fetcher.fetch_all(urls)
            
            assert len(results) == 3
            assert all(r.is_success for r in results)
            # Verify all URLs were fetched
            assert mock_fetch.call_count == 3
    
    @pytest.mark.asyncio
    async def test_fetch_all_with_failures(self, fetcher):
        """Test handling of fetch failures in batch."""
        urls = [
            "https://example.com/1",
            "https://example.com/2"
        ]
        
        with patch.object(fetcher, 'fetch_url') as mock_fetch:
            # Mock one success, one failure
            mock_fetch.side_effect = [
                FetchResult(
                    url="https://example.com/1",
                    content="success",
                    status_code=200
                ),
                NetworkError("Failed to fetch")
            ]
            
            results = await fetcher.fetch_all(urls)
            
            assert len(results) == 2
            assert results[0].is_success is True
            assert results[1].is_success is False
            assert results[1].status_code == 500
    
    def test_etag_loading_and_saving(self, fetcher):
        """Test ETag persistence."""
        # Test loading non-existent file
        etags = fetcher._load_previous_etags()
        assert etags == {}
        
        # Test saving ETags
        results = [
            FetchResult(
                url="https://example.com/1",
                content="test1",
                status_code=200,
                etag="etag1"
            ),
            FetchResult(
                url="https://example.com/2",
                content="test2",
                status_code=200,
                etag="etag2"
            )
        ]
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            fetcher._save_etags(results)
            
            # Verify ETags were extracted and saved
            expected_etags = {
                "https://example.com/1": "etag1",
                "https://example.com/2": "etag2"
            }
            mock_file.write.assert_called_once()
            written_data = mock_file.write.call_args[0][0]
            import json
            saved_etags = json.loads(written_data)
            assert saved_etags == expected_etags


@pytest.mark.asyncio
async def test_integration_fetch_real_url():
    """Integration test with a real URL (if network is available)."""
    fetcher = Fetcher(timeout=10)
    
    try:
        result = await fetcher.fetch_url("https://httpbin.org/html")
        assert result.is_success is True
        assert len(result.content) > 0
        assert result.content_hash is not None
    except Exception as e:
        pytest.skip(f"Network test skipped: {str(e)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
