#!/usr/bin/env python3
"""
CI/CD Health Monitoring - Track build health across all repositories.

Detects:
- Flaky tests
- Build time trends
- Success rate degradation
- Common failure patterns
"""

import json
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict, Counter


class CIHealthMonitor:
    def __init__(self, repos: List[str]):
        self.repos = repos
        self.health_data = {}

    def analyze_all_repos(self) -> Dict:
        """Analyze CI health across all repos."""
        print("📊 Analyzing CI/CD health across all repositories...\n")

        for repo in self.repos:
            print(f"  Analyzing {repo}...")
            self.health_data[repo] = self.analyze_repo_ci(repo)

        return self.generate_health_report()

    def analyze_repo_ci(self, repo: str) -> Dict:
        """Analyze CI health for a single repo."""
        try:
            # Get last 100 workflow runs
            result = subprocess.run([
                'gh', 'run', 'list',
                '--repo', f'cboyd0319/{repo}',
                '--limit', '100',
                '--json', 'conclusion,createdAt,name,durationMs'
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return self.get_empty_health_data()

            runs = json.loads(result.stdout)

            return {
                'total_runs': len(runs),
                'success_rate': self.calculate_success_rate(runs),
                'average_duration': self.calculate_average_duration(runs),
                'duration_trend': self.calculate_duration_trend(runs),
                'flaky_workflows': self.detect_flaky_workflows(repo),
                'common_failures': self.analyze_failure_patterns(repo),
                'last_success': self.get_last_successful_run(runs)
            }

        except Exception as e:
            print(f"    ⚠️  Failed to analyze CI: {e}")
            return self.get_empty_health_data()

    def get_empty_health_data(self) -> Dict:
        """Return empty health data structure."""
        return {
            'total_runs': 0,
            'success_rate': 0.0,
            'average_duration': 0,
            'duration_trend': 'unknown',
            'flaky_workflows': [],
            'common_failures': [],
            'last_success': None
        }

    def calculate_success_rate(self, runs: List[Dict]) -> float:
        """Calculate percentage of successful runs."""
        if not runs:
            return 0.0

        successful = len([r for r in runs if r.get('conclusion') == 'success'])
        return (successful / len(runs)) * 100

    def calculate_average_duration(self, runs: List[Dict]) -> int:
        """Calculate average duration in seconds."""
        durations = [r.get('durationMs', 0) for r in runs if r.get('durationMs')]
        if not durations:
            return 0

        avg_ms = sum(durations) / len(durations)
        return int(avg_ms / 1000)  # Convert to seconds

    def calculate_duration_trend(self, runs: List[Dict]) -> str:
        """Determine if build times are increasing, decreasing, or stable."""
        if len(runs) < 20:
            return 'insufficient_data'

        # Compare first 10 vs last 10
        recent = [r.get('durationMs', 0) for r in runs[:10] if r.get('durationMs')]
        older = [r.get('durationMs', 0) for r in runs[-10:] if r.get('durationMs')]

        if not recent or not older:
            return 'unknown'

        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older)

        change_pct = ((avg_recent - avg_older) / avg_older) * 100

        if change_pct > 10:
            return 'increasing'
        elif change_pct < -10:
            return 'decreasing'
        else:
            return 'stable'

    def detect_flaky_workflows(self, repo: str) -> List[Dict]:
        """
        Detect workflows that fail intermittently (flaky tests).

        A workflow is flaky if:
        - It fails sometimes but succeeds other times
        - Same commit/conditions
        - Pattern of failure-success-failure
        """
        try:
            # Get detailed run history
            result = subprocess.run([
                'gh', 'run', 'list',
                '--repo', f'cboyd0319/{repo}',
                '--limit', '50',
                '--json', 'name,conclusion,headSha'
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return []

            runs = json.loads(result.stdout)

            # Group by workflow name
            workflows = defaultdict(list)
            for run in runs:
                workflows[run['name']].append(run['conclusion'])

            # Detect flakiness
            flaky = []
            for workflow_name, conclusions in workflows.items():
                if len(conclusions) < 5:
                    continue  # Not enough data

                successes = conclusions.count('success')
                failures = conclusions.count('failure')

                # Flaky if both successes and failures present
                if successes > 0 and failures > 0:
                    flakiness_rate = failures / len(conclusions) * 100
                    if 10 < flakiness_rate < 90:  # Not always failing, not always passing
                        flaky.append({
                            'workflow': workflow_name,
                            'flakiness_rate': round(flakiness_rate, 1),
                            'total_runs': len(conclusions),
                            'successes': successes,
                            'failures': failures
                        })

            return sorted(flaky, key=lambda x: x['flakiness_rate'], reverse=True)

        except Exception as e:
            print(f"    ⚠️  Failed to detect flaky workflows: {e}")
            return []

    def analyze_failure_patterns(self, repo: str) -> List[Dict]:
        """Analyze common failure reasons."""
        try:
            # Get recent failed runs
            result = subprocess.run([
                'gh', 'run', 'list',
                '--repo', f'cboyd0319/{repo}',
                '--status', 'failure',
                '--limit', '20',
                '--json', 'name,conclusion,url'
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return []

            failed_runs = json.loads(result.stdout)

            # Count failures by workflow
            failure_counts = Counter(run['name'] for run in failed_runs)

            return [
                {
                    'workflow': workflow,
                    'failure_count': count,
                    'percentage': round((count / len(failed_runs)) * 100, 1)
                }
                for workflow, count in failure_counts.most_common(5)
            ]

        except Exception as e:
            print(f"    ⚠️  Failed to analyze failures: {e}")
            return []

    def get_last_successful_run(self, runs: List[Dict]) -> str:
        """Get timestamp of last successful run."""
        for run in runs:
            if run.get('conclusion') == 'success':
                return run.get('createdAt')
        return None

    def recommend_optimizations(self, repo: str, health_data: Dict) -> List[str]:
        """Suggest ways to improve CI performance."""
        recommendations = []

        # Build time increasing
        if health_data['duration_trend'] == 'increasing':
            avg_duration = health_data['average_duration']
            recommendations.append(
                f"⚠️  Build times increasing (avg: {avg_duration}s). "
                "Consider adding dependency caching or parallelizing tests."
            )

        # Low success rate
        if health_data['success_rate'] < 90:
            recommendations.append(
                f"🚨 Low success rate ({health_data['success_rate']:.1f}%). "
                "Investigate common failure patterns."
            )

        # Flaky tests detected
        if health_data['flaky_workflows']:
            flaky_count = len(health_data['flaky_workflows'])
            recommendations.append(
                f"🔍 {flaky_count} flaky workflow(s) detected. "
                "Fix intermittent test failures to improve reliability."
            )

        # Long build times
        if health_data['average_duration'] > 600:  # > 10 minutes
            recommendations.append(
                "⏱️  Long build times (>10 min). "
                "Consider matrix builds or splitting workflows."
            )

        return recommendations

    def generate_health_report(self) -> Dict:
        """Generate final health report."""
        overall_health = []
        all_recommendations = {}

        for repo, health_data in self.health_data.items():
            # Calculate health score (0-100)
            score = self.calculate_health_score(health_data)
            overall_health.append(score)

            # Generate recommendations
            all_recommendations[repo] = self.recommend_optimizations(repo, health_data)

        avg_health = sum(overall_health) / len(overall_health) if overall_health else 0

        return {
            'overall_health_score': round(avg_health, 1),
            'repos': self.health_data,
            'recommendations': all_recommendations,
            'summary': {
                'total_repos': len(self.repos),
                'healthy_repos': len([s for s in overall_health if s >= 80]),
                'needs_attention': len([s for s in overall_health if s < 80])
            }
        }

    def calculate_health_score(self, health_data: Dict) -> float:
        """Calculate health score (0-100) for a repo."""
        score = 100.0

        # Success rate impact (max -30 points)
        success_rate = health_data['success_rate']
        if success_rate < 100:
            score -= (100 - success_rate) * 0.3

        # Flaky tests impact (max -20 points)
        flaky_count = len(health_data['flaky_workflows'])
        score -= min(flaky_count * 5, 20)

        # Duration trend impact (-10 points if increasing)
        if health_data['duration_trend'] == 'increasing':
            score -= 10

        # Long build times (-10 points if > 10 min)
        if health_data['average_duration'] > 600:
            score -= 10

        return max(0.0, score)

    def generate_markdown_report(self, health_report: Dict, output_path: str):
        """Generate human-readable markdown report."""
        report = f"""# CI/CD Health Report

**Date**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

## Overall Health

**Score**: {health_report['overall_health_score']}/100
{'✅ GOOD' if health_report['overall_health_score'] >= 80 else '⚠️  NEEDS ATTENTION'}

- **Healthy Repos**: {health_report['summary']['healthy_repos']}/{health_report['summary']['total_repos']}
- **Needs Attention**: {health_report['summary']['needs_attention']}

---

"""

        for repo, health_data in health_report['repos'].items():
            score = self.calculate_health_score(health_data)
            status_emoji = "✅" if score >= 80 else "⚠️"

            report += f"## {status_emoji} {repo}\n\n"
            report += f"**Health Score**: {score:.1f}/100\n\n"
            report += f"### Metrics\n\n"
            report += f"- **Success Rate**: {health_data['success_rate']:.1f}%\n"
            report += f"- **Average Build Time**: {health_data['average_duration']}s "
            report += f"({health_data['duration_trend']})\n"
            report += f"- **Total Runs Analyzed**: {health_data['total_runs']}\n\n"

            if health_data['flaky_workflows']:
                report += "### 🔍 Flaky Workflows\n\n"
                for flaky in health_data['flaky_workflows']:
                    report += f"- **{flaky['workflow']}**: "
                    report += f"{flaky['flakiness_rate']}% flaky "
                    report += f"({flaky['failures']}/{flaky['total_runs']} failures)\n"
                report += "\n"

            if health_data['common_failures']:
                report += "### ❌ Common Failures\n\n"
                for failure in health_data['common_failures']:
                    report += f"- **{failure['workflow']}**: "
                    report += f"{failure['failure_count']} failures "
                    report += f"({failure['percentage']}%)\n"
                report += "\n"

            recommendations = health_report['recommendations'].get(repo, [])
            if recommendations:
                report += "### 💡 Recommendations\n\n"
                for rec in recommendations:
                    report += f"- {rec}\n"
                report += "\n"

            report += "---\n\n"

        # Write report
        from pathlib import Path
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(report)


def main():
    import argparse
    import yaml

    parser = argparse.ArgumentParser(description='CI/CD health monitoring')
    parser.add_argument('--output', default='ci-health.json')
    parser.add_argument('--report', default='docs/reports/ci-health.md')
    args = parser.parse_args()

    # Load repos from config
    with open('config/repos.yml') as f:
        config = yaml.safe_load(f)

    repos = [r['name'] for r in config['repositories']]

    # Analyze
    monitor = CIHealthMonitor(repos)
    health_report = monitor.analyze_all_repos()

    # Write JSON
    with open(args.output, 'w') as f:
        json.dump(health_report, f, indent=2)

    # Write Markdown
    monitor.generate_markdown_report(health_report, args.report)

    # Print summary
    print(f"\n{'='*60}")
    print("CI/CD HEALTH ANALYSIS")
    print(f"{'='*60}")
    print(f"Overall health: {health_report['overall_health_score']}/100")
    print(f"Healthy repos: {health_report['summary']['healthy_repos']}/{health_report['summary']['total_repos']}")
    print(f"\nReports written to:")
    print(f"  JSON: {args.output}")
    print(f"  Markdown: {args.report}")


if __name__ == '__main__':
    main()
