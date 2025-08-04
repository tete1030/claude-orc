"""
Container Health Service

Handles health checks for Docker containers.
"""
import subprocess
from typing import Dict, Any, List

from .container_discovery_service import ContainerInfo


class ContainerHealthService:
    """Service for checking container health"""
    
    def check_container_health(self, container: ContainerInfo) -> Dict[str, Any]:
        """Check health of individual container"""
        health = {
            "name": container.name,
            "status": "healthy",
            "running": container.running,
            "claude_process": False,
            "session_files": False,
            "resource_usage": {},
            "issues": [],
        }
        
        if not container.running:
            health["status"] = "stopped"
            health["issues"].append("Container is not running")
            return health
        
        try:
            # Check Claude process
            result = subprocess.run(
                ["docker", "exec", container.name, "pgrep", "-f", "claude"],
                capture_output=True,
                text=True,
            )
            
            health["claude_process"] = result.returncode == 0
            if not health["claude_process"]:
                health["issues"].append("Claude process not found")
                health["status"] = "unhealthy"
            
            # Check session files
            result = subprocess.run(
                ["docker", "exec", container.name, "test", "-f", "/home/developer/.claude.json"],
                capture_output=True,
                text=True,
            )
            
            health["session_files"] = result.returncode == 0
            if not health["session_files"]:
                health["issues"].append("Claude session files missing")
            
            # Check resource usage
            result = subprocess.run(
                [
                    "docker",
                    "stats",
                    "--no-stream",
                    "--format",
                    "{{.CPUPerc}}\t{{.MemUsage}}",
                    container.name,
                ],
                capture_output=True,
                text=True,
            )
            
            if result.returncode == 0 and result.stdout.strip():
                stats = result.stdout.strip().split("\t")
                if len(stats) >= 2:
                    health["resource_usage"] = {
                        "cpu_percent": stats[0], 
                        "memory_usage": stats[1]
                    }
        
        except subprocess.CalledProcessError:
            health["status"] = "error"
            health["issues"].append("Failed to check container health")
        
        return health
    
    def check_all_containers_health(self, containers: List[ContainerInfo]) -> Dict[str, Dict[str, Any]]:
        """Check health of multiple containers"""
        health_results = {}
        
        for container in containers:
            health_results[container.name] = self.check_container_health(container)
        
        return health_results