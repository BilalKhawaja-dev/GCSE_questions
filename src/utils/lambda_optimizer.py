"""
Lambda Performance Optimization Utilities for GCSE Question Generator V2

This module provides utilities for optimizing Lambda function performance
including connection pooling, memory optimization, and warming strategies.
"""

import os
import time
import boto3
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from src.utils.logging_service import ComprehensiveLoggingService

# Initialize logger
logging_service = ComprehensiveLoggingService("lambda_optimizer")
logger = logging_service.logger

class ConnectionPool:
    """Connection pool for AWS services to reduce cold start overhead."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not getattr(self, '_initialized', False):
            self._connections = {}
            self._connection_times = {}
            self._max_age_seconds = 300  # 5 minutes
            self._initialized = True
    
    def get_dynamodb_resource(self, region: str = 'eu-west-2'):
        """Get a cached DynamoDB resource connection."""
        key = f"dynamodb_resource_{region}"
        
        if self._is_connection_stale(key):
            logger.debug(f"Creating new DynamoDB resource for {region}")
            self._connections[key] = boto3.resource('dynamodb', region_name=region)
            self._connection_times[key] = time.time()
        
        return self._connections[key]
    
    def get_dynamodb_client(self, region: str = 'eu-west-2'):
        """Get a cached DynamoDB client connection."""
        key = f"dynamodb_client_{region}"
        
        if self._is_connection_stale(key):
            logger.debug(f"Creating new DynamoDB client for {region}")
            self._connections[key] = boto3.client('dynamodb', region_name=region)
            self._connection_times[key] = time.time()
        
        return self._connections[key]
    
    def get_bedrock_client(self, region: str = 'eu-west-2'):
        """Get a cached Bedrock client connection."""
        key = f"bedrock_client_{region}"
        
        if self._is_connection_stale(key):
            logger.debug(f"Creating new Bedrock client for {region}")
            self._connections[key] = boto3.client('bedrock-runtime', region_name=region)
            self._connection_times[key] = time.time()
        
        return self._connections[key]
    
    def get_s3_client(self, region: str = 'eu-west-2'):
        """Get a cached S3 client connection."""
        key = f"s3_client_{region}"
        
        if self._is_connection_stale(key):
            logger.debug(f"Creating new S3 client for {region}")
            self._connections[key] = boto3.client('s3', region_name=region)
            self._connection_times[key] = time.time()
        
        return self._connections[key]
    
    def get_cloudwatch_client(self, region: str = 'eu-west-2'):
        """Get a cached CloudWatch client connection."""
        key = f"cloudwatch_client_{region}"
        
        if self._is_connection_stale(key):
            logger.debug(f"Creating new CloudWatch client for {region}")
            self._connections[key] = boto3.client('cloudwatch', region_name=region)
            self._connection_times[key] = time.time()
        
        return self._connections[key]
    
    def _is_connection_stale(self, key: str) -> bool:
        """Check if a connection is stale and needs to be refreshed."""
        if key not in self._connections:
            return True
        
        connection_time = self._connection_times.get(key, 0)
        return (time.time() - connection_time) > self._max_age_seconds
    
    def cleanup_stale_connections(self):
        """Clean up stale connections to free memory."""
        current_time = time.time()
        stale_keys = []
        
        for key, connection_time in self._connection_times.items():
            if (current_time - connection_time) > self._max_age_seconds:
                stale_keys.append(key)
        
        for key in stale_keys:
            if key in self._connections:
                del self._connections[key]
            if key in self._connection_times:
                del self._connection_times[key]
            logger.debug(f"Cleaned up stale connection: {key}")

# Global connection pool instance
connection_pool = ConnectionPool()

class MemoryOptimizer:
    """Utilities for optimizing Lambda memory usage."""
    
    @staticmethod
    def get_optimal_memory_config(function_type: str) -> Dict[str, Any]:
        """
        Get optimal memory configuration for different Lambda function types.
        
        Args:
            function_type: Type of Lambda function
            
        Returns:
            Dict with memory and timeout recommendations
        """
        configs = {
            'auth': {
                'memory_mb': 256,
                'timeout_seconds': 10,
                'description': 'Lightweight authentication operations'
            },
            'interpret': {
                'memory_mb': 512,
                'timeout_seconds': 30,
                'description': 'Query parsing and prompt enrichment'
            },
            'generate': {
                'memory_mb': 1024,
                'timeout_seconds': 60,
                'description': 'Question generation with Bedrock'
            },
            'feedback': {
                'memory_mb': 256,
                'timeout_seconds': 10,
                'description': 'Simple feedback storage'
            },
            'session': {
                'memory_mb': 512,
                'timeout_seconds': 15,
                'description': 'Session management operations'
            },
            'export': {
                'memory_mb': 1024,
                'timeout_seconds': 30,
                'description': 'PDF generation and export'
            },
            'topic_coverage': {
                'memory_mb': 256,
                'timeout_seconds': 10,
                'description': 'Topic coverage tracking'
            },
            'refinement': {
                'memory_mb': 1536,
                'timeout_seconds': 300,
                'description': 'AI learning and question refinement'
            },
            'cost_monitoring': {
                'memory_mb': 512,
                'timeout_seconds': 60,
                'description': 'Cost analysis and reporting'
            }
        }
        
        return configs.get(function_type, {
            'memory_mb': 512,
            'timeout_seconds': 30,
            'description': 'Default configuration'
        })
    
    @staticmethod
    def monitor_memory_usage(context) -> Dict[str, float]:
        """
        Monitor current memory usage in Lambda.
        
        Args:
            context: Lambda context object
            
        Returns:
            Dict with memory usage metrics
        """
        try:
            import psutil
            
            # Get memory info
            memory_info = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()
            
            return {
                'total_memory_mb': context.memory_limit_in_mb,
                'used_memory_mb': process_memory.rss / 1024 / 1024,
                'available_memory_mb': context.memory_limit_in_mb - (process_memory.rss / 1024 / 1024),
                'memory_utilization_percent': (process_memory.rss / 1024 / 1024) / context.memory_limit_in_mb * 100,
                'system_memory_percent': memory_info.percent
            }
        except ImportError:
            # psutil not available, return basic info
            return {
                'total_memory_mb': context.memory_limit_in_mb,
                'used_memory_mb': 0,
                'available_memory_mb': context.memory_limit_in_mb,
                'memory_utilization_percent': 0,
                'system_memory_percent': 0
            }
    
    @staticmethod
    def optimize_imports():
        """Optimize imports to reduce cold start time."""
        # Import heavy libraries only when needed
        import sys
        
        # Remove unused modules from memory
        modules_to_remove = []
        for module_name in sys.modules:
            if module_name.startswith('test_') or module_name.startswith('pytest'):
                modules_to_remove.append(module_name)
        
        for module_name in modules_to_remove:
            del sys.modules[module_name]
        
        logger.debug(f"Removed {len(modules_to_remove)} unused modules")

class LambdaWarmer:
    """Utilities for Lambda warming to reduce cold starts."""
    
    @staticmethod
    def is_warming_request(event: Dict[str, Any]) -> bool:
        """
        Check if the request is a warming request.
        
        Args:
            event: Lambda event
            
        Returns:
            bool: True if this is a warming request
        """
        return event.get('source') == 'lambda-warmer' or event.get('warmer') is True
    
    @staticmethod
    def handle_warming_request(function_name: str) -> Dict[str, Any]:
        """
        Handle a warming request.
        
        Args:
            function_name: Name of the Lambda function
            
        Returns:
            Dict with warming response
        """
        logger.info(f"Handling warming request for {function_name}")
        
        # Initialize connections to warm them up
        connection_pool.get_dynamodb_resource()
        connection_pool.get_s3_client()
        
        # Clean up any stale connections
        connection_pool.cleanup_stale_connections()
        
        return {
            'statusCode': 200,
            'body': {
                'message': f'{function_name} warmed successfully',
                'timestamp': datetime.utcnow().isoformat(),
                'warmed': True
            }
        }
    
    @staticmethod
    def create_warming_event() -> Dict[str, Any]:
        """
        Create a warming event for testing.
        
        Returns:
            Dict with warming event structure
        """
        return {
            'source': 'lambda-warmer',
            'warmer': True,
            'timestamp': datetime.utcnow().isoformat()
        }

class PerformanceProfiler:
    """Utilities for profiling Lambda performance."""
    
    def __init__(self):
        self.start_time = time.time()
        self.checkpoints = []
    
    def checkpoint(self, name: str, metadata: Dict[str, Any] = None):
        """
        Add a performance checkpoint.
        
        Args:
            name: Name of the checkpoint
            metadata: Optional metadata for the checkpoint
        """
        current_time = time.time()
        duration_ms = (current_time - self.start_time) * 1000
        
        checkpoint = {
            'name': name,
            'timestamp': current_time,
            'duration_ms': duration_ms,
            'metadata': metadata or {}
        }
        
        self.checkpoints.append(checkpoint)
        logger.debug(f"Performance checkpoint '{name}': {duration_ms:.2f}ms")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get a summary of performance metrics.
        
        Returns:
            Dict with performance summary
        """
        if not self.checkpoints:
            return {'total_duration_ms': 0, 'checkpoints': []}
        
        total_duration = (time.time() - self.start_time) * 1000
        
        # Calculate durations between checkpoints
        checkpoint_durations = []
        prev_time = self.start_time
        
        for checkpoint in self.checkpoints:
            duration = (checkpoint['timestamp'] - prev_time) * 1000
            checkpoint_durations.append({
                'name': checkpoint['name'],
                'duration_ms': duration,
                'cumulative_ms': checkpoint['duration_ms'],
                'metadata': checkpoint['metadata']
            })
            prev_time = checkpoint['timestamp']
        
        return {
            'total_duration_ms': total_duration,
            'checkpoint_count': len(self.checkpoints),
            'checkpoints': checkpoint_durations,
            'slowest_checkpoint': max(checkpoint_durations, key=lambda x: x['duration_ms']) if checkpoint_durations else None
        }

