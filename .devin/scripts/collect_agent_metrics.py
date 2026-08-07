#!/usr/bin/env python3
"""
Agent metrics collection script for Devin runtime optimization.

This script collects usage metrics for agents, skills, workflows, and MCP servers
to inform optimization decisions.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class AgentMetricsCollector:
    """Collects and updates agent usage metrics."""
    
    def __init__(self, metrics_path: Path):
        self.metrics_path = metrics_path
        self.metrics = self._load_metrics()
    
    def _load_metrics(self) -> Dict[str, Any]:
        """Load existing metrics or create new structure."""
        if self.metrics_path.exists():
            with open(self.metrics_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._create_empty_metrics()
    
    def _create_empty_metrics(self) -> Dict[str, Any]:
        """Create empty metrics structure."""
        return {
            "version": "1.0",
            "description": "Agent usage metrics for Devin runtime optimization",
            "metrics_collection_start": datetime.now().isoformat(),
            "agents": {},
            "skills": {},
            "workflows": {},
            "mcp_servers": {}
        }
    
    def record_agent_call(
        self,
        agent_name: str,
        duration_ms: int,
        success: bool,
        mode: str = "",
        scope: str = ""
    ) -> None:
        """Record a metrics entry for an agent call."""
        if agent_name not in self.metrics["agents"]:
            self.metrics["agents"][agent_name] = {
                "call_count": 0,
                "last_used": None,
                "average_duration_ms": 0,
                "success_rate": 0.0,
                "common_modes": [],
                "typical_scope": []
            }
        
        agent = self.metrics["agents"][agent_name]
        agent["call_count"] += 1
        agent["last_used"] = datetime.now().isoformat()
        
        # Update average duration
        total_duration = agent["average_duration_ms"] * (agent["call_count"] - 1) + duration_ms
        agent["average_duration_ms"] = total_duration / agent["call_count"]
        
        # Update success rate
        if success:
            agent["success_rate"] = (agent["success_rate"] * (agent["call_count"] - 1) + 1.0) / agent["call_count"]
        else:
            agent["success_rate"] = (agent["success_rate"] * (agent["call_count"] - 1)) / agent["call_count"]
        
        # Track common modes and scopes
        if mode and mode not in agent["common_modes"]:
            agent["common_modes"].append(mode)
        if scope and scope not in agent["typical_scope"]:
            agent["typical_scope"].append(scope)
    
    def record_skill_call(
        self,
        skill_name: str,
        duration_ms: int
    ) -> None:
        """Record a metrics entry for a skill call."""
        if skill_name not in self.metrics["skills"]:
            self.metrics["skills"][skill_name] = {
                "call_count": 0,
                "last_used": None,
                "average_duration_ms": 0
            }
        
        skill = self.metrics["skills"][skill_name]
        skill["call_count"] += 1
        skill["last_used"] = datetime.now().isoformat()
        
        # Update average duration
        total_duration = skill["average_duration_ms"] * (skill["call_count"] - 1) + duration_ms
        skill["average_duration_ms"] = total_duration / skill["call_count"]
    
    def record_workflow_call(
        self,
        workflow_name: str,
        duration_ms: int,
        success: bool
    ) -> None:
        """Record a metrics entry for a workflow call."""
        if workflow_name not in self.metrics["workflows"]:
            self.metrics["workflows"][workflow_name] = {
                "call_count": 0,
                "last_used": None,
                "average_duration_ms": 0,
                "success_rate": 0.0
            }
        
        workflow = self.metrics["workflows"][workflow_name]
        workflow["call_count"] += 1
        workflow["last_used"] = datetime.now().isoformat()
        
        # Update average duration
        total_duration = workflow["average_duration_ms"] * (workflow["call_count"] - 1) + duration_ms
        workflow["average_duration_ms"] = total_duration / workflow["call_count"]
        
        # Update success rate
        if success:
            workflow["success_rate"] = (workflow["success_rate"] * (workflow["call_count"] - 1) + 1.0) / workflow["call_count"]
        else:
            workflow["success_rate"] = (workflow["success_rate"] * (workflow["call_count"] - 1)) / workflow["call_count"]
    
    def record_mcp_call(
        self,
        mcp_name: str,
        duration_ms: int
    ) -> None:
        """Record a metrics entry for an MCP server call."""
        if mcp_name not in self.metrics["mcp_servers"]:
            self.metrics["mcp_servers"][mcp_name] = {
                "call_count": 0,
                "last_used": None,
                "average_duration_ms": 0
            }
        
        mcp = self.metrics["mcp_servers"][mcp_name]
        mcp["call_count"] += 1
        mcp["last_used"] = datetime.now().isoformat()
        
        # Update average duration
        total_duration = mcp["average_duration_ms"] * (mcp["call_count"] - 1) + duration_ms
        mcp["average_duration_ms"] = total_duration / mcp["call_count"]
    
    def save_metrics(self) -> None:
        """Save metrics to file."""
        with open(self.metrics_path, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False)
    
    def generate_report(self) -> str:
        """Generate a human-readable metrics report."""
        report = []
        report.append("# Agent Usage Metrics Report")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        # Agent usage
        report.append("## Agent Usage")
        for agent_name, metrics in sorted(self.metrics["agents"].items(), key=lambda x: x[1]["call_count"], reverse=True):
            if metrics["call_count"] > 0:
                report.append(f"- {agent_name}: {metrics['call_count']} calls, "
                           f"{metrics['average_duration_ms']:.1f}ms avg, "
                           f"{metrics['success_rate']:.1%} success")
        
        # Skill usage
        report.append("\n## Skill Usage")
        for skill_name, metrics in sorted(self.metrics["skills"].items(), key=lambda x: x[1]["call_count"], reverse=True):
            if metrics["call_count"] > 0:
                report.append(f"- {skill_name}: {metrics['call_count']} calls, "
                           f"{metrics['average_duration_ms']:.1f}ms avg")
        
        # Workflow usage
        report.append("\n## Workflow Usage")
        for workflow_name, metrics in sorted(self.metrics["workflows"].items(), key=lambda x: x[1]["call_count"], reverse=True):
            if metrics["call_count"] > 0:
                report.append(f"- {workflow_name}: {metrics['call_count']} calls, "
                           f"{metrics['average_duration_ms']:.1f}ms avg, "
                           f"{metrics['success_rate']:.1%} success")
        
        # MCP usage
        report.append("\n## MCP Server Usage")
        for mcp_name, metrics in sorted(self.metrics["mcp_servers"].items(), key=lambda x: x[1]["call_count"], reverse=True):
            if metrics["call_count"] > 0:
                report.append(f"- {mcp_name}: {metrics['call_count']} calls, "
                           f"{metrics['average_duration_ms']:.1f}ms avg")
        
        return "\n".join(report)
    
    def analyze_mcp_usage(self, days_threshold: int = 30) -> Dict[str, Any]:
        """Analyze MCP server usage and provide optimization recommendations."""
        from datetime import datetime, timedelta
        
        recommendations = []
        unused_servers = []
        low_usage_servers = []
        
        threshold_date = datetime.now() - timedelta(days=days_threshold)
        
        for mcp_name, metrics in self.metrics["mcp_servers"].items():
            if metrics["call_count"] == 0:
                unused_servers.append(mcp_name)
            elif metrics["call_count"] < 5:
                low_usage_servers.append(mcp_name)
            elif metrics["last_used"]:
                last_used = datetime.fromisoformat(metrics["last_used"])
                if last_used < threshold_date:
                    unused_servers.append(f"{mcp_name} (unused for {days_threshold}+ days)")
        
        if unused_servers:
            recommendations.append({
                "type": "unused_servers",
                "servers": unused_servers,
                "action": "Consider removing or disabling these MCP servers",
                "priority": "medium"
            })
        
        if low_usage_servers:
            recommendations.append({
                "type": "low_usage_servers",
                "servers": low_usage_servers,
                "action": "Monitor usage; consider consolidating if usage remains low",
                "priority": "low"
            })
        
        return {
            "analysis_date": datetime.now().isoformat(),
            "days_threshold": days_threshold,
            "total_mcp_servers": len(self.metrics["mcp_servers"]),
            "unused_count": len(unused_servers),
            "low_usage_count": len(low_usage_servers),
            "recommendations": recommendations
        }


def main():
    """Main entry point for metrics collection."""
    import sys
    
    metrics_path = Path(__file__).parent.parent / "agent-metrics.json"
    collector = AgentMetricsCollector(metrics_path)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "report":
            print(collector.generate_report())
        elif command == "reset":
            collector.metrics = collector._create_empty_metrics()
            collector.save_metrics()
            print("Metrics reset successfully")
        elif command == "analyze-mcp":
            days_threshold = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            analysis = collector.analyze_mcp_usage(days_threshold)
            print(json.dumps(analysis, indent=2, ensure_ascii=False))
        else:
            print(f"Unknown command: {command}")
            print("Available commands: report, reset, analyze-mcp [days]")
    else:
        print("Usage: python collect_agent_metrics.py [report|reset|analyze-mcp [days]]")


if __name__ == "__main__":
    main()