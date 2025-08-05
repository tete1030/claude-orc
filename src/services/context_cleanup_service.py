"""
Context Cleanup Service

Handles cleanup of team contexts including containers and tmux sessions.
"""
import subprocess
from typing import List, Optional

from .container_discovery_service import ContextInfo, ContainerInfo
from .tmux_management_service import TmuxManagementService


class ContextCleanupService:
    """Service for cleaning up team contexts"""
    
    def __init__(self, tmux_service: Optional[TmuxManagementService] = None):
        self.tmux_service = tmux_service or TmuxManagementService()
    
    def cleanup_containers(self, containers: List[ContainerInfo]) -> bool:
        """Stop and remove containers"""
        success = True
        
        for container in containers:
            try:
                # First check if container still exists
                check_result = subprocess.run(
                    ["docker", "inspect", container.name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False
                )
                
                if check_result.returncode != 0:
                    # Container doesn't exist (likely removed by --rm flag)
                    print(f"Container {container.name} already removed (auto-cleanup)")
                    continue
                
                if container.running:
                    print(f"Stopping {container.name}...")
                    subprocess.run(
                        ["docker", "stop", container.name], 
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True
                    )
                
                print(f"Removing {container.name}...")
                subprocess.run(
                    ["docker", "rm", "-f", container.name], 
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
            
            except subprocess.CalledProcessError as e:
                # Check if it's because container doesn't exist
                if "No such container" in str(e) or "No such object" in str(e):
                    print(f"Container {container.name} already removed")
                else:
                    print(f"Error removing {container.name}: {e}")
                    success = False
        
        return success
    
    def cleanup_tmux_session(self, session_name: str) -> bool:
        """Remove tmux session"""
        if self.tmux_service.kill_tmux_session(session_name):
            print(f"Removed tmux session {session_name}")
            return True
        else:
            print(f"Error removing tmux session {session_name}")
            return False
    
    def cleanup_context(self, context: ContextInfo, force: bool = False) -> bool:
        """Complete cleanup of a team context"""
        print(f"\nContext cleanup for: {context.name}")
        print(f"Containers to remove: {len(context.containers)}")
        for container in context.containers:
            print(f"  - {container.name} ({container.status})")
        
        if context.tmux_session:
            print(f"Tmux session to remove: {context.tmux_session}")
        
        if not force:
            confirm = input(
                "\nThis will permanently delete all session data. Continue? (type 'yes'): "
            )
            if confirm.lower() != "yes":
                print("Cleanup cancelled")
                return False
        
        success = True
        
        # Stop and remove containers
        if not self.cleanup_containers(context.containers):
            success = False
        
        # Remove tmux session
        if context.tmux_session:
            if not self.cleanup_tmux_session(context.tmux_session):
                success = False
        
        if success:
            print(f"\nSession '{context.name}' cleanup completed successfully")
        else:
            print(f"\nSession '{context.name}' cleanup completed with some errors")
        
        return success