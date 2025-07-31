"""
Main entry point for Claude Multi-Agent Orchestrator CLI
"""

import argparse
import logging
import sys
from .orchestrator import Orchestrator, OrchestratorConfig


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Claude Multi-Agent Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with default configuration
  claude-orchestrator
  
  # Start with custom session name
  claude-orchestrator --session my-agents
  
  # Start with custom Claude binary
  claude-orchestrator --claude-bin /path/to/claude
        """
    )
    
    parser.add_argument(
        '--session', '-s',
        default='claude-agents',
        help='Tmux session name (default: claude-agents)'
    )
    
    parser.add_argument(
        '--claude-bin', '-c',
        default=None,
        help='Path to Claude binary'
    )
    
    parser.add_argument(
        '--poll-interval', '-p',
        type=float,
        default=0.5,
        help='Session file poll interval in seconds (default: 0.5)'
    )
    
    parser.add_argument(
        '--log-level', '-l',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create config
    config = OrchestratorConfig(
        session_name=args.session,
        poll_interval=args.poll_interval
    )
    
    if args.claude_bin:
        config.claude_bin = args.claude_bin
    
    # Create and run orchestrator
    print(f"Starting orchestrator with session '{args.session}'...")
    orchestrator = Orchestrator(config)
    
    print("\nNote: This CLI starts an empty orchestrator.")
    print("You need to register agents programmatically.")
    print("See examples/basic_two_agent.py for a complete example.\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())