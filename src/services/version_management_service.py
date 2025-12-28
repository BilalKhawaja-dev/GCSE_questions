"""
Version Management Service for GCSE Question Generator

This service handles:
1. Version tagging for specification JSON files
2. Version selection logic for GenerateLambda
3. Multi-version support with "latest" as default
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class VersionManagementService:
    """Service for managing specification versions"""
    
    def __init__(self, s3_client=None):
        """Initialize the version management service"""
        self.s3_client = s3_client or boto3.client('s3')
    
    def add_version_tag(self, content_dict: Dict[str, Any], version: str) -> Dict[str, Any]:
        """
        Add version tagging to specification content.
        
        Args:
            content_dict: Original content dictionary
            version: Version string to add
            
        Returns:
            Updated content dictionary with version information
        """
        # Add version metadata
        content_dict['version'] = version
        content_dict['version_timestamp'] = self._get_current_timestamp()
        content_dict['version_metadata'] = {
            'created_at': self._get_current_timestamp(),
            'status': 'active',
            'description': f'Version {version} of specification content'
        }
        
        logger.info(f"Added version tag {version} to content")
        return content_dict
    
    def create_versioned_file_path(self, base_path: str, version: str) -> str:
        """
        Create versioned file path for S3 storage.
        
        Args:
            base_path: Base file path (e.g., "specifications/number/fractions.json")
            version: Version string
            
        Returns:
            Versioned file path
        """
        # Split path into components
        path_parts = base_path.split('/')
        filename = path_parts[-1]
        directory = '/'.join(path_parts[:-1])
        
        # Remove .json extension and add version
        name_without_ext = filename.replace('.json', '')
        versioned_filename = f"{name_without_ext}_v{version}.json"
        
        return f"{directory}/{versioned_filename}"
    
    def create_latest_symlink(self, base_path: str, version: str) -> str:
        """
        Create "latest" version path that points to the current version.
        
        Args:
            base_path: Base file path
            version: Current version
            
        Returns:
            Latest version file path
        """
        path_parts = base_path.split('/')
        filename = path_parts[-1]
        directory = '/'.join(path_parts[:-1])
        
        # Create latest filename
        name_without_ext = filename.replace('.json', '')
        latest_filename = f"{name_without_ext}_latest.json"
        
        return f"{directory}/{latest_filename}"
    
    def get_available_versions(self, bucket: str, base_path: str) -> List[Dict[str, Any]]:
        """
        Get all available versions for a specification file.
        
        Args:
            bucket: S3 bucket name
            base_path: Base file path
            
        Returns:
            List of version information dictionaries
        """
        versions = []
        
        try:
            # Extract the base name pattern
            path_parts = base_path.split('/')
            filename = path_parts[-1]
            directory = '/'.join(path_parts[:-1])
            name_without_ext = filename.replace('.json', '')
            
            # List objects with the base pattern
            prefix = f"{directory}/{name_without_ext}_v"
            
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix
            )
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    
                    # Extract version from filename
                    version_match = key.split('_v')[-1].replace('.json', '')
                    if version_match and version_match != 'latest':
                        versions.append({
                            'version': version_match,
                            'file_path': key,
                            'last_modified': obj['LastModified'].isoformat(),
                            'size': obj['Size']
                        })
            
            # Sort by version (assuming semantic versioning)
            versions.sort(key=lambda x: self._parse_version(x['version']), reverse=True)
            
            logger.info(f"Found {len(versions)} versions for {base_path}")
            return versions
            
        except ClientError as e:
            logger.error(f"Error listing versions for {base_path}: {str(e)}")
            return []
    
    def get_version_content(self, bucket: str, base_path: str, version: str = "latest") -> Optional[Dict[str, Any]]:
        """
        Get content for a specific version.
        
        Args:
            bucket: S3 bucket name
            base_path: Base file path
            version: Version to retrieve ("latest" for most recent)
            
        Returns:
            Content dictionary or None if not found
        """
        try:
            if version == "latest":
                # Try to get the latest version file first
                latest_path = self.create_latest_symlink(base_path, version)
                try:
                    response = self.s3_client.get_object(Bucket=bucket, Key=latest_path)
                    content = json.loads(response['Body'].read().decode('utf-8'))
                    logger.info(f"Retrieved latest version from {latest_path}")
                    return content
                except ClientError:
                    # If latest doesn't exist, get the most recent version
                    versions = self.get_available_versions(bucket, base_path)
                    if versions:
                        version = versions[0]['version']  # Most recent version
                        logger.info(f"Latest symlink not found, using version {version}")
                    else:
                        logger.warning(f"No versions found for {base_path}")
                        return None
            
            # Get specific version
            versioned_path = self.create_versioned_file_path(base_path, version)
            response = self.s3_client.get_object(Bucket=bucket, Key=versioned_path)
            content = json.loads(response['Body'].read().decode('utf-8'))
            
            logger.info(f"Retrieved version {version} from {versioned_path}")
            return content
            
        except ClientError as e:
            logger.error(f"Error retrieving version {version} for {base_path}: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON for version {version}: {str(e)}")
            return None
    
    def upload_versioned_content(
        self, 
        bucket: str, 
        base_path: str, 
        content: Dict[str, Any], 
        version: str,
        set_as_latest: bool = True
    ) -> bool:
        """
        Upload content with version tagging.
        
        Args:
            bucket: S3 bucket name
            base_path: Base file path
            content: Content to upload
            version: Version string
            set_as_latest: Whether to also upload as "latest"
            
        Returns:
            Success status
        """
        try:
            # Add version tag to content
            versioned_content = self.add_version_tag(content.copy(), version)
            json_content = json.dumps(versioned_content, indent=2, ensure_ascii=False)
            
            # Upload versioned file
            versioned_path = self.create_versioned_file_path(base_path, version)
            self.s3_client.put_object(
                Bucket=bucket,
                Key=versioned_path,
                Body=json_content.encode('utf-8'),
                ContentType='application/json',
                ServerSideEncryption='AES256'
            )
            
            logger.info(f"Uploaded version {version} to {versioned_path}")
            
            # Upload as latest if requested
            if set_as_latest:
                latest_path = self.create_latest_symlink(base_path, version)
                self.s3_client.put_object(
                    Bucket=bucket,
                    Key=latest_path,
                    Body=json_content.encode('utf-8'),
                    ContentType='application/json',
                    ServerSideEncryption='AES256'
                )
                
                logger.info(f"Uploaded as latest version to {latest_path}")
            
            return True
            
        except ClientError as e:
            logger.error(f"Error uploading version {version}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading version {version}: {str(e)}")
            return False
    
    def list_all_versions(self, bucket: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        List all versions for all specification files.
        
        Args:
            bucket: S3 bucket name
            
        Returns:
            Dictionary mapping base paths to version lists
        """
        all_versions = {}
        
        try:
            # List all objects in the specifications directory
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix='specifications/'
            )
            
            if 'Contents' in response:
                # Group files by base name
                base_files = {}
                
                for obj in response['Contents']:
                    key = obj['Key']
                    
                    # Skip latest files for now
                    if '_latest.json' in key:
                        continue
                    
                    # Extract base path
                    if '_v' in key:
                        base_path = key.split('_v')[0] + '.json'
                    else:
                        base_path = key
                    
                    if base_path not in base_files:
                        base_files[base_path] = []
                    
                    base_files[base_path].append(obj)
                
                # Get versions for each base file
                for base_path in base_files:
                    versions = self.get_available_versions(bucket, base_path)
                    if versions:
                        all_versions[base_path] = versions
            
            logger.info(f"Found versions for {len(all_versions)} specification files")
            return all_versions
            
        except ClientError as e:
            logger.error(f"Error listing all versions: {str(e)}")
            return {}
    
    def cleanup_old_versions(self, bucket: str, base_path: str, keep_versions: int = 5) -> int:
        """
        Clean up old versions, keeping only the most recent ones.
        
        Args:
            bucket: S3 bucket name
            base_path: Base file path
            keep_versions: Number of versions to keep
            
        Returns:
            Number of versions deleted
        """
        versions = self.get_available_versions(bucket, base_path)
        
        if len(versions) <= keep_versions:
            logger.info(f"No cleanup needed for {base_path} ({len(versions)} versions)")
            return 0
        
        # Delete older versions
        versions_to_delete = versions[keep_versions:]
        deleted_count = 0
        
        for version_info in versions_to_delete:
            try:
                self.s3_client.delete_object(
                    Bucket=bucket,
                    Key=version_info['file_path']
                )
                deleted_count += 1
                logger.info(f"Deleted old version: {version_info['file_path']}")
                
            except ClientError as e:
                logger.error(f"Error deleting version {version_info['file_path']}: {str(e)}")
        
        logger.info(f"Cleaned up {deleted_count} old versions for {base_path}")
        return deleted_count
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.utcnow().isoformat() + 'Z'
    
    def _parse_version(self, version_str: str) -> tuple:
        """Parse version string for sorting (supports semantic versioning)"""
        try:
            # Handle semantic versioning (e.g., "2024.1.0")
            parts = version_str.split('.')
            return tuple(int(part) for part in parts)
        except ValueError:
            # Fallback for non-numeric versions
            return (0, 0, 0)
    
    def get_version_selection_logic(self, requested_version: Optional[str] = None) -> str:
        """
        Implement version selection logic for GenerateLambda.
        
        Args:
            requested_version: Version requested by user (None for default)
            
        Returns:
            Version string to use
        """
        if requested_version is None or requested_version == "latest":
            return "latest"
        
        # Validate version format
        if not self._is_valid_version_format(requested_version):
            logger.warning(f"Invalid version format: {requested_version}, using latest")
            return "latest"
        
        return requested_version
    
    def _is_valid_version_format(self, version: str) -> bool:
        """Validate version format"""
        # Allow semantic versioning patterns
        import re
        pattern = r'^\d+(\.\d+)*$'
        return bool(re.match(pattern, version))
    
    def test_multi_version_support(self, bucket: str, base_path: str) -> Dict[str, Any]:
        """
        Test multi-version support for a specification file.
        
        Args:
            bucket: S3 bucket name
            base_path: Base file path to test
            
        Returns:
            Test results dictionary
        """
        test_results = {
            'versions_found': 0,
            'latest_accessible': False,
            'specific_version_accessible': False,
            'version_list': [],
            'errors': []
        }
        
        try:
            # Test version listing
            versions = self.get_available_versions(bucket, base_path)
            test_results['versions_found'] = len(versions)
            test_results['version_list'] = [v['version'] for v in versions]
            
            # Test latest version access
            latest_content = self.get_version_content(bucket, base_path, "latest")
            test_results['latest_accessible'] = latest_content is not None
            
            # Test specific version access
            if versions:
                specific_version = versions[0]['version']
                specific_content = self.get_version_content(bucket, base_path, specific_version)
                test_results['specific_version_accessible'] = specific_content is not None
            
            logger.info(f"Multi-version test completed for {base_path}")
            
        except Exception as e:
            error_msg = f"Error testing multi-version support: {str(e)}"
            test_results['errors'].append(error_msg)
            logger.error(error_msg)
        
        return test_results