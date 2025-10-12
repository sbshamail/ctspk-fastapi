# src/api/utils/video_processor.py
import re
import urllib.request
import urllib.parse
from typing import Dict, Optional
import json

class VideoProcessor:
    @staticmethod
    def extract_youtube_video_id(url: str) -> Optional[str]:
        """Extract YouTube video ID from various URL formats"""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&]+)',
            r'youtube\.com/watch\?.*v=([^&]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def extract_vimeo_video_id(url: str) -> Optional[str]:
        """Extract Vimeo video ID from URL"""
        patterns = [
            r'vimeo\.com/(\d+)',
            r'vimeo\.com/channels/.+/(\d+)',
            r'vimeo\.com/groups/.+/videos/(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def extract_dailymotion_video_id(url: str) -> Optional[str]:
        """Extract Dailymotion video ID from URL"""
        patterns = [
            r'dailymotion\.com/video/([^_]+)',
            r'dailymotion\.com/embed/video/([^_]+)',
            r'dai\.ly/([^_]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def get_youtube_video_data(video_id: str) -> Optional[Dict]:
        """Get YouTube video data using oEmbed"""
        try:
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            
            with urllib.request.urlopen(oembed_url, timeout=10) as response:
                data = json.loads(response.read().decode())
                
                return {
                    'title': data.get('title', ''),
                    'description': '',
                    'thumbnail': data.get('thumbnail_url', ''),
                    'duration': None,
                    'embed_url': f"https://www.youtube.com/embed/{video_id}",
                    'video_url': f"https://www.youtube.com/watch?v={video_id}",
                    'provider': 'youtube'
                }
        except Exception:
            # Fallback: Return basic data without API call
            return {
                'title': f'YouTube Video {video_id}',
                'description': '',
                'thumbnail': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg',
                'duration': None,
                'embed_url': f"https://www.youtube.com/embed/{video_id}",
                'video_url': f"https://www.youtube.com/watch?v={video_id}",
                'provider': 'youtube'
            }

    @staticmethod
    def get_vimeo_video_data(video_id: str) -> Optional[Dict]:
        """Get Vimeo video data using oEmbed"""
        try:
            oembed_url = f"https://vimeo.com/api/oembed.json?url=https://vimeo.com/{video_id}"
            
            with urllib.request.urlopen(oembed_url, timeout=10) as response:
                data = json.loads(response.read().decode())
                
                embed_url = f"https://player.vimeo.com/video/{video_id}"
                if 'html' in data:
                    # Extract embed URL from HTML
                    html_match = re.search(r'src="([^"]+)"', data['html'])
                    if html_match:
                        embed_url = html_match.group(1)
                
                return {
                    'title': data.get('title', ''),
                    'description': data.get('description', ''),
                    'thumbnail': data.get('thumbnail_url', ''),
                    'duration': data.get('duration', None),
                    'embed_url': embed_url,
                    'video_url': f"https://vimeo.com/{video_id}",
                    'provider': 'vimeo'
                }
        except Exception:
            # Fallback: Return basic data without API call
            return {
                'title': f'Vimeo Video {video_id}',
                'description': '',
                'thumbnail': '',
                'duration': None,
                'embed_url': f"https://player.vimeo.com/video/{video_id}",
                'video_url': f"https://vimeo.com/{video_id}",
                'provider': 'vimeo'
            }

    @staticmethod
    def get_dailymotion_video_data(video_id: str) -> Optional[Dict]:
        """Get Dailymotion video data using their API"""
        try:
            api_url = f"https://api.dailymotion.com/video/{video_id}?fields=title,description,thumbnail_360_url,duration,embed_url,url"
            
            with urllib.request.urlopen(api_url, timeout=10) as response:
                data = json.loads(response.read().decode())
                
                return {
                    'title': data.get('title', ''),
                    'description': data.get('description', ''),
                    'thumbnail': data.get('thumbnail_360_url', ''),
                    'duration': data.get('duration', None),
                    'embed_url': data.get('embed_url', ''),
                    'video_url': data.get('url', f"https://www.dailymotion.com/video/{video_id}"),
                    'provider': 'dailymotion'
                }
        except Exception:
            # Fallback: Return basic data without API call
            return {
                'title': f'Dailymotion Video {video_id}',
                'description': '',
                'thumbnail': '',
                'duration': None,
                'embed_url': f"https://www.dailymotion.com/embed/video/{video_id}",
                'video_url': f"https://www.dailymotion.com/video/{video_id}",
                'provider': 'dailymotion'
            }

    @staticmethod
    def process_video_url(url: str) -> Optional[Dict]:
        """Process video URL and return video data"""
        # Normalize URL
        url = url.strip()
        
        # YouTube
        youtube_id = VideoProcessor.extract_youtube_video_id(url)
        if youtube_id:
            return VideoProcessor.get_youtube_video_data(youtube_id)
        
        # Vimeo
        vimeo_id = VideoProcessor.extract_vimeo_video_id(url)
        if vimeo_id:
            return VideoProcessor.get_vimeo_video_data(vimeo_id)
        
        # Dailymotion
        dailymotion_id = VideoProcessor.extract_dailymotion_video_id(url)
        if dailymotion_id:
            return VideoProcessor.get_dailymotion_video_data(dailymotion_id)
        
        return None

    @staticmethod
    def is_supported_video_url(url: str) -> bool:
        """Check if the URL is from a supported video platform"""
        supported_domains = ['youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com', 'dai.ly']
        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc.lower()
        
        return any(supported_domain in domain for supported_domain in supported_domains)