def optimize_lambda_performance(function_type: str, context, event: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Apply performance optimizations for a Lambda function.
    
    Args:
        function_type: Type of Lambda function
        context: Lambda context object
        event: Optional Lambda event
        
    Returns:
        Dict with optimization results
    """
    profiler = PerformanceProfiler()
    
    # Handle warming requests
    if event and LambdaWarmer.is_warming_request(event):
        return LambdaWarmer.handle_warming_request(f"{function_type}_lambda")
    
    profiler.checkpoint("optimization_start")
    
    # Optimize imports
    MemoryOptimizer.optimize_imports()
    profiler.checkpoint("imports_optimized")
    
    # Initialize connection pool
    connection_pool.cleanup_stale_connections()
    profiler.checkpoint("connections_cleaned")
    
    # Get memory usage
    memory_usage = MemoryOptimizer.monitor_memory_usage(context)
    profiler.checkpoint("memory_monitored", memory_usage)
    
    # Get optimal configuration
    optimal_config = MemoryOptimizer.get_optimal_memory_config(function_type)
    profiler.checkpoint("config_retrieved")
    
    performance_summary = profiler.get_performance_summary()
    
    logger.info(f"Lambda optimization completed for {function_type}: {performance_summary['total_duration_ms']:.2f}ms")
    
    return {
        'function_type': function_type,
        'optimization_duration_ms': performance_summary['total_duration_ms'],
        'memory_usage': memory_usage,
        'optimal_config': optimal_config,
        'performance_summary': performance_summary
    }

# Decorator for automatic performance optimization
def performance_optimized(function_type: str):
    """
    Decorator to automatically apply performance optimizations to Lambda handlers.
    
    Args:
        function_type: Type of Lambda function
    """
    def decorator(handler_func):
        def wrapper(event, context):
            # Apply optimizations
            optimization_result = optimize_lambda_performance(function_type, context, event)
            
            # If this was a warming request, return early
            if event and LambdaWarmer.is_warming_request(event):
                return optimization_result
            
            # Add optimization info to event for handler use
            event['_optimization'] = optimization_result
            
            # Call the original handler
            return handler_func(event, context)
        
        return wrapper
    return decorator